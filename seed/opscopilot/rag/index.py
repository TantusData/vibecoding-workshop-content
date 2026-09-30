# CONTRACT — Tomasz left these bodies unfinished (plan item 7, HANDOVER_NOTE.md). Signatures, docstrings,
# dataclasses and constants are the interface the tests and the rest of the app rely
# on; keep them. Empty pattern lists are yours to fill.
# ruff: noqa: E501, F401  (generated from the reference; keep the imports for your implementation)
"""opscopilot/rag/index.py — a hand-rolled flat vector index over the wiki chunks.

Purpose:      Brute-force cosine search with numpy — no vector DB. The corpus is small (tens of
              pages) so a matrix product is fast enough, and the mechanics stay visible. Persisted
              as `<dir>/vectors.npy` + `<dir>/chunks.json` (sidecar with ids, page ids, texts and
              a fingerprint of the corpus + settings), rebuilt when the fingerprint changes.
Entry points: FlatIndex.build(pages, embedder), .search(query, k), .save(dir), .load(dir),
              fingerprint(pages, embedder_name)
Depends on:   numpy, opscopilot.rag.chunk, opscopilot.rag.embed, opscopilot.config
Used by:      opscopilot.rag.retrieve
Invariants:   Vector row i corresponds to chunks[i]. Scores are cosine similarities in [-1, 1].
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from opscopilot.config import settings
from opscopilot.rag.chunk import chunk_page
from opscopilot.rag.embed import Embedder
from opscopilot.rag.retrieve import Chunk


def fingerprint(pages: list[dict], embedder_name: str) -> str:
    """Changes when any page text, the embedder, or the chunking settings change."""
    raise NotImplementedError("TODO (plan item 7): implement fingerprint")


@dataclass
class FlatIndex:
    chunks: list[Chunk] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    fingerprint: str = ""
    embedder_name: str = ""

    @classmethod
    def build(cls, pages: list[dict], embedder: Embedder) -> FlatIndex:
        raise NotImplementedError("TODO (plan item 7): implement FlatIndex.build")

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[Chunk]:
        raise NotImplementedError("TODO (plan item 7): implement FlatIndex.search")

    def save(self, directory: Path) -> None:
        raise NotImplementedError("TODO (plan item 7): implement FlatIndex.save")

    @classmethod
    def load(cls, directory: Path) -> FlatIndex | None:
        raise NotImplementedError("TODO (plan item 7): implement FlatIndex.load")
