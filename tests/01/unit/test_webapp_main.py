"""The chat page has no terminal: `detach_terminal()` (run by `python -m opscopilot.webapp`
before the server starts) leaves nothing on standard input to ask a human on, so the approval
gate refuses a write asked from the page instead of prompting on the server's terminal.

Started from a real terminal (a pty here), the page's process would otherwise see one: uvicorn
hands its standard input over to the process that serves the page."""

from __future__ import annotations

import os
import pty
import subprocess
import sys
from pathlib import Path


def test_the_chat_page_starts_without_a_terminal():
    code = (
        "import sys\n"
        "from opscopilot.webapp.__main__ import detach_terminal\n"
        "before = sys.stdin.isatty()\n"
        "detach_terminal()\n"
        "print(before, sys.stdin.isatty())\n"
    )
    master, slave = pty.openpty()
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            stdin=slave,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
            timeout=60,
        )
    finally:
        os.close(master)
        os.close(slave)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["True", "False"]  # a terminal before, none after
