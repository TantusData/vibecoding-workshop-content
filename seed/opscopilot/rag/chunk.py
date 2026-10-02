# CONTRACT — Tomasz left these bodies unfinished (plan item 7, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/rag/chunk.py — split wiki pages into retrievable chunks.

Purpose:      Word-window chunking with overlap, one chunk list per page. Every chunk is prefixed
              with the page title ("<title> — <text>") so a chunk far down a long page still
              carries the page's subject: this is what fixes the KX-90 case, where the model name
              is ~700 words away from the lockout facts (see docs/LOGIC_LOG.md, plan item 7).
Entry points: chunk_page(page_id, title, text, size, overlap) -> list[Chunk], chunk_text()
Depends on:   opscopilot.rag.retrieve.Chunk (the model), opscopilot.config (defaults)
Used by:      opscopilot.rag.index (build)
Invariants:   Chunk ids are "<page_id>#<n>", n from 0, stable for the same text and settings.
              overlap < size. The title prefix is part of the embedded text but is *not*
              counted towards `size`.
"""

from __future__ import annotations

from opscopilot.config import settings
from opscopilot.rag.retrieve import Chunk


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Windows of `size` words stepping by `size - overlap`; the last window may be shorter."""
    raise NotImplementedError("TODO (plan item 7): implement chunk_text")


def chunk_page(
    page_id: str,
    title: str,
    text: str,
    size: int | None = None,
    overlap: int | None = None,
    title_prefix: bool | None = None,
) -> list[Chunk]:
    """Chunk one page; settings supply the defaults (RAG_CHUNK_WORDS / RAG_CHUNK_OVERLAP / ...)."""
    raise NotImplementedError("TODO (plan item 7): implement chunk_page")
