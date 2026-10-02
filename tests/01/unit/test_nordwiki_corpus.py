"""Fixed-input tests for the Nordwiki server's functions — no MCP, no model, no agent."""

from __future__ import annotations

import pytest

from nordwiki_mcp import corpus

ALL_PAGES = [
    "hr-salary-bands-2026",
    "label-printer-zebra-troubleshooting",
    "mes-restart-packing-line",
    "palletiser-kx90-maintenance",
    "sop-backup-restore",
    "vpn (use this one)",
    "vpn-setup-v2-FINAL",
    "vpn-setup",
]


def test_list_pages_returns_every_markdown_page_sorted_and_skips_underscore_files():
    pages = corpus.list_pages()
    assert [p["id"] for p in pages] == ALL_PAGES
    assert all(set(p) == {"id", "title", "path", "words"} for p in pages)
    assert "_ground_truth" not in [p["id"] for p in pages]


def test_get_page_returns_title_and_full_content():
    page = corpus.get_page("vpn (use this one)")
    assert page["title"] == "VPN — quick card (use this one)"
    assert page["path"] == "vpn (use this one).md"
    assert page["content"].startswith("# VPN — quick card (use this one)")
    assert corpus.get_page("nope") == {"error": "page 'nope' not found"}


def test_search_pages_ranks_by_keyword_count_with_title_boost():
    hits = corpus.search_pages("VPN setup")
    assert [h["id"] for h in hits] == ["vpn-setup-v2-FINAL", "vpn-setup", "vpn (use this one)"]
    assert hits[0]["score"] > hits[1]["score"] > hits[2]["score"]
    assert "snippet" in hits[0]


def test_search_pages_short_or_empty_queries_return_nothing():
    assert corpus.search_pages("") == []
    assert corpus.search_pages("a of") == []


def test_search_is_naive_keyword_matching_not_semantic():
    """Documented weakness: the KX-90 lockout facts are found by word overlap only."""
    hits = corpus.search_pages("cool-down before opening the drive panel")
    assert hits[0]["id"] == "palletiser-kx90-maintenance"
    # ...and a paraphrase with no shared words finds nothing useful
    assert [
        h["id"] for h in corpus.search_pages("waiting period prior to accessing electronics")
    ] != ["palletiser-kx90-maintenance"]


def test_corpus_is_reread_on_every_call(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDWIKI_ROOT", str(tmp_path))
    (tmp_path / "one.md").write_text("# One\n\nalpha beta\n")
    assert [p["id"] for p in corpus.list_pages()] == ["one"]
    (tmp_path / "two.md").write_text("# Two\n\ngamma\n")
    assert [p["id"] for p in corpus.list_pages()] == ["one", "two"]
    assert corpus.search_pages("gamma")[0]["id"] == "two"


def test_wiki_root_missing_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDWIKI_ROOT", str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="NORDWIKI_ROOT"):
        corpus.list_pages()
