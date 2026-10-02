"""norddesk_mcp/store.py — the fake NordDesk's data: a JSON file, re-read on every call.

Purpose:      Holds tickets, systems, on-call rota and assets in one JSON document. Nothing is
              cached in memory: every tool call loads the file fresh and every write saves it
              back, so editing the file by hand (or from another process) is visible immediately —
              exactly how a real ticket system behaves from the assistant's point of view.
Entry points: load(), save(), init_store(), store_path(), SEED_PATH, and the plain-Python tool
              functions: search_tickets(), get_ticket(), create_ticket(), post_update(),
              get_system_status(), get_oncall() — importable and testable without MCP or a model.
Depends on:   stdlib only (json, pathlib, datetime, os, shutil)
Used by:      norddesk_mcp.server (wraps these as MCP tools), norddesk_mcp.__main__ (init)
Invariants:   Never mutates data/norddesk/seed.json — writes go to store_path() (NORDDESK_STORE,
              default var/norddesk.json), resolved at call time. A missing store is created from
              the seed on first read, so a fresh checkout needs no setup command.
              Ticket ids are unique and prefixed by type (INC/REQ/CHG/Q). Timestamps are ISO-8601
              with the Europe/Warsaw offset.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = REPO_ROOT / "data" / "norddesk" / "seed.json"
DEFAULT_STORE_PATH = REPO_ROOT / "var" / "norddesk.json"


def store_path() -> Path:
    """Resolved on every call so NORDDESK_STORE can point a test (or a demo) at another file."""
    return Path(os.environ.get("NORDDESK_STORE", DEFAULT_STORE_PATH))


_PREFIX = {
    "incident": "INC",
    "access_request": "REQ",
    "change_request": "CHG",
    "question": "Q",
    "vendor": "VEN",
    "other": "OTH",
}
_WARSAW = timezone(timedelta(hours=2))  # CEST; good enough for a fake


def _now() -> str:
    return datetime.now(_WARSAW).replace(microsecond=0).isoformat()


def init_store(force: bool = False) -> Path:
    """Copy the committed seed to the runtime store (skips if present unless force=True)."""
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if force or not path.exists():
        shutil.copyfile(SEED_PATH, path)
    return path


def load() -> dict[str, Any]:
    """Read the whole store from disk. Called at the start of EVERY tool call — never cached."""
    path = store_path()
    if not path.exists():
        init_store()  # first use on a fresh checkout: start from the committed seed
    return json.loads(path.read_text(encoding="utf-8"))


def save(data: dict[str, Any]) -> None:
    store_path().write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---- tool functions (plain Python; the MCP layer in server.py just exposes these) -----------


def _brief(t: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "type", "system", "urgency", "status", "summary", "updated_at")
    return {k: t.get(k) for k in keys}


def search_tickets(
    query: str = "",
    status: str | None = None,
    system: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Case-insensitive substring search over id, summary, description and comments."""
    data = load()
    q = query.strip().lower()
    out = []
    for t in data["tickets"]:
        if status and t.get("status") != status:
            continue
        if system and t.get("system") != system:
            continue
        haystack = " ".join(
            [t["id"], t.get("summary", ""), t.get("description", "")]
            + [u.get("text", "") for u in t.get("updates", [])]
        ).lower()
        if q and q not in haystack:
            continue
        out.append(_brief(t))
    out.sort(key=lambda t: t["updated_at"] or "", reverse=True)
    return out[: max(1, limit)]


def get_ticket(ticket_id: str) -> dict[str, Any]:
    """The full ticket, comments included. Unknown id -> {"error": ...} (tools should not raise)."""
    data = load()
    for t in data["tickets"]:
        if t["id"].upper() == ticket_id.strip().upper():
            return t
    return {"error": f"ticket {ticket_id!r} not found"}


def create_ticket(
    summary: str,
    description: str,
    type: str = "incident",  # noqa: A002 -- NordDesk field name
    urgency: str = "P3",
    system: str | None = None,
    reporter: str = "opscopilot",
) -> dict[str, Any]:
    """Append a new ticket and persist. Returns the created ticket."""
    if type not in _PREFIX:
        return {"error": f"unknown type {type!r}; use one of {sorted(_PREFIX)}"}
    if urgency not in {"P1", "P2", "P3", "P4"}:
        return {"error": f"unknown urgency {urgency!r}; use P1..P4"}
    data = load()
    prefix = _PREFIX[type]
    existing = [
        int(t["id"].split("-")[1]) for t in data["tickets"] if t["id"].startswith(prefix + "-")
    ]
    new_id = f"{prefix}-{((max(existing) + 1) if existing else 1000):04d}"
    now = _now()
    ticket = {
        "id": new_id,
        "type": type,
        "system": system,
        "urgency": urgency,
        "team": "unassigned",
        "status": "open",
        "summary": summary[:200],
        "description": description,
        "reporter": reporter,
        "created_at": now,
        "updated_at": now,
        "updates": [],
    }
    data["tickets"].append(ticket)
    save(data)
    return ticket


def post_update(
    ticket_id: str,
    text: str,
    author: str = "opscopilot",
    status: str | None = None,
) -> dict[str, Any]:
    """Add a comment to a ticket (and optionally set its status), persist, return the ticket."""
    data = load()
    for t in data["tickets"]:
        if t["id"].upper() == ticket_id.strip().upper():
            now = _now()
            t.setdefault("updates", []).append({"at": now, "author": author, "text": text})
            if status:
                t["status"] = status
            t["updated_at"] = now
            save(data)
            return t
    return {"error": f"ticket {ticket_id!r} not found"}


def get_system_status(system: str | None = None) -> list[dict[str, Any]]:
    """Systems with their declared status plus a live count of open tickets against each."""
    data = load()
    open_by_system: dict[str, int] = {}
    for t in data["tickets"]:
        if t.get("status") in ("open", "in_progress") and t.get("system"):
            open_by_system[t["system"]] = open_by_system.get(t["system"], 0) + 1
    out = []
    for s in data["systems"]:
        if system and s["id"] != system and s["name"].lower() != system.lower():
            continue
        out.append({**s, "open_tickets": open_by_system.get(s["id"], 0)})
    return out


def get_oncall(shift: str | None = None) -> list[dict[str, Any]]:
    """The on-call rota: every team for one shift ("day" | "night"), or the whole rota."""
    data = load()
    rota = data.get("oncall", [])
    if shift:
        rota = [r for r in rota if r.get("shift") == shift]
    return rota
