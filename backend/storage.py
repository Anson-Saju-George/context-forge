import json
import re
from pathlib import Path

try:
  from .config import ROOT_DIR, settings
except ImportError:
  from config import ROOT_DIR, settings


def storage_base_dir() -> Path:
  configured_dir = settings()["config"].get("storage", {}).get("base_dir", "data/chats")
  return ROOT_DIR / configured_dir


def chat_dir(chat_id: str) -> Path:
  safe_chat_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", chat_id).strip("_") or "default"
  return storage_base_dir() / safe_chat_id


def uploads_dir(chat_id: str) -> Path:
  return chat_dir(chat_id) / "uploads"


def chunks_path(chat_id: str) -> Path:
  return chat_dir(chat_id) / "chunks.json"


def documents_path(chat_id: str) -> Path:
  return chat_dir(chat_id) / "documents.json"


def load_json(path: Path, default):
  if not path.exists():
    return default

  return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
