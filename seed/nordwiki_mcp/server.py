"""nordwiki_mcp/server.py — the Nordwiki MCP server (stdio), exposing the corpus functions as tools.

Purpose:      A thin MCP layer over nordwiki_mcp.corpus, the same shape as norddesk_mcp.server so a
              client written for one is a copy-and-rename away from the other.
Entry points: mcp (FastMCP instance), run() — tools: list_pages, get_page, search_pages
Depends on:   mcp.server.fastmcp.FastMCP, nordwiki_mcp.corpus
Used by:      nordwiki_mcp.__main__ (`serve`), opscopilot.mcp_wiki.client (once wired)
Invariants:   Read-only; tool names are the contract the client is written against.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from nordwiki_mcp import corpus

mcp = FastMCP(
    "nordwiki",
    log_level="WARNING",  # keep stderr quiet for CLI users
    instructions=(
        "Nordwiki — Nordfarm Foods' internal documentation (fake, a folder of markdown pages). "
        "Tools: list_pages, search_pages, get_page. Read-only."
    ),
)


@mcp.tool()
def list_pages() -> list[dict]:
    """List every wiki page: id, title, path, word count."""
    return corpus.list_pages()


@mcp.tool()
def get_page(page_id: str) -> dict:
    """Get one page in full by id (the file name without .md), e.g. 'vpn-setup'."""
    return corpus.get_page(page_id)


@mcp.tool()
def search_pages(query: str, limit: int = 5) -> list[dict]:
    """Keyword search over all pages; returns the best matches with a short snippet."""
    return corpus.search_pages(query, limit=limit)


def run() -> None:
    mcp.run(transport="stdio")
