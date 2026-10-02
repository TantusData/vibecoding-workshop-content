"""Fixed-input tests for the Nordwiki MCP *client* — real server subprocess over stdio, no model."""

from __future__ import annotations

from nordwiki_mcp import corpus
from opscopilot.mcp_wiki import client


def test_list_pages_over_mcp_matches_the_server_function():
    assert client.run(client.list_pages()) == corpus.list_pages()


def test_get_page_over_mcp_returns_full_content_and_errors_as_dicts():
    page = client.run(client.get_page("sop-backup-restore"))
    assert page == corpus.get_page("sop-backup-restore")
    assert "Assistant note" in page["content"]  # the CP4 injection fixture rides along untouched
    assert client.run(client.get_page("nope")) == {"error": "page 'nope' not found"}


def test_search_pages_over_mcp():
    hits = client.run(client.search_pages("VPN setup", limit=2))
    assert [h["id"] for h in hits] == ["vpn-setup-v2-FINAL", "vpn-setup"]
    assert client.run(client.search_pages("")) == []


def test_fetch_corpus_returns_every_page_in_one_session():
    pages = client.run(client.fetch_corpus())
    assert [p["id"] for p in pages] == [p["id"] for p in corpus.list_pages()]
    assert all("content" in p for p in pages)


def test_client_forwards_nordwiki_root(tmp_path, monkeypatch):
    (tmp_path / "solo.md").write_text("# Solo page\n\nonly one here\n")
    monkeypatch.setenv("NORDWIKI_ROOT", str(tmp_path))
    assert [p["id"] for p in client.run(client.list_pages())] == ["solo"]
