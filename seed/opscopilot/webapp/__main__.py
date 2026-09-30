"""opscopilot/webapp/__main__.py — `python -m opscopilot.webapp`: start the chat page.

Purpose:      Runs the FastAPI app with uvicorn on 0.0.0.0:$PORT (default 8000), reloading when a
              .py file of this project changes, and prints how to OPEN it on our code-server
              machines — through the editor's Ports panel, never a localhost address (localhost in
              the user's browser is their own laptop, not this machine). Uvicorn's own "running
              on" line is silenced for that reason. Works from the project root it lives in, not
              from the terminal's current directory, so a terminal left in a moved or deleted
              directory cannot make it watch (and serve) stale code.
Entry points: main()
Depends on:   uvicorn, opscopilot.webapp.app
Used by:      whoever runs the chat page
Invariants:   Never prints a bare localhost URL. Watches only this project's directory.
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

PROJECT = Path(__file__).resolve().parents[2]

MESSAGE = """
OpsCopilot is running (port {port}). To stop it: Ctrl+C in this terminal.

How to open the page:
  1. Open the PORTS panel (at the bottom of the window, next to TERMINAL).
  2. Next to port {port} click the address — or copy it and open it with
     Ctrl+Shift+P -> "Simple Browser: Show".
Do not type an address with "localhost" — in your browser that is your laptop, not this machine.
"""


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    print(MESSAGE.format(port=port), flush=True)
    os.chdir(PROJECT)
    uvicorn.run(
        "opscopilot.webapp.app:app",
        host="0.0.0.0",  # noqa: S104 - the machine forwards the port; nothing else listens
        port=port,
        reload=True,
        reload_dirs=[str(PROJECT)],
        log_level="warning",
    )


if __name__ == "__main__":
    main()
