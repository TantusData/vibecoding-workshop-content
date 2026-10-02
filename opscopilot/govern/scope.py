# CONTRACT — Tomasz left these bodies unfinished (plan item 6, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/govern/scope.py — is this something OpsCopilot should answer at all?

Purpose:      Rules first, model second: deny patterns (policy circumvention, credentials,
              restricted/personal data, safety overrides) and allow patterns (our systems,
              ticket ids, ops vocabulary) decide most requests without a model call; only the
              ambiguous remainder goes to a structured classification with `scope.md`.
              Same rules -> LLM -> both progression as the rest of the app.
Entry points: classify(question, prior) -> ScopeDecision, rules(question) -> ScopeDecision | None,
              REFUSAL (the fixed reply), ScopeDecision
Depends on:   re (stdlib), pydantic, opscopilot.llm.client, opscopilot/llm/prompts/scope.md
Used by:      opscopilot.cli (first step of ask), scripts/eval_guardrails.py
Invariants:   A deny rule beats an allow rule. rules() never calls the model. The refusal text
              is one fixed string so tests and the gold set can match it exactly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from opscopilot.llm.client import get_llm_client

PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "scope.md"
REFUSAL = "I can only help with Nordfarm Foods IT/OT operations — tickets, our systems and our documented procedures — and I can't help route around a policy or share restricted data."
_TICKET = "(?:INC|REQ|CHG|Q)-\\d{3,5}"
_ALL_TICKETS = "\\b(?:all|every)\\s+(?:open\\s+)?tickets?\\b"
_SEND = "\\b(?:e-?mail|send|forward|export)\\b"
_PL_TICKETS = "\\b(?:wszystkie|każde)\\s+(?:otwarte\\s+)?zgłosze\\w*"
_PL_SEND = "\\b(?:wyślij|prześlij|wysłać|przesłać|wyeksportuj|mailem|e-?mailem)\\b"
DENY: list[tuple[str, re.Pattern[str]]] = []
ALLOW: list[tuple[str, re.Pattern[str]]] = []


class ScopeDecision(BaseModel):
    allowed: bool
    reason: str
    method: Literal["rule-deny", "rule-allow", "llm"]


class ScopeVerdict(BaseModel):
    in_scope: bool
    reason: str


def rules(question: str) -> ScopeDecision | None:
    """Deny beats allow; None means the rules could not decide."""
    raise NotImplementedError("TODO (plan item 6): implement rules")


def classify(question: str, prior: list[dict[str, str]] | None = None) -> ScopeDecision:
    """Rules on the current message, then the model — with the conversation so far, if any —
    for whatever the rules left undecided (a follow-up like "and who is on it?" has no keyword)."""
    raise NotImplementedError("TODO (plan item 6): implement classify")
