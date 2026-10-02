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
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("need size > 0 and 0 <= overlap < size")
    words = text.split()
    if not words:
        return []
    step = size - overlap
    out = []
    for start in range(0, len(words), step):
        out.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return out


def chunk_page(
    page_id: str,
    title: str,
    text: str,
    size: int | None = None,
    overlap: int | None = None,
    title_prefix: bool | None = None,
) -> list[Chunk]:
    """Chunk one page; settings supply the defaults (RAG_CHUNK_WORDS / RAG_CHUNK_OVERLAP / ...)."""
    size = settings.rag_chunk_words if size is None else size
    overlap = settings.rag_chunk_overlap if overlap is None else overlap
    title_prefix = settings.rag_title_prefix if title_prefix is None else title_prefix
    chunks = []
    for n, body in enumerate(chunk_text(text, size, overlap)):
        chunks.append(
            Chunk(
                id=f"{page_id}#{n}",
                page_id=page_id,
                text=f"{title} — {body}" if title_prefix else body,
            )
        )
    return chunks
