"""opscopilot/webapp/app.py — the bare chat page's backend (FastAPI, one route).

Purpose:      Serves `static/index.html` (+ static/: app.css, theme.css, branding.json) and
              exposes POST /ask, which calls the very same
              `opscopilot.cli.ask()` the CLI uses. No sessions, no history, no auth — it exists so
              non-CLI people can try the prototype. Run with `python -m opscopilot.webapp`.
              The page sends a per-tab session id so follow-up questions see the conversation,
              and gets back the turn's audit trail to draw the side panel.
Entry points: app (FastAPI), POST /ask {question, session_id} -> {answer, turn_id, trace},
              GET / -> index.html, GET /static/* -> the page's files
Depends on:   fastapi, opscopilot.cli.ask_traced
Used by:      opscopilot.webapp.__main__ (`python -m opscopilot.webapp`)
Invariants:   Never duplicates ask() logic — if the CLI changes, the page changes with it.
              Every URL the page uses is RELATIVE ("ask", "static/app.css"): on our code-server
              machines the app is served under /proxy/8000/, and a leading "/" would escape that
              prefix.
              The look lives in theme.css + branding.json only (the owner's files).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from opscopilot import __version__
from opscopilot.cli import ask_traced

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="OpsCopilot", version=__version__)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None  # ext-history: the page keeps one per tab


class AskResponse(BaseModel):
    answer: str
    turn_id: str = ""
    trace: list[dict[str, Any]] = []  # ext-trace: this turn's audit events, in order, redacted


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/ask", response_model=AskResponse)
def ask_route(body: AskRequest) -> AskResponse:
    answer, turn_id, events = ask_traced(body.question, session_id=body.session_id)
    return AskResponse(answer=answer, turn_id=turn_id, trace=events)
