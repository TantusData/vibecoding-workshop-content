"""opscopilot/govern/audit.py — one JSON line per event, redacted, in var/audit.log.

Purpose:      The trace of what the assistant did: every model call, tool call, approval
              decision, scope refusal, redaction and injection removal — in the order it happened.
              Answers "why did it do that?" from the log, not from the model's own explanation.
              ext-trace: inside `with audit.turn()` every event also carries `turn_id` and `ms`
              and is collected, so a caller can hand the turn's own trace back to the user.
              Every line carries `user` (OPSCOPILOT_USER or the OS account) — "who ran it".
Entry points: log_event(kind, **fields), current_user(), turn() (context manager: turn_id +
              ms + collector), current_turn_id(), audit_path(), read_events(), KINDS
Depends on:   json, datetime (stdlib); opscopilot.govern.redact (every string field is redacted)
Used by:      opscopilot.cli, opscopilot.report, opscopilot.mcp_tickets.approval, govern.*
Invariants:   Append-only. Nothing is written to the log before passing through redact_obj(),
              so a secret can never be in the log in the clear. Path from OPSCOPILOT_AUDIT_LOG.
"""

from __future__ import annotations

import contextvars
import getpass
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opscopilot.govern.redact import redact_obj

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KINDS = {
    "model_call",
    "tool_call",
    "approval",
    "refusal",
    "redaction",
    "injection",
    "answer",
    "refetch",
    "scope",
    "loop",
}


# ext-trace: the turn every event belongs to. (turn_id, started_at, collected events)
_turn: contextvars.ContextVar[tuple[str, float, list[dict[str, Any]]] | None] = (
    contextvars.ContextVar("opscopilot_turn", default=None)
)


@contextmanager
def turn(turn_id: str | None = None):
    """Scope a turn: events logged inside get `turn_id` + `ms` and are collected.

    Yields the collector list; nested turns keep their own list (the outer one is restored).
    """
    tid = turn_id or uuid.uuid4().hex[:12]
    events: list[dict[str, Any]] = []
    token = _turn.set((tid, time.monotonic(), events))
    try:
        yield tid, events
    finally:
        _turn.reset(token)


def current_user() -> str:
    """Who ran it: `OPSCOPILOT_USER`, else the OS account. A real deployment would put the
    authenticated identity here — the audit question "who" needs a field, not a guess."""
    return os.environ.get("OPSCOPILOT_USER") or getpass.getuser() or "unknown"


def current_turn_id() -> str | None:
    t = _turn.get()
    return t[0] if t else None


def audit_path() -> Path:
    return Path(os.environ.get("OPSCOPILOT_AUDIT_LOG", REPO_ROOT / "var" / "audit.log"))


def log_event(kind: str, **fields: Any) -> dict[str, Any]:
    """Append one redacted JSON line; returns the record as written."""
    if kind not in KINDS:
        raise ValueError(f"unknown audit kind {kind!r}")
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "user": current_user(),
    }
    t = _turn.get()
    if t is not None:
        record["turn_id"] = t[0]
        record["ms"] = int((time.monotonic() - t[1]) * 1000)
    record.update(fields)
    try:
        record, findings = redact_obj(record)
    except NotImplementedError:  # redaction comes later in the plan; until then the log is raw
        findings = []
    if findings:
        record["redacted"] = [f.model_dump() for f in findings]
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    if t is not None:
        t[2].append(record)
    return record


def read_events() -> list[dict[str, Any]]:
    path = audit_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
