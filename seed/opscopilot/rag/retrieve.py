# CONTRACT — Tomasz left these bodies unfinished (plan item 7, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/rag/retrieve.py — retrieval over the Nordwiki corpus.

Purpose:      Given an operator question, return the most relevant chunks of our wiki pages so
              the model can answer from them instead of from memory. Pages come from the Nordwiki
              MCP server (one session, every page), get chunked and embedded into a flat numpy
              index that is cached on disk and rebuilt whenever the corpus or settings change.
Entry points: retrieve(query, k) -> list[Chunk], Chunk, build_or_load_index(), index_dir()
Depends on:   opscopilot.mcp_wiki.client (fetch_corpus), opscopilot.rag.{chunk,embed,index},
              opscopilot.config
Used by:      opscopilot.cli (ask's grounding step), scripts/eval_rag.py
Invariants:   retrieve() is a pure function of (corpus, settings, query) — no model call, no
              state beyond the on-disk cache. Chunks come back best-first with cosine scores.
              The fake embedder writes its cache to a separate directory so it never poisons the
              real index.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

from opscopilot.config import settings


class Chunk(BaseModel):
    """One retrievable piece of a wiki page."""

    id: str
    page_id: str
    text: str
    score: float = 0.0


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def index_dir() -> Path:
    base = Path(os.environ.get("RAG_INDEX_DIR", REPO_ROOT / "var" / "wiki_index"))
    backend = os.environ.get("EMBEDDINGS_BACKEND", settings.embeddings_backend).lower()
    return base / backend


def build_or_load_index():
    """Load the cached index if its fingerprint still matches the live corpus; else rebuild."""
    raise NotImplementedError("TODO (plan item 7): implement build_or_load_index")


def retrieve(query: str, k: int | None = None) -> list[Chunk]:
    """The k best chunks for `query`, best first, with cosine scores."""
    raise NotImplementedError("TODO (plan item 7): implement retrieve")
