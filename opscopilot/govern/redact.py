# CONTRACT — Tomasz left these bodies unfinished (plan item 6, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/govern/redact.py — strip credentials and identifiers before text reaches a prompt/log.

Purpose:      Regex-based redaction (deliberately no presidio): pasted passwords and user/pass
              pairs, API keys and bearer tokens, PESEL numbers, badge ids. Applied at the boundary
              where tool results and ticket text enter a prompt, and to every audit-log line.
              Business phone numbers and names are NOT redacted — the on-call table needs them.
Entry points: redact(text) -> Redaction, redact_obj(obj) -> (obj, findings), PATTERNS
Depends on:   re (stdlib), pydantic
Used by:      opscopilot.cli (tool results), opscopilot.report (gather), opscopilot.govern.audit
Invariants:   Idempotent: redact(redact(x).text).text == redact(x).text. Never raises on any
              string. Findings name the kind, never the secret itself.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

PATTERNS: list[tuple[str, re.Pattern[str]]] = []


class Finding(BaseModel):
    kind: str
    count: int


class Redaction(BaseModel):
    text: str
    findings: list[Finding] = []

    @property
    def changed(self) -> bool:
        return bool(self.findings)


def redact(text: str) -> Redaction:
    """Replace every secret with `[REDACTED:<kind>]`; report what kinds were hit, how often."""
    raise NotImplementedError("TODO (plan item 6): implement redact")


def redact_obj(obj: Any) -> tuple[Any, list[Finding]]:
    """Walk dicts/lists/strings (tool results) and redact every string in place."""
    raise NotImplementedError("TODO (plan item 6): implement redact_obj")
