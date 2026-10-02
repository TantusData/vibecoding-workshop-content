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

    id: str  # "<page-id>#<n>"
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
    from opscopilot.mcp_wiki import client as wiki
    from opscopilot.rag.embed import get_embedder
    from opscopilot.rag.index import FlatIndex, fingerprint

    pages = wiki.run(wiki.fetch_corpus())
    embedder = get_embedder()
    cached = FlatIndex.load(index_dir())
    if cached is not None and cached.fingerprint == fingerprint(pages, embedder.name):
        return cached
    index = FlatIndex.build(pages, embedder)
    index.save(index_dir())
    return index


def retrieve(query: str, k: int | None = None) -> list[Chunk]:
    """The k best chunks for `query`, best first, with cosine scores."""
    from opscopilot.rag.embed import get_embedder

    k = settings.rag_top_k if k is None else k
    index = build_or_load_index()
    query_vec = get_embedder().embed([query])[0]
    return index.search(query_vec, k=k)
