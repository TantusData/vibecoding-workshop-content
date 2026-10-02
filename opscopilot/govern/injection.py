# CONTRACT — Tomasz left these bodies unfinished (plan item 6, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
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

MARKERS: list[tuple[str, re.Pattern[str]]] = []
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
EXTERNAL_EMAIL = re.compile("\\b[\\w.+-]+@(?!nordfarm\\.example\\b)[\\w-]+\\.[\\w.-]+\\b")


class Hit(BaseModel):
    kind: str
    where: str
    excerpt: str


def scan(text: str, where: str = "text") -> list[Hit]:
    raise NotImplementedError("TODO (plan item 6): implement scan")


def _paragraphs(text: str) -> list[str]:
    return re.split("\\n\\s*\\n", text)


def sanitize_docs(chunks: list[Chunk]) -> tuple[list[Chunk], list[Hit]]:
    """Drop every paragraph (and, for single-paragraph chunks, every sentence) that scan() flags."""
    raise NotImplementedError("TODO (plan item 6): implement sanitize_docs")


def allowed_tools(question: str) -> set[str]:
    """Reads always; writes only when the request itself carries no injection markers."""
    raise NotImplementedError("TODO (plan item 6): implement allowed_tools")


def scan_output(text: str) -> tuple[str, list[Hit]]:
    """Output scanner: strip external e-mail addresses and any secret that slipped through."""
    raise NotImplementedError("TODO (plan item 6): implement scan_output")
