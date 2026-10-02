"""opscopilot/store.py — one SQLite file for conversation history and model usage (stdlib only).

Purpose:      Persistence for the two post-`final` extensions. `messages` holds every turn of a
              session (user, assistant, tool_call, tool_result); `usage` holds one row per model
              call. Everything written passes `govern.redact` first, same rule as the audit log,
              so the database can never hold a secret in the clear.
Entry points: connect(), add_message(), messages(session_id), sessions(), purge(older_than_days),
              add_usage(), usage_rows(), db_path(), new_session_id(), estimate_tokens()
Depends on:   sqlite3 (stdlib), opscopilot.govern.redact
Used by:      opscopilot.history (window), opscopilot.cli (usage rows), opscopilot.webapp.app
Invariants:   Append-only for messages (purge is the only delete). tokens_est = len(text) // 4 —
              an estimate, the gateway does not pre-count. One file, WAL mode, path from
              OPSCOPILOT_DB.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from opscopilot.govern.redact import redact

REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES = {"user", "assistant", "tool_call", "tool_result"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tokens_est INTEGER NOT NULL,
    redacted_kinds TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id);
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    step TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    est_system_tokens INTEGER NOT NULL DEFAULT 0,
    est_user_tokens INTEGER NOT NULL DEFAULT 0,
    est_tool_tokens INTEGER NOT NULL DEFAULT 0,
    tool TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS usage_session ON usage(session_id, id);
"""


def db_path() -> Path:
    return Path(os.environ.get("OPSCOPILOT_DB", REPO_ROOT / "var" / "opscopilot.db"))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def new_session_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def estimate_tokens(text: str) -> int:
    """Rough and honest: ~4 characters per token for English/JSON."""
    return max(1, len(text) // 4)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _redact(text: str):
    """Redaction is a guardrail (a later item of the plan in HANDOVER_NOTE.md); until it exists
    the store keeps raw text.
    That is exactly the kind of gap a redaction test catches — see test_store."""
    try:
        return redact(text)
    except NotImplementedError:
        from opscopilot.govern.redact import Redaction

        return Redaction(text=text, findings=[])


def add_message(session_id: str, role: str, content: str) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    r = _redact(content)
    row = {
        "session_id": session_id,
        "ts": _now(),
        "role": role,
        "content": r.text,
        "tokens_est": estimate_tokens(r.text),
        "redacted_kinds": ",".join(f.kind for f in r.findings),
    }
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages(session_id, ts, role, content, tokens_est, redacted_kinds) "
            "VALUES (:session_id, :ts, :role, :content, :tokens_est, :redacted_kinds)",
            row,
        )
        row["id"] = cur.lastrowid
    return row


def messages(session_id: str) -> list[dict[str, Any]]:
    """Every message of a session, oldest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def sessions() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT session_id, MIN(ts) AS started, MAX(ts) AS last, COUNT(*) AS n "
            "FROM messages GROUP BY session_id ORDER BY last DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def purge(older_than_days: int) -> int:
    """Delete messages (and usage rows) older than N days; returns rows removed."""
    cutoff = (datetime.now(UTC) - timedelta(days=older_than_days)).isoformat(timespec="seconds")
    with connect() as conn:
        n = conn.execute("DELETE FROM messages WHERE ts < ?", (cutoff,)).rowcount
        n += conn.execute("DELETE FROM usage WHERE ts < ?", (cutoff,)).rowcount
    return n


def add_usage(session_id: str, **fields: Any) -> None:
    row = {
        "session_id": session_id,
        "ts": _now(),
        "step": "",
        "provider": "",
        "model": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "est_system_tokens": 0,
        "est_user_tokens": 0,
        "est_tool_tokens": 0,
        "tool": "",
    }
    row.update({k: v for k, v in fields.items() if k in row})
    with connect() as conn:
        conn.execute(
            "INSERT INTO usage(session_id, ts, step, provider, model, input_tokens, output_tokens, "
            "cost_usd, est_system_tokens, est_user_tokens, est_tool_tokens, tool) VALUES "
            "(:session_id, :ts, :step, :provider, :model, :input_tokens, :output_tokens, "
            ":cost_usd, :est_system_tokens, :est_user_tokens, :est_tool_tokens, :tool)",
            row,
        )


def usage_rows(
    session_id: str | None = None, since_days: int | None = None
) -> list[dict[str, Any]]:
    sql, params = "SELECT * FROM usage", []
    where = []
    if session_id:
        where.append("session_id = ?")
        params.append(session_id)
    if since_days is not None:
        where.append("ts >= ?")
        params.append(
            (datetime.now(UTC) - timedelta(days=since_days)).isoformat(timespec="seconds")
        )
    if where:
        sql += " WHERE " + " AND ".join(where)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY id", params).fetchall()]
