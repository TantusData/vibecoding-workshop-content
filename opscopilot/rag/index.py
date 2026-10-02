"""opscopilot/rag/index.py — a hand-rolled flat vector index over the wiki chunks.

Purpose:      Brute-force cosine search with numpy — no vector DB. The corpus is small (tens of
              pages) so a matrix product is fast enough, and the mechanics stay visible. Persisted
              as `<dir>/vectors.npy` + `<dir>/chunks.json` (sidecar with ids, page ids, texts and
              a fingerprint of the corpus + settings + the chunking code), rebuilt when the
              fingerprint changes — so editing chunk.py rebuilds the index even when no setting
              moved (the title-prefix fix lands with RAG_TITLE_PREFIX already at its default).
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
    """Changes when any page text, the embedder, the chunking settings or the chunking code
    (rag/chunk.py) change — a cached index never outlives the code that cut it."""
    from opscopilot.rag import chunk

    h = hashlib.sha256()
    h.update(
        f"{embedder_name}|{settings.rag_chunk_words}|{settings.rag_chunk_overlap}|"
        f"{settings.rag_title_prefix}".encode()
    )
    h.update(Path(chunk.__file__).read_bytes())
    for p in sorted(pages, key=lambda p: p["id"]):
        h.update(p["id"].encode())
        h.update(p["content"].encode("utf-8"))
    return h.hexdigest()


@dataclass
class FlatIndex:
    chunks: list[Chunk] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    fingerprint: str = ""
    embedder_name: str = ""

    @classmethod
    def build(cls, pages: list[dict], embedder: Embedder) -> FlatIndex:
        chunks: list[Chunk] = []
        for page in pages:
            chunks.extend(chunk_page(page["id"], page["title"], page["content"]))
        vectors = embedder.embed([c.text for c in chunks]) if chunks else np.zeros((0, 1))
        return cls(
            chunks=chunks,
            vectors=vectors,
            fingerprint=fingerprint(pages, embedder.name),
            embedder_name=embedder.name,
        )

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[Chunk]:
        if not self.chunks:
            return []
        scores = self.vectors @ query_vec.reshape(-1)
        order = np.argsort(-scores, kind="stable")[:k]
        return [self.chunks[i].model_copy(update={"score": float(scores[i])}) for i in order]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "vectors.npy", self.vectors)
        sidecar = {
            "fingerprint": self.fingerprint,
            "embedder": self.embedder_name,
            "chunks": [c.model_dump(exclude={"score"}) for c in self.chunks],
        }
        (directory / "chunks.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> FlatIndex | None:
        try:
            sidecar = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
            vectors = np.load(directory / "vectors.npy")
        except (OSError, ValueError):
            return None
        return cls(
            chunks=[Chunk(**c) for c in sidecar["chunks"]],
            vectors=vectors,
            fingerprint=sidecar["fingerprint"],
            embedder_name=sidecar["embedder"],
        )
