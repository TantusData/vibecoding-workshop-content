"""opscopilot/mcp_tickets/client.py — NordDesk (ticket system) MCP client.

Purpose:      Talk to the NordDesk MCP server (`norddesk_mcp/`, stdio) so OpsCopilot can look up
              and update tickets. Every function opens a fresh session, calls exactly one tool and
              returns the tool's JSON — nothing is cached anywhere on this side, so an answer is
              only ever as old as the call that produced it ("re-fetch before answering").
              Writes go through the approval gate first.
Entry points: connect() (async context manager), call_tool(name, args); search_tickets(),
              get_ticket(), create_ticket(), post_update(), get_system_status(), get_oncall() —
              async — plus run(coro) for sync callers and TOOLS (name -> function)
Depends on:   mcp (ClientSession, stdio_client), norddesk_mcp (the server it launches),
              opscopilot.mcp_tickets.approval
Used by:      opscopilot.cli (ask's tool step)
Invariants:   No client-side caching. create_ticket/post_update never reach the server without
              require_approval() returning first. NORDDESK_STORE is forwarded to the server
              subprocess so tests and demos can point both sides at the same file.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

from opscopilot.mcp_tickets.approval import require_approval

T = TypeVar("T")


def server_params() -> StdioServerParameters:
    """Our own fake NordDesk (norddesk_mcp/), launched as a subprocess over stdio."""
    env = get_default_environment()
    for key in ("NORDDESK_STORE", "PYTHONPATH"):
        if key in os.environ:
            env[key] = os.environ[key]
    return StdioServerParameters(
        command=sys.executable, args=["-m", "norddesk_mcp", "serve"], env=env
    )


@asynccontextmanager
async def connect() -> AsyncIterator[ClientSession]:
    """Open a stdio session to the NordDesk MCP server and initialise the handshake."""
    async with stdio_client(server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


# tools whose result is a JSON list
LIST_TOOLS = {"search_tickets", "get_system_status", "get_oncall"}


async def call_tool(name: str, args: dict[str, Any]) -> Any:
    """One tool call on a fresh session; the server's JSON, decoded. Gate applies to writes."""
    require_approval(name, args)
    async with connect() as session:
        result = await session.call_tool(name, args)
    if result.isError:
        raise RuntimeError(f"NordDesk tool {name} failed: {result.content}")
    texts = [c.text for c in result.content if getattr(c, "type", "") == "text"]
    decoded = [json.loads(t) for t in texts]
    if name in LIST_TOOLS:
        # FastMCP serialises a list result as one text item per element (none for an empty list)
        return decoded
    return decoded[0] if decoded else None


async def search_tickets(
    query: str = "", status: str | None = None, system: str | None = None, limit: int = 10
) -> list[dict]:
    """Find tickets whose id/summary/description/comments contain `query` (filters optional)."""
    args: dict[str, Any] = {"query": query, "limit": limit}
    if status:
        args["status"] = status
    if system:
        args["system"] = system
    return await call_tool("search_tickets", args)


async def get_ticket(ticket_id: str) -> dict:
    """Fetch one ticket in full (fields, comments, status history)."""
    return await call_tool("get_ticket", {"ticket_id": ticket_id})


async def create_ticket(
    summary: str,
    description: str,
    *,
    type: str = "incident",  # noqa: A002 -- matches the NordDesk field name
    urgency: str = "P3",
    system: str | None = None,
) -> dict:
    """Create a new ticket. WRITE action — goes through the approval gate."""
    args: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "type": type,
        "urgency": urgency,
    }
    if system:
        args["system"] = system
    return await call_tool("create_ticket", args)


async def post_update(ticket_id: str, text: str, status: str | None = None) -> dict:
    """Add a comment (and optionally change status). WRITE action — approval gate."""
    args: dict[str, Any] = {"ticket_id": ticket_id, "text": text}
    if status:
        args["status"] = status
    return await call_tool("post_update", args)


async def get_system_status(system: str | None = None) -> list[dict]:
    """Current status of one system, or all systems, as NordDesk sees them."""
    args = {"system": system} if system else {}
    return await call_tool("get_system_status", args)


async def get_oncall(shift: str | None = None) -> list[dict]:
    """The on-call rota for one shift ("day" | "night") or all of it."""
    return await call_tool("get_oncall", {"shift": shift} if shift else {})


TOOLS: dict[str, Callable[..., Awaitable[Any]]] = {
    "search_tickets": search_tickets,
    "get_ticket": get_ticket,
    "create_ticket": create_ticket,
    "post_update": post_update,
    "get_system_status": get_system_status,
    "get_oncall": get_oncall,
}


def run(coro: Awaitable[T]) -> T:
    """Sync convenience for the CLI: run one client coroutine to completion."""
    return asyncio.run(coro)  # type: ignore[arg-type]
