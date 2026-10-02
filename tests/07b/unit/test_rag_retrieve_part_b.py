"""Fixed-input tests for opscopilot.rag.retrieve — real Nordwiki server, fake embedder, no LLM.

The fake embedder is a hashed bag-of-words, so these tests prove the *mechanics* (fetch → chunk →
index → search → cache) with a deterministic ranking; retrieval *quality* with the real model is
graded by `make eval` against data/eval/rag_gold.jsonl.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from opscopilot.rag import retrieve as rag
from opscopilot.rag.embed import FakeEmbedder, get_embedder
from opscopilot.rag.index import FlatIndex


@pytest.fixture(autouse=True)
def fake_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))


def test_retrieve_kx90_lockout_returns_the_chunk_with_the_answer():
    """The CP2 chunking case: the answer sits ~700 words below the only 'KX-90' mention."""
    chunks = rag.retrieve("KX-90 cool-down before opening the drive panel", k=4)
    assert chunks[0].page_id == "palletiser-kx90-maintenance"
    assert "20-minute cool-down" in chunks[0].text
    # the lockout section is ~330 words, i.e. three 120-word chunks: the model needs the top-k
    # *together* to see all three facts — chunk size is the lever, not the model
    seen = " ".join(c.text for c in chunks)
    assert "Two-person sign-off" in seen and "P3-07" in seen


def test_without_title_prefix_the_kx90_chunk_loses_the_model_name(monkeypatch):
    """Why the title prefix exists: the answer chunk itself never says 'KX-90'."""
    monkeypatch.setattr(rag.settings, "rag_title_prefix", False)
    chunks = rag.retrieve("KX-90 cool-down before opening the drive panel", k=1)
    assert "KX-90" not in chunks[0].text


