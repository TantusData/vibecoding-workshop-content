"""opscopilot/rag/embed.py — text -> vector, with a real backend and a deterministic fake.

Purpose:      `GatewayEmbedder` asks the company's LiteLLM gateway for embeddings (`titan-embed`
              = Amazon Titan Text Embeddings V2, 1024 dimensions) with the user's own
              virtual key — no local model, nothing to download. `FakeEmbedder`
              (EMBEDDINGS_BACKEND=fake) is a
              hashed bag-of-words vector — no model, no download, fully deterministic — so the
              retrieval *mechanics* can be unit-tested; it is not a stand-in for quality.
Entry points: get_embedder() -> Embedder, Embedder.embed(texts) -> np.ndarray (rows L2-normalised),
              Embedder.name
Depends on:   numpy; httpx (real backend only); opscopilot.config
Used by:      opscopilot.rag.index, opscopilot.rag.retrieve
Invariants:   Output rows are unit-length so cosine similarity is a dot product. The fake never
              opens a network connection. One text per request (the gateway's Titan route embeds
              one input at a time); the index is built once and cached on disk.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Protocol

import numpy as np

from opscopilot.config import settings

_WORD = re.compile(r"[a-z0-9][a-z0-9\-]+")


def _normalise(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class FakeEmbedder:
    """Hashed bag-of-words: each word (and word bigram) bumps one of `dim` buckets."""

    name = "fake-bow"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            words = _WORD.findall(text.lower())
            for tok in words + [a + "_" + b for a, b in zip(words, words[1:], strict=False)]:
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)  # noqa: S324 - not security
                out[row, h % self.dim] += 1.0
        return _normalise(out)


class GatewayEmbedder:
    """Embeddings from the LiteLLM gateway (`EMBEDDINGS_MODEL`, default titan-embed)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.embeddings_model
        self.name = self.model  # part of the index fingerprint: a new model rebuilds the index

    def embed(self, texts: list[str]) -> np.ndarray:
        import httpx

        key = settings.litellm_virtual_key
        if not key:
            raise RuntimeError("LITELLM_VIRTUAL_KEY is not set — the model gateway needs it")
        url = settings.litellm_base_url.rstrip("/") + "/embeddings"
        rows = []
        with httpx.Client(headers={"Authorization": f"Bearer {key}"}, timeout=60) as client:
            for text in texts:
                response = client.post(url, json={"model": self.model, "input": text})
                response.raise_for_status()
                rows.append(response.json()["data"][0]["embedding"])
        return _normalise(np.asarray(rows, dtype=np.float32))


_cached: Embedder | None = None


def get_embedder() -> Embedder:
    """EMBEDDINGS_BACKEND=fake -> FakeEmbedder; anything else -> the gateway (titan-embed)."""
    global _cached
    backend = os.environ.get("EMBEDDINGS_BACKEND", settings.embeddings_backend).lower()
    if backend == "fake":
        return FakeEmbedder()
    if _cached is None:
        _cached = GatewayEmbedder()
    return _cached
