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

# (kind, pattern) — first match wins per span; keep the secret in one group named `secret`
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "password: x", "pw = x", "hasło: x", "pass x" — value = anything up to whitespace/quote
    (
        "credential",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|pw|pass|hasło|haslo)\b\s*(?:is|=|:|-)?\s*"
            r"(?P<secret>[^\s\"'`,;]{4,})"
        ),
    ),
    # "user / pass" pairs as people paste them: "mesadmin / Nordf@rm2026!"
    (
        "credential",
        re.compile(r"\b(?P<user>[a-z][a-z0-9_.-]{2,})\s*/\s*(?P<secret>\S*[@#$%!?]\S*)"),
    ),
    ("aws-key", re.compile(r"\b(?P<secret>AKIA[0-9A-Z]{16})\b")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+(?P<secret>[a-z0-9._~+/=-]{16,})")),
    ("api-key", re.compile(r"\b(?P<secret>sk-[A-Za-z0-9]{16,})\b")),
    ("pesel", re.compile(r"\b(?P<secret>\d{11})\b")),
    ("badge", re.compile(r"(?i)\bbadge\s*(?:no\.?|number|#)?\s*(?P<secret>\d{4,6})\b")),
]


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
    counts: dict[str, int] = {}
    out = text
    for kind, pattern in PATTERNS:

        def _sub(m: re.Match[str], kind: str = kind) -> str:
            counts[kind] = counts.get(kind, 0) + 1
            start, end = m.span("secret")
            return m.string[m.start() : start] + f"[REDACTED:{kind}]" + m.string[end : m.end()]

        out = pattern.sub(_sub, out)
    return Redaction(text=out, findings=[Finding(kind=k, count=v) for k, v in counts.items()])


def redact_obj(obj: Any) -> tuple[Any, list[Finding]]:
    """Walk dicts/lists/strings (tool results) and redact every string in place."""
    counts: dict[str, int] = {}

    def walk(node: Any) -> Any:
        if isinstance(node, str):
            r = redact(node)
            for f in r.findings:
                counts[f.kind] = counts.get(f.kind, 0) + f.count
            return r.text
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return walk(obj), [Finding(kind=k, count=v) for k, v in counts.items()]
