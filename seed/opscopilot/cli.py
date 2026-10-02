"""opscopilot/cli.py — the command-line entry point (`opscopilot ...`) and the `ask()` pipeline.

Purpose:      Typer app: `ask`, `status`. `ask()` is a three-step pipeline: one structured
              "which tool?" call (ToolPlan, `llm/prompts/route.md`) → at most one NordDesk tool
              call through the MCP client → a second model call that answers from the tool result
              (`answer_tickets.md`). A question that needs no tool gets a short `chat.md` reply.
              The NordDesk client itself is unfinished (plan item 2): until it is, a question
              that needs a ticket gets a plain "not connected yet". The web page calls the same
              `ask_traced()`.
Entry points: app, ask(), ask_traced(), route_system(), plan_step(), run_tool(),
              tool_result_block(), load_prompt(), ask_cmd, status_cmd
Depends on:   typer, opscopilot.llm.client, opscopilot.mcp_tickets.client (+ approval),
              opscopilot.schema.ToolPlan, opscopilot/llm/prompts/{route,answer_tickets,chat}.md
Used by:      opscopilot.webapp.app; the `opscopilot` console script
Invariants:   Ticket data is fetched fresh on every ask() — nothing is remembered between calls.
              Writes reach NordDesk only through the approval gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from opscopilot import loop
from opscopilot.llm.client import get_llm_client
from opscopilot.mcp_tickets import client as tickets
from opscopilot.mcp_tickets.approval import ApprovalDenied
from opscopilot.schema import ToolPlan

PROMPTS_DIR = Path(__file__).parent / "llm" / "prompts"
# NordDesk's system ids with their English and Polish names: users ask in Polish ("MES linii
# pakowania"), the `system` filter only matches the exact id
SYSTEM_IDS = (
    "palletiser-l3 (Line 3 palletiser KX-90 / paletyzator linii 3), "
    "mes-packing (Packing-line MES / MES linii pakowania), "
    "label-printer-l2 (Line 2 label printer / drukarka etykiet linii 2), "
    "vpn (Remote access VPN / VPN, zdalny dostęp), "
    "wifi-coldstore (Wi-Fi in the cold store / Wi-Fi w chłodni), "
    "erp (ERP Dynamics / system ERP), "
    "scada-l1 (Line 1 SCADA / SCADA linii 1)"
)

app = typer.Typer(
    name="opscopilot",
    help="OpsCopilot — Nordfarm Foods internal IT/OT assistant (prototype).",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """OpsCopilot — Nordfarm Foods internal IT/OT assistant (prototype)."""


# nothing to run yet: wiki search arrives with plan item 7, the impact model as a tool with item 8
NOT_A_LOOKUP = ("final", "search_docs", "impact_estimate")
NOT_CONNECTED = (
    "NordDesk is not connected yet (the ticket client is unfinished), so I cannot look this up."
)


def load_prompt(name: str) -> str:
    """Read `llm/prompts/<name>.md` (kept as files so prompts are reviewable like code)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def route_system(prior: list[dict[str, str]] | None = None) -> str:
    """route.md with the system list and the tool-call budget filled in."""
    return (
        load_prompt("route")
        .replace("{systems}", SYSTEM_IDS)
        .replace("{max_calls}", str(loop.max_tool_calls()))
        .replace("{history_option}", "")
    )


def plan_step(
    question: str,
    prior: list[dict[str, str]] | None = None,
    results: list[Any] | None = None,
) -> ToolPlan:
    """Ask the model which tool (if any) this question needs — one structured call."""
    result = get_llm_client().complete(
        route_system(prior), [*(prior or []), {"role": "user", "content": question}], ToolPlan
    )
    assert isinstance(result.parsed, ToolPlan)
    return result.parsed


def run_tool(plan: ToolPlan) -> Any:
    """One fresh MCP call. Writes pass the approval gate inside the client."""
    return tickets.run(tickets.TOOLS[plan.tool](**plan.args()))


def tool_result_block(plan: ToolPlan, tool_result: Any) -> str:
    """The fresh tool result, tagged with the tool and its arguments."""
    return (
        f'<tool_result tool="{plan.tool}" args={json.dumps(plan.args())}>\n'
        f"{json.dumps(tool_result, indent=2, ensure_ascii=False)}\n</tool_result>"
    )


def ask(question: str, session_id: str | None = None) -> str:
    """Plan → (one tool) → answer. `session_id` is accepted (web page), unused until plan item 3."""
    return ask_traced(question, session_id)[0]


def ask_traced(
    question: str, session_id: str | None = None
) -> tuple[str, str, list[dict[str, Any]]]:
    """Same contract as the final solution: (answer, turn_id, trace). Trace is empty for now."""
    return _ask(question, []), "", []


def _ask(question: str, prior: list[dict[str, str]]) -> str:
    client = get_llm_client()
    plan = plan_step(question, prior)
    if plan.tool in NOT_A_LOOKUP:
        # nothing to look up: a short reply from chat.md
        return client.complete(load_prompt("chat"), [{"role": "user", "content": question}]).text
    try:
        tool_result = run_tool(plan)
    except ApprovalDenied:
        return f"Not done — the {plan.tool} change was not approved, so NordDesk is unchanged."
    except NotImplementedError:
        return NOT_CONNECTED
    # the question, then what NordDesk returned
    messages = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": tool_result_block(plan, tool_result)},
    ]
    return client.complete(load_prompt("answer_tickets"), messages).text


@app.command("ask")
def ask_cmd(
    question: Annotated[str, typer.Argument(help="What do you want to know?")],
    session: Annotated[
        str | None, typer.Option(help="Conversation id — accepted, no memory until plan item 3")
    ] = None,
) -> None:
    """Ask OpsCopilot a question (uses NordDesk when the question is about tickets)."""
    typer.echo(ask(question, session_id=session))


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
