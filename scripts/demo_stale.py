"""scripts/demo_stale.py — the stale-answer story with conversation memory, naive then fixed.

Purpose:      `python scripts/demo_stale.py`. Twice: ask about INC-1042, resolve the ticket on disk
              behind the assistant's back, ask "Is it still open?" — first with the naive memory
              (the router may answer from the conversation: a stale "yes"), then with
              OPSCOPILOT_HISTORY_REFETCH=1 (a state question re-runs the last lookup). Prints the
              route the router chose and the audit events so the mechanism is visible. Needs a real
              model.
Entry points: main()
Depends on:   opscopilot.cli, opscopilot.history, opscopilot.govern.audit, norddesk_mcp.store
Used by:      Makefile `demo-stale`
Invariants:   Fresh session and seeded store per round; store re-seeded at the end.
"""

from __future__ import annotations

import sys
from pathlib import Path

# run as `python scripts/<name>.py` from the project folder, with nothing installed: make the
# project importable (under uv it already is; this line then changes nothing)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import sys
import textwrap


def round_(label: str, refetch: bool) -> None:
    from norddesk_mcp import store as norddesk
    from opscopilot import cli, store
    from opscopilot.govern import audit

    os.environ["OPSCOPILOT_HISTORY_REFETCH"] = "1" if refetch else "0"
    norddesk.init_store(force=True)
    audit.audit_path().unlink(missing_ok=True)
    sid = store.new_session_id()
    print(f"\n{'=' * 78}\n{label}\n{'-' * 78}")
    print("Q1: Check INC-1042.")
    print(textwrap.indent(cli.ask("Check INC-1042.", session_id=sid).splitlines()[0], "    "))
    norddesk.post_update("INC-1042", "Sensor S3 realigned, line running again", status="resolved")
    print("    [meanwhile: the ticket is resolved on disk]")
    print("Q2: Is it still open? Who was on it?")
    print(textwrap.indent(cli.ask("Is it still open? Who was on it?", session_id=sid), "    "))
    routes = [
        e.get("tool")
        for e in audit.read_events()
        if e["kind"] == "model_call" and e["step"] == "route"
    ]
    refetches = [e for e in audit.read_events() if e["kind"] == "refetch"]
    print(f"\n    router chose: {routes}   refetch overrides: {len(refetches)}")


def main() -> int:
    if os.environ.get("LLM_PROVIDER", "litellm").lower() == "fake":
        print("needs a real LLM_PROVIDER", file=sys.stderr)
        return 2
    from norddesk_mcp import store as norddesk

    try:
        round_(
            "ROUND 1 — naive memory (OPSCOPILOT_HISTORY_REFETCH=0): the conversation is a cache",
            False,
        )
        round_("ROUND 2 — the fix (OPSCOPILOT_HISTORY_REFETCH=1): state questions re-fetch", True)
    finally:
        norddesk.init_store(force=True)
    print(
        "\nMemory made the assistant faster and cheaper — and wrong. Neither dropping old tool "
        "results nor a prompt rule fixed it; a control-flow rule did. Which of your questions are "
        "about state?"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
