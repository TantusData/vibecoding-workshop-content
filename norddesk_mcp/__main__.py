"""norddesk_mcp/__main__.py — `python -m norddesk_mcp {init|serve}`.

Purpose:      `init` copies the committed seed into the runtime store (var/norddesk.json);
              `serve` runs the MCP server on stdio (the app's client launches it itself; the
              store is also created on first use, so `init --force` is only needed to reset it).
Entry points: main()
Depends on:   norddesk_mcp.store, norddesk_mcp.server
Used by:      Makefile, opscopilot.mcp_tickets.client (SERVER_PARAMS launches `serve`)
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "serve"
    if cmd == "init":
        from norddesk_mcp.store import init_store, load

        path = init_store(force="--force" in argv)
        print(f"norddesk: store at {path} ({len(load()['tickets'])} tickets)", file=sys.stderr)
        return 0
    if cmd == "serve":
        from norddesk_mcp.server import run

        run()
        return 0
    print("usage: python -m norddesk_mcp [init [--force] | serve]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
