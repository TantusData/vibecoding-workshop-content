"""opscopilot/govern/injection.py — keep instructions out of data: retrieved docs and tool output.

Purpose:      Three plain-Python controls (no model): (1) `scan()` flags instruction-like text
              addressed to an assistant ("Assistant: …", "ignore your instructions", "email all …
              to …@…", "does not need approval"); (2) `sanitize_docs()` removes flagged paragraphs
              from retrieved chunks before they enter a prompt and records what was removed;
              (3) `allowed_tools()` is the tool allowlist per path — writes are never allowed
              when the request itself carries injection markers. `scan_output()` is the output
              scanner: external e-mail addresses and residual secrets are stripped from answers.
Entry points: scan(text) -> list[Hit], sanitize_docs(chunks) -> (chunks, hits),
              allowed_tools(question) -> set[str], scan_output(text) -> (text, hits), Hit
Depends on:   re (stdlib), pydantic, opscopilot.govern.redact, opscopilot.rag.retrieve.Chunk
Used by:      opscopilot.cli (docs path, tool step, answers), opscopilot.report
Invariants:   scan() hits are ordered by kind name (stable whatever MARKERS' order).
              Never mutates the corpus; sanitisation happens on the retrieved copy. A doc is
              data: nothing found by scan() is ever executed, only removed and logged.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from opscopilot.govern.redact import redact
from opscopilot.rag.retrieve import Chunk

MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("addressed-to-assistant", re.compile(r"(?im)^\s*(?:\*\*)?assistant\s*(?:note)?\s*[:：]")),
    ("addressed-to-assistant", re.compile(r"(?i)\bif you are an (?:ai|llm|assistant)\b")),
    (
        "override",
        re.compile(
            r"(?i)\bignore\s+(?:all\s+|any\s+)?(?:your|the|previous|prior|above)\s+\w*\s*instructions?\b"
        ),
    ),
    (
        "override",
        re.compile(r"(?i)\b(?:you are now|new instructions?|system prompt|developer message)\b"),
    ),
    (
        "override",
        re.compile(r"(?i)\bzignoruj\w*\s+(?:\w+\s+){0,2}(?:instrukcj\w*|polece\w*|zasad\w*)"),
    ),
    (
        "exfiltration",
        re.compile(
            r"(?i)\b(?:e-?mail|send|forward|post|upload|export)\b[^.]{0,30}"
            r"\b(?:tickets?|comments?|records?|data|database|credentials?|passwords?|logs?)\b"
            r"[^.]{0,80}\b(?:to|at)\s+[\w.+-]+@[\w-]+\.[\w.-]+"
        ),
    ),
    (
        "exfiltration",
        re.compile(
            r"(?i)\b(?:all|every)\s+(?:open\s+)?tickets?\b[^.]{0,60}\b(?:e-?mail|send|forward|export)\b"
        ),
    ),
    (
        "approval-bypass",
        re.compile(r"(?i)\b(?:does not|doesn't|no)\s+need\s+(?:user\s+|human\s+)?approval\b"),
    ),
    (
        "approval-bypass",
        re.compile(r"(?i)\bnie\s+(?:wymaga\w*|potrzebuj\w*)\s+(?:\w+\s+)?(?:zgody|zatwierdzenia)"),
    ),
]

READ_TOOLS = {
    "get_ticket",
    "search_tickets",
    "get_system_status",
    "get_oncall",
    "impact_estimate",
    "search_docs",
    "final",
}
WRITE_TOOLS = {"create_ticket", "post_update"}
EXTERNAL_EMAIL = re.compile(r"\b[\w.+-]+@(?!nordfarm\.example\b)[\w-]+\.[\w.-]+\b")


class Hit(BaseModel):
    kind: str
    where: str  # chunk id / "question" / "answer"
    excerpt: str  # first ~60 chars of the offending text, for the audit log


def scan(text: str, where: str = "text") -> list[Hit]:
    hits = []
    for kind, pattern in MARKERS:
        for m in pattern.finditer(text):
            hits.append(Hit(kind=kind, where=where, excerpt=m.group(0)[:60]))
    return sorted(hits, key=lambda h: h.kind)  # by kind name: stable whatever the MARKERS order


def _paragraphs(text: str) -> list[str]:
    return re.split(r"\n\s*\n", text)


def sanitize_docs(chunks: list[Chunk]) -> tuple[list[Chunk], list[Hit]]:
    """Drop every paragraph (and, for single-paragraph chunks, every sentence) that scan() flags."""
    out: list[Chunk] = []
    hits: list[Hit] = []
    for c in chunks:
        kept = []
        for para in _paragraphs(c.text):
            found = scan(para, where=c.id)
            if not found:
                kept.append(para)
                continue
            hits.extend(found)
            # keep the harmless sentences of a mixed paragraph
            clean = [s for s in re.split(r"(?<=[.!?])\s+", para) if not scan(s)]
            kept.append(" ".join(clean) + " [removed: instruction-like text]")
        out.append(c.model_copy(update={"text": "\n\n".join(kept)}))
    return out, hits


def allowed_tools(question: str) -> set[str]:
    """Reads always; writes only when the request itself carries no injection markers."""
    return READ_TOOLS if scan(question, "question") else READ_TOOLS | WRITE_TOOLS


def scan_output(text: str) -> tuple[str, list[Hit]]:
    """Output scanner: strip external e-mail addresses and any secret that slipped through."""
    hits = [
        Hit(kind="external-email", where="answer", excerpt=m.group(0))
        for m in EXTERNAL_EMAIL.finditer(text)
    ]
    cleaned = EXTERNAL_EMAIL.sub("[removed: external address]", text)
    r = redact(cleaned)
    hits += [Hit(kind=f"secret:{f.kind}", where="answer", excerpt="") for f in r.findings]
    return r.text, hits
