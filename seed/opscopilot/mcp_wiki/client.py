"""opscopilot/mcp_wiki/client.py — Nordwiki (internal docs) MCP client.

Purpose:      Talk to the Nordwiki MCP server (`nordwiki_mcp/`, stdio — a folder of markdown pages,
              not real Confluence) so OpsCopilot can read our runbooks and SOPs. Same shape as the
              tickets client: one fresh session per call, decoded JSON back, nothing cached.
              `fetch_corpus()` pulls every page in one session for the retrieval index.
Entry points: connect(), call_tool(name, args); list_pages(), get_page(), search_pages(),
              fetch_corpus() — async — plus run(coro) for sync callers
Depends on:   mcp (ClientSession, stdio_client), nordwiki_mcp (the server it launches)
Used by:      opscopilot.rag.retrieve (fetch_corpus)
Invariants:   Read-only — the server has no write tools, so no approval gate is needed here.
              NORDWIKI_ROOT is forwarded to the server subprocess.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

T = TypeVar("T")
LIST_TOOLS = {"list_pages", "search_pages"}


def server_params() -> StdioServerParameters:
    env = get_default_environment()
    for key in ("NORDWIKI_ROOT", "PYTHONPATH"):
        if key in os.environ:
            env[key] = os.environ[key]
    return StdioServerParameters(
        command=sys.executable, args=["-m", "nordwiki_mcp", "serve"], env=env
    )


@asynccontextmanager
async def connect() -> AsyncIterator[ClientSession]:
    """Open a stdio session to the Nordwiki MCP server and initialise the handshake."""
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _decode(name: str, result: Any) -> Any:
    if result.isError:
        raise RuntimeError(f"Nordwiki tool {name} failed: {result.content}")
    decoded = [json.loads(c.text) for c in result.content if getattr(c, "type", "") == "text"]
    if name in LIST_TOOLS:
        return decoded
    return decoded[0] if decoded else None


async def call_tool(name: str, args: dict[str, Any]) -> Any:
    """One tool call on a fresh session; the server's JSON, decoded."""
    async with connect() as session:
        return _decode(name, await session.call_tool(name, args))


async def list_pages() -> list[dict]:
    return await call_tool("list_pages", {})


async def get_page(page_id: str) -> dict:
    return await call_tool("get_page", {"page_id": page_id})


async def search_pages(query: str, limit: int = 5) -> list[dict]:
    return await call_tool("search_pages", {"query": query, "limit": limit})


async def fetch_corpus() -> list[dict]:
    """Every page in full, fetched in ONE session (list_pages, then get_page per id)."""
    async with connect() as session:
        pages = _decode("list_pages", await session.call_tool("list_pages", {}))
        out = []
        for meta in pages:
            page = _decode("get_page", await session.call_tool("get_page", {"page_id": meta["id"]}))
            out.append(page)
        return out


def run(coro: Awaitable[T]) -> T:
    """Sync convenience: run one client coroutine to completion."""
    return asyncio.run(coro)  # type: ignore[arg-type]
