"""opscopilot/report.py — the handover-summary pipeline behind `opscopilot report`.

Purpose:      Compose the two tools already built (NordDesk MCP client, Nordwiki retrieval) into
              Marek's end-of-shift handover: gather open incidents, follow-ups, the runbook each
              incident points at, and the next shift's on-call; then have the model fill
              the template and verify the mandatory headings came back in order (one retry).
Entry points: gather(shift, date) -> HandoverData, draft(data) -> str, check_template(text) ->
              list[str] (missing headings), next_shift(), TEMPLATE_PATH, REQUIRED_HEADINGS
Depends on:   opscopilot.mcp_tickets.client, opscopilot.rag.retrieve, opscopilot.llm.client,
              opscopilot.govern.{redact,audit},
              opscopilot/llm/prompts/report.md, opscopilot/templates/handover.md
Used by:      opscopilot.cli (`report`), scripts/demo.py
Invariants:   gather() makes no model call and is deterministic given the store + corpus. The
              output of draft() always contains REQUIRED_HEADINGS in order, or draft() raises.
              Ticket text is redacted before it reaches the model; a redacted ticket carries a
              `sensitive` list naming the kinds found, so section 3 can flag it without the value.
"""

from __future__ import annotations

import json
import re
from datetime import date as date_type
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from opscopilot import store
from opscopilot.govern import audit
from opscopilot.govern.redact import redact_obj
from opscopilot.llm.client import get_llm_client
from opscopilot.mcp_tickets import client as tickets
from opscopilot.rag.retrieve import retrieve

TEMPLATE_PATH = Path(__file__).parent / "templates" / "handover.md"  # Marek's format
PROMPT_PATH = Path(__file__).parent / "llm" / "prompts" / "report.md"

REQUIRED_HEADINGS = [
    "## 1. Open incidents (P1/P2 first)",
    "## 2. Tickets needing follow-up on the next shift",
    "## 3. Anything flagged sensitive",
    "## 4. On-call for the next shift",
]
_URGENCY_RANK = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}


class HandoverData(BaseModel):
    """Everything the model gets — gathered, not generated."""

    shift: str
    date: str
    next_shift: str
    outgoing_lead: str
    incoming_lead: str
    stats: dict[str, int]
    open_incidents: list[dict[str, Any]]
    follow_ups: list[dict[str, Any]]
    runbooks: dict[str, str]  # ticket id -> wiki page id
    oncall: list[dict[str, Any]]


def next_shift(shift: str) -> str:
    return "night" if shift == "day" else "day"


def _brief(t: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "type", "system", "urgency", "status", "summary", "updated_at", "updates")
    brief = {k: t.get(k) for k in keys}
    if "sensitive" in t:
        brief["sensitive"] = t["sensitive"]
    return brief


def _lead(rota: list[dict[str, Any]], team: str = "ot") -> str:
    return next((r["name"] for r in rota if r.get("team") == team), "(unknown)")


def gather(shift: str, date: str | None = None) -> HandoverData:
    """Step 1 — tools only, no model. Fresh calls every time (the re-fetch rule)."""
    date = date or date_type.today().isoformat()
    live = tickets.run(tickets.search_tickets("", status="open", limit=50)) + tickets.run(
        tickets.search_tickets("", status="in_progress", limit=50)
    )
    full = []
    for t in live:
        clean, findings = redact_obj(tickets.run(tickets.get_ticket(t["id"])))
        if findings:
            audit.log_event(
                "redaction", where=f"ticket:{t['id']}", findings=[f.model_dump() for f in findings]
            )
            clean["sensitive"] = [
                f.kind for f in findings
            ]  # tells the model WHAT was there, not the value
        full.append(clean)
    incidents = sorted(
        (t for t in full if t["type"] == "incident"),
        key=lambda t: (_URGENCY_RANK.get(t["urgency"], 9), t["id"]),
    )
    follow_ups = sorted((t for t in full if t["type"] != "incident"), key=lambda t: t["id"])
    runbooks: dict[str, str] = {}
    for t in incidents:
        hits = retrieve(t["summary"], k=1)
        if hits:
            runbooks[t["id"]] = hits[0].page_id
    nxt = next_shift(shift)
    oncall_next = tickets.run(tickets.get_oncall(nxt))
    oncall_now = tickets.run(tickets.get_oncall(shift))
    return HandoverData(
        shift=shift,
        date=date,
        next_shift=nxt,
        outgoing_lead=_lead(oncall_now),
        incoming_lead=_lead(oncall_next),
        stats={
            "open_incidents": len(incidents),
            "p1_p2_incidents": sum(1 for t in incidents if t["urgency"] in ("P1", "P2")),
            "follow_ups": len(follow_ups),
            "tickets_seen": len(full),
        },
        open_incidents=[_brief(t) for t in incidents],
        follow_ups=[_brief(t) for t in follow_ups],
        runbooks=runbooks,
        oncall=oncall_next,
    )


def check_template(text: str) -> list[str]:
    """The mandatory headings that are missing or out of order (empty list = conforms)."""
    pos = -1
    missing = []
    for heading in REQUIRED_HEADINGS:
        m = re.search("^" + re.escape(heading) + r"\s*$", text, flags=re.MULTILINE)
        if m is None or m.start() < pos:
            missing.append(heading)
        else:
            pos = m.start()
    return missing


def user_message(data: HandoverData) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        f"<template>\n{template}\n</template>\n\n"
        f"<stats>\n{json.dumps(data.stats)}\n</stats>\n\n"
        f"<context>\n{json.dumps(data.model_dump(exclude={'stats'}), indent=1, ensure_ascii=False)}"
        "\n</context>"
    )


def draft(data: HandoverData) -> str:
    """Step 2 — the model fills the template; verified against REQUIRED_HEADINGS, one retry."""
    client = get_llm_client()
    system = PROMPT_PATH.read_text(encoding="utf-8").strip()
    user = user_message(data)
    result = client.complete(system, [{"role": "user", "content": user}])
    audit.log_event(
        "model_call",
        step="report",
        provider=result.provider,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
    )
    store.add_usage(
        "report",
        step="report",
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
    )
    text = result.text
    missing = check_template(text)
    if missing:
        hint = (
            f"{user}\n\nYour previous draft was missing or reordered these mandatory headings: "
            f"{missing}. Produce the document again with every heading verbatim and in order."
        )
        text = client.complete(system, [{"role": "user", "content": hint}]).text
        missing = check_template(text)
        if missing:
            raise ValueError(f"draft does not match the handover template; missing {missing}")
    return text.strip()
