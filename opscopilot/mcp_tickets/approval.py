# CONTRACT — Tomasz left these bodies unfinished (plan item 2, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/mcp_tickets/approval.py — the human approval gate in front of every NordDesk write.

Purpose:      Any tool that changes a ticket (create_ticket, post_update) must pass through
              require_approval() first. Interactive runs ask on the terminal; automated runs set
              OPSCOPILOT_AUTO_APPROVE=1 (tests) — nothing else bypasses it. No terminal (the web
              page, a pipe) means no approval. A refusal raises ApprovalDenied so the caller
              cannot silently continue.
Entry points: require_approval(action, args) -> None, ApprovalDenied, approvals (log of decisions)
Depends on:   typer (confirm prompt)
Used by:      opscopilot.mcp_tickets.client (create_ticket, post_update)
Invariants:   Writes are never executed before require_approval() returns. AUTO_APPROVE is read at
              call time, never cached. Every decision is appended to `approvals` and the audit log.
"""

from __future__ import annotations

import json
import os
import sys

import typer

from opscopilot.govern import audit

approvals: list[tuple[str, dict, bool]] = []
WRITE_ACTIONS = {"create_ticket", "post_update"}


class ApprovalDenied(PermissionError):
    """The human said no (or nobody could be asked)."""


def auto_approve() -> bool:
    return os.environ.get("OPSCOPILOT_AUTO_APPROVE", "0") == "1"


def require_approval(action: str, args: dict) -> None:
    """Block until a human approves `action(**args)`, or raise ApprovalDenied."""
    raise NotImplementedError("TODO (plan item 2): implement require_approval")
