"""opscopilot/cli.py — the command-line entry point (`opscopilot ...`).

Purpose:      Typer app. Today: `ask` — a plain call to the model with the `ask.md` prompt, no
              tools, no retrieval, no memory of our systems; and `status` — what this repo can
              actually do right now, probed from the code. The web page calls the same `ask()`.
Entry points: app, ask(question, session_id) -> str, ask_traced() -> (answer, turn_id, events),
              load_prompt(name), ask_cmd, status_cmd
Depends on:   typer, opscopilot.llm.client, opscopilot/llm/prompts/ask.md, opscopilot.status
Used by:      opscopilot.webapp.app; the `opscopilot` console script
Invariants:   ask() sends only the question — nothing about tickets or docs is looked up, so any
              ticket detail in an answer is invented by the model. `session_id` is accepted (the
              web page sends one) and ignored until plan item 3. ask_traced() returns an empty trace
              until the audit log exists (plan item 6) and the trace panel (plan item 8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from opscopilot.llm.client import get_llm_client

PROMPTS_DIR = Path(__file__).parent / "llm" / "prompts"

app = typer.Typer(
    name="opscopilot",
    help="OpsCopilot — Nordfarm Foods internal IT/OT assistant (prototype).",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """OpsCopilot — Nordfarm Foods internal IT/OT assistant (prototype)."""


def load_prompt(name: str) -> str:
    """Read `llm/prompts/<name>.md` (kept as files so prompts are reviewable like code)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def ask(question: str, session_id: str | None = None) -> str:
    """Send the question straight to the model. No tools, no grounding — just the model's memory."""
    return ask_traced(question, session_id)[0]


def ask_traced(
    question: str, session_id: str | None = None
) -> tuple[str, str, list[dict[str, Any]]]:
    """Same contract as the final solution: (answer, turn_id, trace). Trace is empty for now."""
    result = get_llm_client().complete(load_prompt("ask"), [{"role": "user", "content": question}])
    return result.text, "", []


@app.command("ask")
def ask_cmd(question: Annotated[str, typer.Argument(help="What do you want to know?")]) -> None:
    """Ask OpsCopilot a question (plain model call — see HANDOVER_NOTE.md)."""
    typer.echo(ask(question))


@app.command("status")
def status_cmd() -> None:
    """What this repo can actually do right now, probed from the code (no model call)."""
    from opscopilot.status import capabilities, render

    typer.echo(render(capabilities()))


@app.command("impact")
def impact_cmd(ticket_id: Annotated[str, typer.Argument(help="e.g. INC-1042")]) -> None:
    """Estimate downtime / EUR impact for a ticket from the pre-trained model (no LLM).

    Tomasz's shortcut: reads var/norddesk.json through the server's own store module, not
    through the MCP client — good enough for a side project; the app proper goes through MCP."""
    import json

    from norddesk_mcp import store
    from opscopilot.impact import estimate as impact
    from opscopilot.impact.features import incident_from_ticket

    ticket = store.get_ticket(ticket_id)
    if "error" in ticket:
        raise typer.BadParameter(ticket["error"])
    inc = incident_from_ticket(ticket)
    typer.echo(impact.explain(inc))
    typer.echo(json.dumps(impact.estimate(inc).model_dump(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()
