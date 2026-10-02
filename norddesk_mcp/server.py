"""norddesk_mcp/server.py — the NordDesk MCP server (stdio), exposing the store functions as tools.

Purpose:      A thin MCP layer over norddesk_mcp.store. Each tool delegates to the plain function
              of the same name, which re-reads the JSON store — so the server itself holds no
              state and can be restarted at any time.
Entry points: mcp (FastMCP instance), run() — tools: search_tickets, get_ticket, create_ticket,
              post_update, get_system_status, get_oncall
Depends on:   mcp.server.fastmcp.FastMCP, norddesk_mcp.store
Used by:      norddesk_mcp.__main__ (`serve`), opscopilot.mcp_tickets.client (once wired)
Invariants:   Tool names and argument names are the contract the client is written against —
              do not rename them without changing the client.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from norddesk_mcp import store

mcp = FastMCP(
    "norddesk",
    log_level="WARNING",  # keep stderr quiet for CLI users
    instructions=(
        "NordDesk — Nordfarm Foods' ticket system (fake, file-backed). "
        "Read tools: search_tickets, get_ticket, get_system_status, get_oncall. "
        "Write tools: create_ticket, post_update."
    ),
)


@mcp.tool()
def search_tickets(
    query: str = "",
    status: str | None = None,
    system: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search tickets by free text (id, summary, description, comments); filter by status/system."""
    return store.search_tickets(query=query, status=status, system=system, limit=limit)


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Get one ticket in full by id, e.g. INC-1042."""
    return store.get_ticket(ticket_id)


@mcp.tool()
def create_ticket(
    summary: str,
    description: str,
    type: str = "incident",  # noqa: A002
    urgency: str = "P3",
    system: str | None = None,
    reporter: str = "opscopilot",
) -> dict:
    """Create a ticket (WRITE).

    type: incident|access_request|change_request|question|vendor|other; urgency: P1..P4.
    """
    return store.create_ticket(
        summary=summary,
        description=description,
        type=type,
        urgency=urgency,
        system=system,
        reporter=reporter,
    )


@mcp.tool()
def post_update(
    ticket_id: str,
    text: str,
    author: str = "opscopilot",
    status: str | None = None,
) -> dict:
    """Add a comment to a ticket (WRITE); optional status: open|in_progress|resolved|closed."""
    return store.post_update(ticket_id=ticket_id, text=text, author=author, status=status)


@mcp.tool()
def get_system_status(system: str | None = None) -> list[dict]:
    """Status of one system (by id or name) or all systems, with open-ticket counts."""
    return store.get_system_status(system)


@mcp.tool()
def get_oncall(shift: str | None = None) -> list[dict]:
    """Who is on call: all teams for one shift ("day" | "night"), or the whole rota."""
    return store.get_oncall(shift)


def run() -> None:
    mcp.run(transport="stdio")
