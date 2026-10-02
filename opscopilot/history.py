# CONTRACT — Tomasz left these bodies unfinished (plan item 3, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/history.py — the conversation window handed to the model on each turn.

Purpose:      Turns a session's stored messages into the prior turns for the router and the
              answer call: the last N user/assistant messages, capped by estimated tokens,
              oldest dropped first, never split. How earlier *tool results* are treated is a
              setting, because it is the lesson: `replay` (default — the naive memory that goes
              stale), `drop` (text only; the plan item 2 re-fetch rule restored), `summarise` (a one-line
              "you looked up X" so the model knows to fetch again). Live finding: none of the
              three stops a stale answer on its own — the assistant's *own earlier words* are
              cache too, and a prompt rule alone did not stop the router picking from_history.
              The fix that works is control flow (`refetch()` + `is_state_question()` +
              `last_tool_call()`): a state question routed to memory is overridden and the last
              ticket lookup re-run. Default off so the failure can be shown first.
Entry points: window(session_id) -> list[Message], record_turn(session_id, question, answer,
              tool_calls), router_history_option(), refetch(), is_state_question(),
              last_tool_call(). Env: OPSCOPILOT_HISTORY_MESSAGES
              (20), OPSCOPILOT_HISTORY_TOKENS (6000), OPSCOPILOT_HISTORY_TOOL_RESULTS (replay),
              OPSCOPILOT_HISTORY_REFETCH (0)
Depends on:   opscopilot.store
Used by:      opscopilot.cli.ask
Invariants:   A window never exceeds the message or token cap. Messages alternate user /
              assistant as the model API requires (tool rows fold into the assistant turn).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from opscopilot import store

Message = dict[str, str]


def max_messages() -> int:
    return int(os.environ.get("OPSCOPILOT_HISTORY_MESSAGES", "20"))


def max_tokens() -> int:
    return int(os.environ.get("OPSCOPILOT_HISTORY_TOKENS", "6000"))


def tool_results_mode() -> str:
    mode = os.environ.get("OPSCOPILOT_HISTORY_TOOL_RESULTS", "replay").lower()
    if mode not in ("replay", "drop", "summarise"):
        raise ValueError("OPSCOPILOT_HISTORY_TOOL_RESULTS must be replay | drop | summarise")
    return mode


def refetch() -> bool:
    """OPSCOPILOT_HISTORY_REFETCH=1: the router may not answer state questions from memory."""
    return os.environ.get("OPSCOPILOT_HISTORY_REFETCH", "0") == "1"


FROM_HISTORY_OPTION = "  Also use final when the conversation so far already contains what is needed (a follow-up\n  about something already looked up or discussed) — no new lookup.\n"
FROM_HISTORY_REFETCH = "  The conversation so far may be used ONLY for what was *said* earlier (a name, a decision,\n  a summary). Never answer about the current state of a ticket or a system from it —\n  statuses, assignees, comments and priorities change; such a question always needs a fresh\n  tool call in this turn, even if the conversation already shows an answer.\n"
STATE_WORDS = re.compile(
    "(?i)\\b(status|open|closed|resolved|fixed|still|now|current(ly)?|latest|update[ds]?|assigned|who is on|who's on|working on|progress)\\b|\\b(?:status\\w*|otwart\\w*|zamknię\\w*|rozwiązan\\w*|naprawion\\w*|nadal|wciąż|teraz|obecnie|aktualn\\w*|przypisan\\w*|pracuj\\w*|postęp\\w*)"
)


def is_state_question(question: str) -> bool:
    """Does the question ask about something that changes (state), not about what was said?"""
    return bool(STATE_WORDS.search(question))


def last_tool_call(session_id: str) -> tuple[str, dict[str, Any]] | None:
    """The most recent tool call of the session (what a state follow-up should re-run)."""
    raise NotImplementedError("TODO (plan item 3): implement last_tool_call")


def router_history_option() -> str:
    """The memory guidance for route.md's `final` option: naive by default, guarded with refetch."""
    return FROM_HISTORY_REFETCH if refetch() else FROM_HISTORY_OPTION


def record_turn(
    session_id: str,
    question: str,
    answer: str,
    tool_calls: list[tuple[str, dict[str, Any], Any]] | None = None,
) -> None:
    """Persist one exchange: the user turn, this turn's tool calls/results, the assistant turn."""
    raise NotImplementedError("TODO (plan item 3): implement record_turn")


def _fold(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    """Merge tool rows into the assistant turn that used them, per the configured mode."""
    raise NotImplementedError("TODO (plan item 3): implement _fold")


def window(session_id: str) -> list[Message]:
    """Prior turns for the model: last N messages under the token cap, oldest dropped first."""
    raise NotImplementedError("TODO (plan item 3): implement window")
