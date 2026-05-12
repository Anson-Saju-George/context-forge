import json
import sqlite3
import time
from pathlib import Path

from config import ROOT_DIR, settings


def db_path() -> Path:
  return ROOT_DIR / "data" / "contextforge.db"


def connect() -> sqlite3.Connection:
  path = db_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  connection = sqlite3.connect(path)
  connection.row_factory = sqlite3.Row
  return connection


def init_db() -> None:
  with connect() as connection:
    connection.executescript(
      """
      CREATE TABLE IF NOT EXISTS users (
        sub TEXT PRIMARY KEY,
        email TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        picture TEXT NOT NULL DEFAULT '',
        is_admin INTEGER NOT NULL DEFAULT 0,
        free_grant_used INTEGER NOT NULL DEFAULT 0,
        entitled_until INTEGER NOT NULL DEFAULT 0,
        total_payments_paise INTEGER NOT NULL DEFAULT 0,
        payment_count INTEGER NOT NULL DEFAULT 0,
        query_count INTEGER NOT NULL DEFAULT 0,
        ingest_count INTEGER NOT NULL DEFAULT 0,
        uploaded_chunk_count INTEGER NOT NULL DEFAULT 0,
        last_login_at INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL DEFAULT 0
      );

      CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sub TEXT NOT NULL,
        email TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at INTEGER NOT NULL
      );
      """
    )


def record_event(sub: str, email: str, event_type: str, details: dict | None = None) -> None:
  now = int(time.time())
  payload = json.dumps(details or {}, separators=(",", ":"))
  with connect() as connection:
    connection.execute(
      """
      INSERT INTO usage_events (sub, email, event_type, details_json, created_at)
      VALUES (?, ?, ?, ?, ?)
      """,
      (sub, email or "", event_type, payload, now),
    )


def upsert_user_profile(user: dict, is_admin: bool) -> sqlite3.Row:
  now = int(time.time())
  with connect() as connection:
    connection.execute(
      """
      INSERT INTO users (
        sub, email, name, picture, is_admin, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(sub) DO UPDATE SET
        email=excluded.email,
        name=excluded.name,
        picture=excluded.picture,
        is_admin=excluded.is_admin,
        updated_at=excluded.updated_at
      """,
      (
        user["sub"],
        user.get("email", ""),
        user.get("name", ""),
        user.get("picture", ""),
        1 if is_admin else 0,
        now,
        now,
      ),
    )
    return connection.execute("SELECT * FROM users WHERE sub = ?", (user["sub"],)).fetchone()


def ensure_user_entitlement(user: dict, is_admin: bool) -> dict:
  row = upsert_user_profile(user, is_admin)
  now = int(time.time())
  expires_in = settings().get("auth_session_seconds", 3600)

  if is_admin:
    with connect() as connection:
      connection.execute(
        "UPDATE users SET last_login_at = ?, updated_at = ? WHERE sub = ?",
        (now, now, user["sub"]),
      )
    record_event(user["sub"], user.get("email", ""), "login_admin", {})
    return {"paid": True, "exp": 0}

  entitled_until = int(row["entitled_until"] or 0)
  free_grant_used = bool(row["free_grant_used"])

  if not free_grant_used:
    entitled_until = now + expires_in
    with connect() as connection:
      connection.execute(
        """
        UPDATE users
        SET free_grant_used = 1,
            entitled_until = ?,
            last_login_at = ?,
            updated_at = ?
        WHERE sub = ?
        """,
        (entitled_until, now, now, user["sub"]),
      )
    record_event(
      user["sub"],
      user.get("email", ""),
      "free_trial_granted",
      {"entitled_until": entitled_until, "duration_seconds": expires_in},
    )
    return {"paid": True, "exp": entitled_until}

  with connect() as connection:
    connection.execute(
      "UPDATE users SET last_login_at = ?, updated_at = ? WHERE sub = ?",
      (now, now, user["sub"]),
    )

  active = entitled_until > now
  record_event(
    user["sub"],
    user.get("email", ""),
    "login",
    {"active_entitlement": active, "entitled_until": entitled_until},
  )
  return {"paid": active, "exp": entitled_until if active else 0}


def extend_user_entitlement(sub: str, email: str, amount_paise: int, duration_seconds: int) -> int:
  now = int(time.time())
  with connect() as connection:
    row = connection.execute("SELECT entitled_until FROM users WHERE sub = ?", (sub,)).fetchone()
    current_until = int(row["entitled_until"] or 0) if row else 0
    new_until = max(current_until, now) + duration_seconds
    connection.execute(
      """
      UPDATE users
      SET entitled_until = ?,
          total_payments_paise = total_payments_paise + ?,
          payment_count = payment_count + 1,
          updated_at = ?
      WHERE sub = ?
      """,
      (new_until, amount_paise, now, sub),
    )
  record_event(
    sub,
    email,
    "payment_verified",
    {"amount_paise": amount_paise, "duration_seconds": duration_seconds, "entitled_until": new_until},
  )
  return new_until


def record_payment_attempt(sub: str, email: str, amount_paise: int, currency: str) -> None:
  record_event(sub, email, "payment_order_created", {"amount_paise": amount_paise, "currency": currency})


def increment_query_usage(sub: str, email: str, rag_version: str, provider: str) -> None:
  now = int(time.time())
  with connect() as connection:
    connection.execute(
      "UPDATE users SET query_count = query_count + 1, updated_at = ? WHERE sub = ?",
      (now, sub),
    )
  record_event(sub, email, "chat_query", {"rag_version": rag_version, "provider": provider})


def increment_ingest_usage(sub: str, email: str, document_count: int, chunk_count: int) -> None:
  now = int(time.time())
  with connect() as connection:
    connection.execute(
      """
      UPDATE users
      SET ingest_count = ingest_count + ?,
          uploaded_chunk_count = uploaded_chunk_count + ?,
          updated_at = ?
      WHERE sub = ?
      """,
      (document_count, chunk_count, now, sub),
    )
  record_event(
    sub,
    email,
    "documents_ingested",
    {"document_count": document_count, "chunk_count": chunk_count},
  )


def get_user_usage(sub: str) -> dict | None:
  with connect() as connection:
    row = connection.execute(
      """
      SELECT sub, email, name, is_admin, free_grant_used, entitled_until,
             total_payments_paise, payment_count, query_count, ingest_count,
             uploaded_chunk_count, last_login_at, created_at, updated_at
      FROM users
      WHERE sub = ?
      """,
      (sub,),
    ).fetchone()
  if not row:
    return None
  return dict(row)
