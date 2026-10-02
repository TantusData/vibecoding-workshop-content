"""Fixed-input tests for opscopilot.rag.chunk — pure functions, exact outputs."""

from __future__ import annotations

import pytest

from opscopilot.rag.chunk import chunk_page, chunk_text

WORDS = " ".join(f"w{i}" for i in range(10))  # "w0 w1 ... w9"


def test_chunk_page_ids_and_title_prefix():
    chunks = chunk_page("p", "My Title", WORDS, size=5, overlap=0, title_prefix=True)
    assert [c.id for c in chunks] == ["p#0", "p#1"]
    assert chunks[0].page_id == "p"
    assert chunks[0].text == "My Title — w0 w1 w2 w3 w4"
    assert chunks[1].text == "My Title — w5 w6 w7 w8 w9"


