import os
import subprocess
import time
import urllib.error
import urllib.request

import modal

app = modal.App("context-forge-ollama")

# Persists pulled model weights across container cold starts so a fresh container
# doesn't re-download multi-GB models on every scale-up.
models_volume = modal.Volume.from_name("context-forge-ollama-models", create_if_missing=True)

MODELS_DIR = "/ollama-models"
OLLAMA_PORT = 11434
DEFAULT_MODEL = os.getenv("MODAL_OLLAMA_MODEL", "qwen3:4b-instruct")

image = (
  modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
  .apt_install("curl", "zstd")
  .run_commands("curl -fsSL https://ollama.com/install.sh | sh")
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
  scaledown_window=300,
  # Model pre-pull in @modal.enter() can take a few minutes on a cold volume;
  # give the container long enough to finish before Modal calls it unhealthy.
  startup_timeout=600,
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
    # Pre-pull so the first real chat request doesn't also pay for the download.
    subprocess.run(["ollama", "pull", DEFAULT_MODEL], check=True)
    models_volume.commit()


@app.local_entrypoint()
def main():
  # `modal run backend/modal_app.py` deploys a throwaway instance and prints its URL
  # for manual testing. Use `modal deploy backend/modal_app.py` for a persistent
  # deployment, then copy the printed URL into OLLAMA_BASE_URL in .env, and set
  # MODAL_PROXY_KEY / MODAL_PROXY_SECRET so requests carry the required auth headers.
  print(f"Ollama server URL: {OllamaServer().get_web_url()}")
