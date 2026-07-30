import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import modal

app = modal.App("context-forge-ollama")

# Persists pulled model weights across container cold starts so a fresh container
# doesn't re-download multi-GB models on every scale-up.
models_volume = modal.Volume.from_name("context-forge-ollama-models", create_if_missing=True)

MODELS_DIR = "/ollama-models"
OLLAMA_PORT = 11434


def _deploy_time_allowlist() -> list[str]:
  """Runs LOCALLY at `modal deploy` time. The models Modal serves are driven by the
  SAME single source the app uses - OLLAMA_MODEL_ALLOWLIST - read from the shell env
  or the repo-root .env, so Modal pulls exactly the models the app offers."""
  raw = os.getenv("OLLAMA_MODEL_ALLOWLIST", "").strip()
  if not raw:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
      for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("OLLAMA_MODEL_ALLOWLIST=") and not stripped.startswith("#"):
          raw = stripped.split("=", 1)[1].strip()
          break
  models = [m.strip() for m in raw.split(",") if m.strip()]
  return models or ["qwen3:4b-instruct"]


PULL_MODELS = _deploy_time_allowlist()

image = (
  modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
  .apt_install("curl", "zstd")
  .run_commands("curl -fsSL https://ollama.com/install.sh | sh")
  # Bake the allowlist into the image at deploy time so the container pulls the same
  # set the app offers (single source: OLLAMA_MODEL_ALLOWLIST).
  .env({"OLLAMA_PULL_MODELS": ",".join(PULL_MODELS)})
)


def _wait_for_ollama(timeout_seconds: int = 60) -> None:
  deadline = time.time() + timeout_seconds
  while time.time() < deadline:
    try:
      urllib.request.urlopen(f"http://127.0.0.1:{OLLAMA_PORT}/api/tags", timeout=2)
      return
    except (urllib.error.URLError, OSError):
      time.sleep(1)
  raise RuntimeError("Ollama server did not become ready in time.")


@app.server(
  image=image,
  gpu="A10G",
  volumes={MODELS_DIR: models_volume},
  # Keep the GPU warm for 2 min after the last request. Lower = cheaper idle
  # (~2c/sparse session vs ~9c at 300s) at the cost of more cold starts.
  scaledown_window=120,
  # First cold start pulls every allowlisted model into the Volume (multi-GB); give
  # it plenty of headroom. Subsequent cold starts find them cached and start fast.
  startup_timeout=1800,
  port=OLLAMA_PORT,
  # unauthenticated defaults to False: Modal requires Modal-Key/Modal-Secret proxy
  # auth headers on every request. Do not set this to True - that would expose a
  # bare GPU inference endpoint to the entire internet with zero auth.
)
class OllamaServer:
  @modal.enter()
  def start(self):
    os.environ["OLLAMA_MODELS"] = MODELS_DIR
    # Ollama defaults to binding 127.0.0.1 only, which Modal's server proxy can't
    # reach from outside the process's own loopback.
    os.environ["OLLAMA_HOST"] = f"0.0.0.0:{OLLAMA_PORT}"
    subprocess.Popen(["ollama", "serve"])
    _wait_for_ollama()
    # Pre-pull every allowlisted model (idempotent - cached in the Volume) so the app
    # only ever offers models that are actually installed here.
    models = [m.strip() for m in os.getenv("OLLAMA_PULL_MODELS", "qwen3:4b-instruct").split(",") if m.strip()]
    for model in models:
      print(f"[startup] ensuring model present: {model}")
      subprocess.run(["ollama", "pull", model], check=True)
    models_volume.commit()


@app.local_entrypoint()
def main():
  # `modal run backend/modal_app.py` deploys a throwaway instance and prints its URL
  # for manual testing. Use `modal deploy backend/modal_app.py` for a persistent
  # deployment, then copy the printed URL into OLLAMA_BASE_URL in .env, and set
  # MODAL_PROXY_KEY / MODAL_PROXY_SECRET so requests carry the required auth headers.
  print(f"Ollama server URL: {OllamaServer().get_web_url()}")
