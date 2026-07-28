import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Header, HTTPException

from config import auth_enabled, settings


def b64encode(payload: bytes) -> str:
  return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def b64decode(payload: str) -> bytes:
  padding = "=" * (-len(payload) % 4)
  return base64.urlsafe_b64decode(f"{payload}{padding}")


def session_secret() -> bytes:
  secret = settings().get("jwt_secret")
  if not secret:
    raise HTTPException(status_code=500, detail="Auth secret is not configured.")
  return secret.encode("utf-8")


def payment_enabled() -> bool:
  app_settings = settings()
  return bool(
    auth_enabled()
    and app_settings.get("razorpay_key_id")
    and app_settings.get("razorpay_key_secret_configured")
  )


def is_admin_email(email: str) -> bool:
  normalized = (email or "").strip().lower()
  return bool(normalized and normalized in set(settings().get("admin_emails", [])))


def local_user() -> dict:
  return {
    "sub": "local-development",
    "email": "local@contextforge.dev",
    "name": "Local Development",
    "picture": "",
    "is_admin": True,
    "iat": int(time.time()),
    "exp": 0,
  }


def sign_payload(payload: dict) -> str:
  body = b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
  signature = hmac.new(session_secret(), body.encode("ascii"), hashlib.sha256).digest()
  return f"{body}.{b64encode(signature)}"


def verify_session_token(token: str) -> dict:
  try:
    body, signature = token.split(".", 1)
    expected = b64encode(hmac.new(session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
      raise ValueError("Bad signature")
    payload = json.loads(b64decode(body).decode("utf-8"))
  except (ValueError, json.JSONDecodeError):
    raise HTTPException(status_code=401, detail="Invalid auth session.")

  if not payload.get("is_admin") and int(payload.get("exp", 0)) and int(payload.get("exp", 0)) < int(time.time()):
    raise HTTPException(status_code=401, detail="Auth session expired.")
  return payload


def create_session(user: dict, paid: bool = False, exp_override: int | None = None) -> str:
  now = int(time.time())
  expires_in = settings().get("auth_session_seconds", 3600)
  is_admin = is_admin_email(user.get("email", ""))
  effective_paid = bool(
    is_admin
    or paid
    or not payment_enabled()
    or (exp_override is not None and int(exp_override) > now)
  )
  expires_at = 0 if is_admin else int(exp_override or 0)
  if not is_admin and exp_override is None and effective_paid:
    expires_at = now + int(expires_in)
  payload = {
    "sub": user["sub"],
    "email": user.get("email", ""),
    "name": user.get("name", ""),
    "picture": user.get("picture", ""),
    "is_admin": is_admin,
    "paid": effective_paid,
    "iat": now,
    "exp": expires_at,
  }
  return sign_payload(payload)


def require_user(authorization: Annotated[str | None, Header()] = None) -> dict:
  if not auth_enabled():
    return local_user()

  if not authorization or not authorization.lower().startswith("bearer "):
    raise HTTPException(status_code=401, detail="Authentication required.")
  return verify_session_token(authorization.split(" ", 1)[1].strip())


def require_entitled_user(authorization: Annotated[str | None, Header()] = None) -> dict:
  user = require_user(authorization)
  if not payment_enabled() or user.get("is_admin"):
    return user
  if user.get("paid") and int(user.get("exp", 0)) > int(time.time()):
    return user
  raise HTTPException(status_code=402, detail="Payment required.")


def user_key(user: dict) -> str:
  digest = hashlib.sha256(user["sub"].encode("utf-8")).hexdigest()[:16]
  return f"u_{digest}"


def scoped_chat_id(chat_id: str, user: dict | None) -> str:
  if not auth_enabled():
    return chat_id

  if not isinstance(user, dict) or not user.get("sub"):
    return chat_id
  return f"{user_key(user)}_{chat_id}"


def verify_google_credential(credential: str) -> dict:
  client_id = settings().get("google_client_id", "")
  if not client_id:
    raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured.")

  try:
    from google.auth.transport import requests
    from google.oauth2 import id_token
  except ImportError as error:
    raise HTTPException(status_code=500, detail="google-auth is not installed.") from error

  try:
    idinfo = id_token.verify_oauth2_token(credential, requests.Request(), client_id)
  except ValueError as error:
    raise HTTPException(status_code=401, detail="Invalid Google credential.") from error

  allowed_domain = settings().get("google_allowed_domain", "")
  if allowed_domain and idinfo.get("hd") != allowed_domain:
    raise HTTPException(status_code=403, detail="Google account domain is not allowed.")
  if not idinfo.get("email_verified"):
    raise HTTPException(status_code=403, detail="Google email is not verified.")

  return {
    "sub": idinfo["sub"],
    "email": idinfo.get("email", ""),
    "name": idinfo.get("name", ""),
    "picture": idinfo.get("picture", ""),
  }
