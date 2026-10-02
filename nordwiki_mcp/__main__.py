"""nordwiki_mcp/__main__.py — `python -m nordwiki_mcp {init|serve}`.

Purpose:      `init` only checks the corpus folder exists and reports the page count (the wiki is
              read straight from data/wiki, there is no runtime copy); `serve` runs the MCP server
              on stdio (the app's client launches `serve` itself).
Entry points: main()
Depends on:   nordwiki_mcp.corpus, nordwiki_mcp.server
Used by:      Makefile, opscopilot.mcp_wiki.client (SERVER_PARAMS launches `serve`)
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "serve"
    if cmd == "init":
        from nordwiki_mcp.corpus import list_pages, wiki_root

        print(f"nordwiki: corpus at {wiki_root()} ({len(list_pages())} pages)", file=sys.stderr)
        return 0
    if cmd == "serve":
        from nordwiki_mcp.server import run

        run()
        return 0
    print("usage: python -m nordwiki_mcp [init | serve]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
