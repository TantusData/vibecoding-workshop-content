"""opscopilot/cli.py — the command-line entry point (`opscopilot ...`) and the `ask()` pipeline.

Purpose:      Typer app: `ask` (+ `history` sub-commands), `status`. `ask()` = one structured
              "which tool?" call (ToolPlan) → at most one NordDesk tool call → an answer from the
              result; no tool → a chat reply. Since plan item 3 a session's prior turns (the window
              from opscopilot.history) are sent to the planner and the answer call, the exchange
              is recorded, and a turn that looks nothing up but has a conversation is answered
              from memory (`answer_history.md`) — the naive path that can go stale.
Entry points: app, ask(question, session_id), ask_traced(), route_system(), plan_step(),
              run_tool(), tool_user_message(), current_session(), load_prompt(), ask_cmd,
              history_new/show/purge, status_cmd
Depends on:   typer, opscopilot.llm.client, opscopilot.mcp_tickets.client (+ approval),
              opscopilot.{history,store,loop}, opscopilot.schema.ToolPlan,
              opscopilot/llm/prompts/{route,answer_tickets,answer_history,chat}.md
Used by:      opscopilot.webapp.app; the `opscopilot` console script
Invariants:   Writes reach NordDesk only through the approval gate. Earlier tool results are
              replayed from history by default (OPSCOPILOT_HISTORY_TOOL_RESULTS); with
              OPSCOPILOT_HISTORY_REFETCH=1 a state question is never answered from memory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer

from opscopilot import history, loop, store
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
SESSION_FILE = Path(__file__).resolve().parent.parent / "var" / "current_session"


def current_session(explicit: str | None = None, new: bool = False) -> str:
    """--session > OPSCOPILOT_SESSION > var/current_session (created on first use / --new)."""
    if explicit:
        return explicit
    if os.environ.get("OPSCOPILOT_SESSION"):
        return os.environ["OPSCOPILOT_SESSION"]
    if new or not SESSION_FILE.exists():
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(store.new_session_id(), encoding="utf-8")
    return SESSION_FILE.read_text(encoding="utf-8").strip()


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


def load_prompt(name: str) -> str:
    """Read `llm/prompts/<name>.md` (kept as files so prompts are reviewable like code)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def route_system(prior: list[dict[str, str]] | None = None) -> str:
    """route.md with the system list, the budget, and the memory guidance when there IS a
    conversation (naive or guarded per OPSCOPILOT_HISTORY_REFETCH)."""
    return (
        load_prompt("route")
        .replace("{systems}", SYSTEM_IDS)
        .replace("{max_calls}", str(loop.max_tool_calls()))
        .replace("{history_option}", history.router_history_option() if prior else "")
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


def tool_user_message(question: str, plan: ToolPlan, tool_result: Any) -> str:
    """The answer step's user turn: the question plus the fresh tool result in <tool_result>."""
    return (
        f'{question}\n\n<tool_result tool="{plan.tool}" args={json.dumps(plan.args())}>\n'
        f"{json.dumps(tool_result, indent=2, ensure_ascii=False)}\n</tool_result>"
    )


def ask(question: str, session_id: str | None = None) -> str:
    """Plan → (one tool) → answer, with the session's conversation when a session_id is given."""
    return ask_traced(question, session_id)[0]


def ask_traced(
    question: str, session_id: str | None = None
) -> tuple[str, str, list[dict[str, Any]]]:
    """Same contract as the final solution: (answer, turn_id, trace). Trace is empty for now."""
    prior = history.window(session_id) if session_id else []
    answer, tool_calls = _ask(question, prior, session_id)
    if session_id:
        history.record_turn(session_id, question, answer, tool_calls)
    return answer, "", []


def _ask(
    question: str, prior: list[dict[str, str]], session_id: str | None = None
) -> tuple[str, list[tuple[str, dict, Any]]]:
    client = get_llm_client()
    plan = plan_step(question, prior)
    no_lookup = plan.tool in NOT_A_LOOKUP
    if no_lookup and history.refetch() and history.is_state_question(question):
        # the fix that works for stale memory: a state question is never answered from memory —
        # re-run the last lookup instead (a prompt rule alone does not hold)
        last = history.last_tool_call(session_id) if session_id else None
        if last and last[0] in tickets.TOOLS:
            plan = ToolPlan(tool=last[0], reason="refetch override", **last[1])  # type: ignore[arg-type]
    if plan.tool in NOT_A_LOOKUP:
        if prior:  # no lookup, but a conversation: the naive memory path (may go stale)
            user = [*prior, {"role": "user", "content": question}]
            return client.complete(load_prompt("answer_history"), user).text, []
        chat = client.complete(load_prompt("chat"), [{"role": "user", "content": question}])
        return chat.text, []
    try:
        tool_result = run_tool(plan)
    except ApprovalDenied:
        return f"Not done — the {plan.tool} change was not approved, so NordDesk is unchanged.", []
    user = tool_user_message(question, plan, tool_result)
    turns = [*prior, {"role": "user", "content": user}]
    text = client.complete(load_prompt("answer_tickets"), turns).text
    return text, [(plan.tool, plan.args(), tool_result)]


@app.command("ask")
def ask_cmd(
    question: Annotated[str, typer.Argument(help="What do you want to know?")],
    session: Annotated[str | None, typer.Option(help="Conversation id (default: current)")] = None,
    new: Annotated[bool, typer.Option("--new", help="Start a new conversation first")] = False,
    no_history: Annotated[bool, typer.Option("--no-history", help="Stateless")] = False,
) -> None:
    """Ask OpsCopilot a question (uses NordDesk when the question is about tickets)."""
    sid = None if no_history else current_session(session, new=new)
    typer.echo(ask(question, session_id=sid))


history_app = typer.Typer(help="Conversation history.", no_args_is_help=True)
app.add_typer(history_app, name="history")


@history_app.command("new")
def history_new() -> None:
    """Start a new conversation (the next `ask` gets a fresh session id)."""
    typer.echo(current_session(new=True))


@history_app.command("show")
def history_show(
    session: Annotated[str | None, typer.Option(help="Conversation id (default: current)")] = None,
) -> None:
    """Print the stored turns of a conversation (redacted, as stored)."""
    sid = current_session(session)
    typer.echo(f"session {sid}")
    for m in store.messages(sid):
        typer.echo(f"[{m['ts']}] {m['role']:11s} {m['content'][:160]}")


@history_app.command("purge")
def history_purge(older_than: Annotated[int, typer.Option(help="days")] = 30) -> None:
    """Delete conversation and usage rows older than N days."""
    typer.echo(f"removed {store.purge(older_than)} rows")


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
