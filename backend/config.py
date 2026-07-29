import json
import os
import secrets
from functools import lru_cache
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_ENV_PATH = ROOT_DIR / ".env"
BACKEND_ENV_PATH = BACKEND_DIR / ".env"
SECRETS_ENV_PATH = BACKEND_DIR / "secrets.env"


def load_env_file(path: Path) -> None:
  if not path.exists():
    return

  for raw_line in path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue

    key, value = line.split("=", 1)
    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def load_dotenv() -> None:
  load_env_file(ROOT_ENV_PATH)
  load_env_file(BACKEND_ENV_PATH)
  load_env_file(SECRETS_ENV_PATH)


def config_path() -> Path:
  configured_file = os.getenv("CONFIG_FILE", "config.json").strip() or "config.json"
  configured_path = Path(configured_file)

  if configured_path.is_absolute():
    return configured_path

  return ROOT_DIR / configured_path


def read_config() -> dict:
  path = config_path()
  if not path.exists():
    raise FileNotFoundError(f"Config file not found: {path}")

  with path.open("r", encoding="utf-8") as config_file:
    return json.load(config_file)


def env_value(name: str) -> str:
  return os.getenv(name, "").strip()


def env_int(name: str, default: int) -> int:
  raw_value = env_value(name)
  if not raw_value:
    return default
  try:
    return int(raw_value)
  except ValueError:
    return default


def env_float(name: str, default: float) -> float:
  raw_value = env_value(name)
  if not raw_value:
    return default
  try:
    return float(raw_value)
  except ValueError:
    return default


def env_bool(name: str, default: bool) -> bool:
  raw_value = env_value(name).lower()
  if not raw_value:
    return default
  return raw_value in ("1", "true", "yes", "on")


# --- Single source of truth for human-facing access/price labels --------------
# These derive entirely from the env-configured duration + amount so a value is
# defined in exactly one place (the env) and formatted once here.

_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def format_duration_label(seconds: int) -> str:
  seconds = int(seconds)
  if seconds >= 3600 and seconds % 3600 == 0:
    hours = seconds // 3600
    return f"{hours} hour" + ("s" if hours > 1 else "")
  if seconds >= 60 and seconds % 60 == 0:
    return f"{seconds // 60} min"
  return f"{seconds} sec"


def format_amount_label(amount_paise: int, currency: str) -> str:
  symbol = _CURRENCY_SYMBOLS.get((currency or "").upper(), (currency or "").upper() + " ")
  amount = int(amount_paise) / 100
  text = f"{amount:.2f}".rstrip("0").rstrip(".")
  return f"{symbol}{text}"


def access_label(app_settings: dict) -> str:
  """One canonical 'what you're buying' string, reused by the payment order
  description and the frontend button so there is a single source of truth."""
  return f"{format_duration_label(app_settings['auth_session_seconds'])} ContextForge access"


def apply_env_overrides(config: dict) -> dict:
  routing = config.setdefault("routing", {})
  storage = config.setdefault("storage", {})

  frontend_base_path = env_value("FRONTEND_BASE_PATH")
  api_base_url = env_value("API_BASE_URL")
  api_prefix = env_value("API_PREFIX")
  storage_base_dir = env_value("STORAGE_BASE_DIR")
  cors_origins = env_value("CORS_ORIGINS")

  if frontend_base_path:
    routing["frontend_base_path"] = frontend_base_path
  if api_base_url:
    routing["api_base_url"] = api_base_url
  if api_prefix:
    routing["api_prefix"] = api_prefix
  if storage_base_dir:
    storage["base_dir"] = storage_base_dir
  if cors_origins:
    routing["cors_origins"] = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

  return config


@lru_cache(maxsize=1)
def settings() -> dict:
  load_dotenv()
  config = apply_env_overrides(read_config())
  routing = config.get("routing", {})
  app_env = os.getenv("APP_ENV", config.get("deployment_profile", "local_dev"))
  secrets_enabled = SECRETS_ENV_PATH.exists()
  jwt_secret = os.getenv("JWT_SECRET")
  jwt_secret_generated = False

  if not jwt_secret and app_env == "local_dev":
    jwt_secret = secrets.token_urlsafe(48)
    jwt_secret_generated = True

  return {
    "app_name": "ContextForge",
    "app_env": app_env,
    "config": config,
    "config_file": str(config_path().relative_to(ROOT_DIR)),
    "config_path": str(config_path()),
    "api_prefix": routing.get("api_prefix", "/context-forge/api"),
    "docs_path": routing.get("docs_path", "/context-forge/api/docs"),
    "openapi_path": routing.get("openapi_path", "/context-forge/api/openapi.json"),
    "cors_origins": routing.get("cors_origins", []),
    "jwt_secret_configured": bool(jwt_secret),
    "jwt_secret_generated": jwt_secret_generated,
    "jwt_secret": jwt_secret,
    "secrets_enabled": secrets_enabled,
    "google_client_id": env_value("GOOGLE_CLIENT_ID"),
    "google_allowed_domain": env_value("GOOGLE_ALLOWED_DOMAIN"),
    "auth_session_seconds": int(env_value("AUTH_SESSION_SECONDS") or "3600"),
    "admin_emails": [
      email.strip().lower()
      for email in (env_value("ADMIN_EMAILS") or env_value("admin")).split(",")
      if email.strip()
    ],
    "razorpay_key_id": env_value("RAZORPAY_KEY_ID"),
    "razorpay_key_secret_configured": bool(env_value("RAZORPAY_KEY_SECRET")),
    "razorpay_key_secret": env_value("RAZORPAY_KEY_SECRET"),
    "razorpay_amount_paise": int(env_value("RAZORPAY_AMOUNT_PAISE") or "2000"),
    "razorpay_currency": env_value("RAZORPAY_CURRENCY") or "INR",
    "max_upload_files": env_int("MAX_UPLOAD_FILES", 5),
    "max_active_clients": max(1, env_int("MAX_ACTIVE_CLIENTS", 1)),
    "vram_available_gb": env_float("VRAM_AVAILABLE_GB", 0),
    "vram_required_gb": env_float("VRAM_REQUIRED_GB", 0),
    "max_chats_per_user": max(1, env_int("MAX_CHATS_PER_USER", 2)),
    "max_prompts_per_chat": max(1, env_int("MAX_PROMPTS_PER_CHAT", 10)),
    "chat_retention_days": max(1, env_int("CHAT_RETENTION_DAYS", 30)),
    "free_trial_enabled": env_bool("FREE_TRIAL_ENABLED", True),
  }


def auth_enabled() -> bool:
  app_settings = settings()
  if app_settings.get("app_env") != "local_dev":
    # Outside local dev, missing/misconfigured secrets must fail closed (require real
    # Google auth) rather than silently reporting auth as disabled to the frontend.
    return True
  return bool(app_settings.get("secrets_enabled") and app_settings.get("google_client_id"))


def generation_config() -> dict:
  return settings()["config"].get("features", {}).get("generation", {})


def model_allowlist() -> list[str]:
  load_dotenv()
  raw_allowlist = os.getenv("OLLAMA_MODEL_ALLOWLIST", "").strip()
  if not raw_allowlist:
    return []
  return [
    model.strip()
    for model in raw_allowlist.split(",")
    if model.strip()
  ]


def resolve_capabilities() -> dict:
  app_settings = settings()
  config = app_settings["config"]
  features = config.get("features", {})
  generation = features.get("generation", {})
  allowed_models = model_allowlist()
  auth_is_enabled = auth_enabled()
  payments_enabled = bool(
    auth_is_enabled
    and app_settings["razorpay_key_id"]
    and app_settings["razorpay_key_secret_configured"]
  )

  return {
    "profile": config.get("deployment_profile", "local_dev"),
    "limits": config.get("limits", {}),
    "generation": {
      "default_provider": generation.get("default_provider", "ollama"),
      "default_model": generation.get("default_model", "qwen3:4b-instruct"),
      "models": [
        {
          "id": model,
          "label": model,
          "status": "enabled",
        }
        for model in allowed_models
      ],
      "providers": [
        {
          "id": provider,
          "label": provider.replace("_", " ").title(),
          "status": "enabled" if enabled else "disabled",
        }
        for provider, enabled in generation.get("providers", {}).items()
      ],
    },
    "retrieval": {
      "default": features.get("retrieval", {}).get("default", "v3.1"),
      "options": [
        {
          "id": strategy,
          "label": strategy.replace("_", " ").title(),
          "status": "enabled" if enabled else "disabled",
        }
        for strategy, enabled in features.get("retrieval", {}).get("strategies", {}).items()
      ],
    },
    "auth": {
      "provider": "google",
      "enabled": auth_is_enabled,
      "google_client_id": app_settings["google_client_id"] if auth_is_enabled else "",
      "session_seconds": app_settings["auth_session_seconds"],
      "admin_emails_configured": len(app_settings["admin_emails"]),
    },
    "payments": {
      "provider": "razorpay",
      "enabled": payments_enabled,
      "razorpay_key_id": app_settings["razorpay_key_id"] if payments_enabled else "",
      "duration_seconds": app_settings["auth_session_seconds"],
      "amount": app_settings["razorpay_amount_paise"],
      "currency": app_settings["razorpay_currency"],
      # Derived labels so the frontend never hardcodes duration/price.
      "duration_label": format_duration_label(app_settings["auth_session_seconds"]),
      "amount_label": format_amount_label(app_settings["razorpay_amount_paise"], app_settings["razorpay_currency"]),
      "access_label": access_label(app_settings),
      "free_trial_enabled": app_settings["free_trial_enabled"],
    },
    "scheduler": {
      "max_upload_files": app_settings["max_upload_files"],
      "max_active_clients": app_settings["max_active_clients"],
      "vram_available_gb": app_settings["vram_available_gb"],
      "vram_required_gb": app_settings["vram_required_gb"],
      "vram_ready": not app_settings["vram_required_gb"] or app_settings["vram_available_gb"] >= app_settings["vram_required_gb"],
    },
  }
