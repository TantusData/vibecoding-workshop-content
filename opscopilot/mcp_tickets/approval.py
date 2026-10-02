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

# in-process record of (action, args, approved) — what a test asserts on; the audit log is plan item 6's
approvals: list[tuple[str, dict, bool]] = []

WRITE_ACTIONS = {"create_ticket", "post_update"}


class ApprovalDenied(PermissionError):
    """The human said no (or nobody could be asked)."""


def auto_approve() -> bool:
    return os.environ.get("OPSCOPILOT_AUTO_APPROVE", "0") == "1"


def require_approval(action: str, args: dict) -> None:
    """Block until a human approves `action(**args)`, or raise ApprovalDenied."""
    if action not in WRITE_ACTIONS:
        return  # reads never need approval
    if auto_approve():
        approvals.append((action, args, True))
        audit.log_event("approval", action=action, args=args, approved=True, how="auto")
        return
    if not sys.stdin.isatty():
        # the web page, a pipe, a cron job: nobody can be asked, so the answer is no
        approvals.append((action, args, False))
        audit.log_event("approval", action=action, args=args, approved=False, how="no-tty")
        raise ApprovalDenied(f"{action} needs a human to approve it and no terminal is attached")
    typer.echo(f"\n[approval needed] NordDesk write: {action}")
    typer.echo(json.dumps(args, indent=2, ensure_ascii=False))
    ok = typer.confirm("Apply this change?", default=False)
    approvals.append((action, args, ok))
    audit.log_event("approval", action=action, args=args, approved=ok, how="terminal")
    if not ok:
        raise ApprovalDenied(f"{action} was not approved")
