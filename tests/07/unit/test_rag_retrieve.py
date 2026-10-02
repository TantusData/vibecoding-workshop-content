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


def test_fake_embedder_is_deterministic_and_unit_length():
    e = get_embedder()
    assert isinstance(e, FakeEmbedder)
    a = e.embed(["vpn setup portal", "palletiser lockout"])
    b = e.embed(["vpn setup portal", "palletiser lockout"])
    assert np.array_equal(a, b)
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)
    assert a[0] @ a[1] < a[0] @ e.embed(["vpn portal setup"])[0]


def test_retrieve_vpn_setup_returns_a_vpn_chunk_first():
    chunks = rag.retrieve("VPN setup", k=3)
    assert chunks[0].page_id.startswith("vpn")
    assert chunks[0].id.startswith(chunks[0].page_id + "#")
    assert chunks[0].score >= chunks[1].score >= chunks[2].score


def test_index_is_cached_and_rebuilt_only_when_the_corpus_changes(tmp_path, monkeypatch):
    rag.retrieve("anything", k=1)
    sidecar = rag.index_dir() / "chunks.json"
    first = json.loads(sidecar.read_text())["fingerprint"]
    rag.retrieve("anything else", k=1)
    assert json.loads(sidecar.read_text())["fingerprint"] == first  # untouched

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "only.md").write_text("# Only page\n\nzebra ribbon calibration\n")
    monkeypatch.setenv("NORDWIKI_ROOT", str(wiki))
    chunks = rag.retrieve("ribbon", k=1)
    assert chunks[0].page_id == "only"
    assert json.loads(sidecar.read_text())["fingerprint"] != first  # rebuilt


def test_index_is_rebuilt_when_the_chunking_code_changes(tmp_path, monkeypatch):
    # same settings, new chunk.py (e.g. the title prefix lands while RAG_TITLE_PREFIX is already
    # at its default): a cached index cut by the old code must not be reused
    from pathlib import Path

    from opscopilot.rag import chunk

    rag.retrieve("anything", k=1)
    sidecar = rag.index_dir() / "chunks.json"
    first = json.loads(sidecar.read_text())["fingerprint"]
    edited = tmp_path / "chunk.py"
    edited.write_bytes(Path(chunk.__file__).read_bytes() + b"\n# edited\n")
    monkeypatch.setattr(chunk, "__file__", str(edited))
    rag.retrieve("anything", k=1)
    assert json.loads(sidecar.read_text())["fingerprint"] != first  # rebuilt


def test_flat_index_roundtrip_and_ranking(tmp_path):
    pages = [
        {"id": "a", "title": "A", "content": "apples and pears"},
        {"id": "b", "title": "B", "content": "zebra printers and ribbons"},
    ]
    idx = FlatIndex.build(pages, FakeEmbedder())
    idx.save(tmp_path)
    loaded = FlatIndex.load(tmp_path)
    assert loaded is not None
    assert [c.id for c in loaded.chunks] == ["a#0", "b#0"]
    assert np.array_equal(loaded.vectors, idx.vectors)
    hit = loaded.search(FakeEmbedder().embed(["zebra ribbons"])[0], k=1)[0]
    assert hit.page_id == "b" and hit.score > 0
    assert FlatIndex.load(tmp_path / "nope") is None
