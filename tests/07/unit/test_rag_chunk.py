"""Fixed-input tests for opscopilot.rag.chunk — pure functions, exact outputs."""

from __future__ import annotations

import pytest

from opscopilot.rag.chunk import chunk_page, chunk_text

WORDS = " ".join(f"w{i}" for i in range(10))  # "w0 w1 ... w9"


def test_chunk_text_windows_with_overlap():
    assert chunk_text(WORDS, size=4, overlap=1) == [
        "w0 w1 w2 w3",
        "w3 w4 w5 w6",
        "w6 w7 w8 w9",
    ]


def test_chunk_text_without_overlap_and_short_tail():
    assert chunk_text(WORDS, size=4, overlap=0) == ["w0 w1 w2 w3", "w4 w5 w6 w7", "w8 w9"]
    assert chunk_text("one two", size=10, overlap=2) == ["one two"]
    assert chunk_text("   ", size=4, overlap=0) == []


def test_chunk_text_rejects_bad_settings():
    with pytest.raises(ValueError):
        chunk_text(WORDS, size=4, overlap=4)
    with pytest.raises(ValueError):
        chunk_text(WORDS, size=0, overlap=0)


def test_chunk_page_without_title_prefix_is_the_raw_window():
    chunks = chunk_page("p", "My Title", WORDS, size=5, overlap=0, title_prefix=False)
    assert chunks[0].text == "w0 w1 w2 w3 w4"
