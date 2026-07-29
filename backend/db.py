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

      CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY,
        user_sub TEXT NOT NULL,
        storage_chat_id TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT 'New chat',
        created_at INTEGER NOT NULL,
        last_active_at INTEGER NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_chats_user ON chats (user_sub, last_active_at);
      CREATE INDEX IF NOT EXISTS idx_chats_last_active ON chats (last_active_at);

      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        reasoning TEXT NOT NULL DEFAULT '',
        citations_json TEXT NOT NULL DEFAULT '[]',
        created_at INTEGER NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id, created_at);
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


def entitled_until(sub: str) -> int:
  with connect() as connection:
    row = connection.execute("SELECT entitled_until FROM users WHERE sub = ?", (sub,)).fetchone()
  return int(row["entitled_until"]) if row and row["entitled_until"] else 0


# --- Chats & messages ---------------------------------------------------------


def count_user_chats(user_sub: str) -> int:
  with connect() as connection:
    row = connection.execute("SELECT COUNT(*) AS n FROM chats WHERE user_sub = ?", (user_sub,)).fetchone()
  return int(row["n"]) if row else 0


def create_chat(chat_id: str, user_sub: str, storage_chat_id: str, title: str) -> dict:
  now = int(time.time())
  with connect() as connection:
    connection.execute(
      """
      INSERT INTO chats (id, user_sub, storage_chat_id, title, created_at, last_active_at)
      VALUES (?, ?, ?, ?, ?, ?)
      """,
      (chat_id, user_sub, storage_chat_id, title or "New chat", now, now),
    )
  return {"id": chat_id, "title": title or "New chat", "created_at": now, "last_active_at": now, "message_count": 0}


def list_chats(user_sub: str) -> list[dict]:
  with connect() as connection:
    rows = connection.execute(
      """
      SELECT c.id, c.title, c.created_at, c.last_active_at,
             (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.id) AS message_count
      FROM chats c
      WHERE c.user_sub = ?
      ORDER BY c.last_active_at DESC
      """,
      (user_sub,),
    ).fetchall()
  return [dict(row) for row in rows]


def get_chat(chat_id: str, user_sub: str) -> dict | None:
  with connect() as connection:
    row = connection.execute(
      "SELECT id, title, storage_chat_id, created_at, last_active_at FROM chats WHERE id = ? AND user_sub = ?",
      (chat_id, user_sub),
    ).fetchone()
  return dict(row) if row else None


def rename_chat(chat_id: str, user_sub: str, title: str) -> None:
  with connect() as connection:
    connection.execute(
      "UPDATE chats SET title = ? WHERE id = ? AND user_sub = ?",
      (title, chat_id, user_sub),
    )


def delete_chat(chat_id: str, user_sub: str) -> str | None:
  with connect() as connection:
    row = connection.execute(
      "SELECT storage_chat_id FROM chats WHERE id = ? AND user_sub = ?",
      (chat_id, user_sub),
    ).fetchone()
    if not row:
      return None
    connection.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    connection.execute("DELETE FROM chats WHERE id = ? AND user_sub = ?", (chat_id, user_sub))
  return row["storage_chat_id"]


def append_message(chat_id: str, role: str, content: str, reasoning: str = "", citations: list | None = None) -> None:
  now = int(time.time())
  citations_json = json.dumps(citations or [], separators=(",", ":"))
  with connect() as connection:
    connection.execute(
      """
      INSERT INTO messages (chat_id, role, content, reasoning, citations_json, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
      """,
      (chat_id, role, content, reasoning or "", citations_json, now),
    )
    connection.execute("UPDATE chats SET last_active_at = ? WHERE id = ?", (now, chat_id))


def get_messages(chat_id: str, limit: int | None = None) -> list[dict]:
  query = "SELECT role, content, reasoning, citations_json, created_at FROM messages WHERE chat_id = ? ORDER BY created_at ASC, id ASC"
  params: tuple = (chat_id,)
  if limit is not None:
    # Take the most recent `limit`, then restore chronological order.
    query = (
      "SELECT role, content, reasoning, citations_json, created_at FROM ("
      "SELECT role, content, reasoning, citations_json, created_at, id FROM messages "
      "WHERE chat_id = ? ORDER BY created_at DESC, id DESC LIMIT ?"
      ") ORDER BY created_at ASC, id ASC"
    )
    params = (chat_id, limit)
  with connect() as connection:
    rows = connection.execute(query, params).fetchall()
  messages = []
  for row in rows:
    item = dict(row)
    try:
      item["citations"] = json.loads(item.pop("citations_json") or "[]")
    except json.JSONDecodeError:
      item["citations"] = []
    messages.append(item)
  return messages


def count_user_prompts(chat_id: str) -> int:
  with connect() as connection:
    row = connection.execute(
      "SELECT COUNT(*) AS n FROM messages WHERE chat_id = ? AND role = 'user'",
      (chat_id,),
    ).fetchone()
  return int(row["n"]) if row else 0


def purge_expired_chats(retention_days: int) -> list[str]:
  """Delete chats (and their messages) with no activity for `retention_days`.

  Returns the storage_chat_ids of purged chats so the caller can remove their
  on-disk document folders.
  """
  cutoff = int(time.time()) - retention_days * 86400
  with connect() as connection:
    rows = connection.execute(
      "SELECT id, storage_chat_id FROM chats WHERE last_active_at < ?",
      (cutoff,),
    ).fetchall()
    if not rows:
      return []
    chat_ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in chat_ids)
    connection.execute(f"DELETE FROM messages WHERE chat_id IN ({placeholders})", chat_ids)
    connection.execute(f"DELETE FROM chats WHERE id IN ({placeholders})", chat_ids)
  return [row["storage_chat_id"] for row in rows]
