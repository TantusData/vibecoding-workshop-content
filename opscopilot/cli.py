"""opscopilot/cli.py — the command-line entry point (`opscopilot ...`) and the `ask()` pipeline.

Purpose:      Typer app: `ask` (+ `history` sub-commands), `report`, `impact`, `status`. `ask()`:
              a structured "which tool?" call (ToolPlan) → one NordDesk tool + an answer (plan item 2), or —
              for everything else — retrieval over the Nordwiki corpus + a grounded, cited answer
              (plan item 7). There is no ungrounded path any more. The web page calls the same `ask()`.
              `report` runs opscopilot.report (gather → draft) for Marek's shift handover.
              `impact_estimate` (plan item 8) is a router option composed here: get_ticket → Incident
              features → the pre-trained regressor's downtime/€/drivers, answered like a tool.
              Since plan item 6 every ask() is guarded: scope check first (refuse off-topic / policy
              circumvention), tool results redacted before they reach a prompt, retrieved docs
              sanitised of instruction-like text, writes blocked when the request carries
              injection markers, answers scanned on the way out, and every step audited.
              ext-history: with a session id the prior turns (window from opscopilot.history)
              are sent to the router and the answer call and the exchange is recorded.
              ext-trace: ask_traced() runs the turn inside audit.turn() and returns the turn's
              own events (the side panel / --trace); every model call also writes a usage row.
Entry points: app (typer.Typer), ask(question, session_id) -> str, ask_traced() -> (answer,
              turn_id, events), format_trace(), route_system(), plan_tool(),
              run_tool(), answer_from_docs(), impact_estimate(ticket_id), tool_user_message(),
              docs_user_message(), current_session(), ask_cmd, history_* , usage_cmd,
              report_cmd, impact_cmd, status_cmd, load_prompt()
Depends on:   typer, opscopilot.llm.client, opscopilot.mcp_tickets.client (+ approval),
              opscopilot.rag.retrieve, opscopilot.report, opscopilot.govern.{scope,redact,
              injection,audit}, opscopilot.impact.{estimate,features}, opscopilot.{history,store},
              opscopilot.schema.{ToolPlan,GroundedAnswer,Answer},
              opscopilot/llm/prompts/{route,answer_tickets,answer}.md
Used by:      opscopilot.webapp.app; the `opscopilot` console script (pyproject)
Invariants:   Writes reach NordDesk only through the
              approval gate. Doc questions are answered only from retrieved <doc> chunks, with
              chunk ids as citations; anything not in the docs gets the exact string
              NOT_FOUND. Retrieved text is passed as data inside <doc> tags. Earlier tool
              results are replayed from history by default (OPSCOPILOT_HISTORY_TOOL_RESULTS) —
              deliberately, see docs/EXTENSIONS_PLAN.md §1. Out-of-scope
              requests get the exact string scope.REFUSAL before any tool or answer call. No
              tool result or document reaches a prompt un-redacted / un-sanitised.
"""

from __future__ import annotations

import contextvars
import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer

from opscopilot import history, loop, store
from opscopilot.govern import audit, injection
from opscopilot.govern.redact import redact_obj
from opscopilot.govern.scope import REFUSAL, classify
from opscopilot.llm.client import get_llm_client
from opscopilot.loop import LoopOutcome, ToolBlocked, ToolDenied, ToolResult
from opscopilot.mcp_tickets import client as tickets
from opscopilot.mcp_tickets.approval import ApprovalDenied
from opscopilot.rag.retrieve import Chunk, retrieve
from opscopilot.schema import Answer, GroundedAnswer, ToolPlan

NOT_FOUND = "Not found in the current knowledge base."

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
_SESSION: contextvars.ContextVar[str] = contextvars.ContextVar("opscopilot_session", default="")


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


def load_prompt(name: str) -> str:
    """Read `llm/prompts/<name>.md` (kept as files so prompts are reviewable like code)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def route_system(prior: list[dict[str, str]] | None = None) -> str:
    """route.md with the system list filled and the from_history option only when there IS
    a conversation (naive or guarded per OPSCOPILOT_HISTORY_REFETCH)."""
    return (
        load_prompt("route")
        .replace("{systems}", SYSTEM_IDS)
        .replace("{max_calls}", str(loop.max_tool_calls()))
        .replace("{history_option}", history.router_history_option() if prior else "")
    )


def plan_step(
    question: str,
    prior: list[dict[str, str]] | None = None,
    results: list[ToolResult] | None = None,
) -> ToolPlan:
    """One planning step: given the question, the conversation and what this turn has gathered
    so far, which tool next — or `final`."""
    client = get_llm_client()
    system = route_system(prior)
    user = loop.plan_user_message(question, results or [])
    result = client.complete(system, [*(prior or []), {"role": "user", "content": user}], ToolPlan)
    assert isinstance(result.parsed, ToolPlan)
    _audit_model("route", result, tool=result.parsed.tool, step_n=len(results or []) + 1)
    return result.parsed


def plan_tool(question: str, prior: list[dict[str, str]] | None = None) -> ToolPlan:
    """The first planning step (kept for callers/tests of the pre-loop API)."""
    return plan_step(question, prior, [])


def _audit_model(step: str, result: Any, **fields: Any) -> None:
    audit.log_event(
        "model_call",
        step=step,
        provider=result.provider,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        **fields,
    )


def search_docs(query: str) -> list[Chunk]:
    """Retrieval as a tool: the top chunks for `query`, sanitised of instruction-like text."""
    chunks, hits = injection.sanitize_docs(retrieve(query))
    for h in hits:
        audit.log_event("injection", where=h.where, marker=h.kind, excerpt=h.excerpt)
    audit.log_event(
        "tool_call", tool="search_docs", args={"query": query}, result=[c.id for c in chunks]
    )
    return chunks


def run_tool(plan: ToolPlan) -> Any:
    """Execute one planned step: MCP call (redacted, writes gated), impact, or retrieval."""
    if plan.tool == "search_docs":
        return search_docs(plan.query or "")
    if plan.tool == "impact_estimate":  # the impact model becomes a tool in plan item 8
        raw = {"error": "impact_estimate is not available yet"}
    else:
        raw = tickets.run(tickets.TOOLS[plan.tool](**plan.args()))
    result, findings = redact_obj(raw)
    audit.log_event("tool_call", tool=plan.tool, args=plan.args(), result=result)
    if findings:
        audit.log_event(
            "redaction",
            where=f"tool_result:{plan.tool}",
            findings=[f.model_dump() for f in findings],
        )
    return result


def docs_user_message(question: str, chunks: list[Chunk]) -> str:
    """The grounded answer's user turn: the question plus each chunk as a <doc id=...> block."""
    docs = "\n".join(f'<doc id="{c.id}" page="{c.page_id}">\n{c.text}\n</doc>' for c in chunks)
    return f"{question}\n\n{docs}"


def gathered_user_message(question: str, results: list[ToolResult]) -> str:
    """The answer step's user turn: the question, every <tool_result> and every <doc> gathered."""
    blocks = []
    for r in results:
        if r.tool == "search_docs":
            blocks.append(
                "\n".join(
                    f'<doc id="{c.id}" page="{c.page_id}">\n{c.text}\n</doc>' for c in r.result
                )
            )
        else:
            blocks.append(
                f'<tool_result tool="{r.tool}" args={json.dumps(r.args, ensure_ascii=False)}>\n'
                f"{json.dumps(r.result, indent=2, ensure_ascii=False)}\n</tool_result>"
            )
    return f"{question}\n\n" + "\n".join(blocks)


def answer_grounded(
    question: str, prior: list[dict[str, str]], results: list[ToolResult]
) -> Answer:
    """Docs contract: at least one search_docs result is present, so the model must answer only
    from the <doc>/<tool_result> blocks and cite chunk ids, or say NOT_FOUND."""
    chunks = [c for r in results if r.tool == "search_docs" for c in r.result]
    result = get_llm_client().complete(
        load_prompt("answer"),
        [*prior, {"role": "user", "content": gathered_user_message(question, results)}],
        GroundedAnswer,
    )
    assert isinstance(result.parsed, GroundedAnswer)
    _audit_model("answer_docs", result)
    known = {c.id for c in chunks}
    citations = [c for c in result.parsed.citations if c in known]
    not_found = result.parsed.text.strip() == NOT_FOUND
    text, out_hits = injection.scan_output(result.parsed.text)
    for h in out_hits:
        audit.log_event("injection", where="answer", marker=h.kind, excerpt=h.excerpt)
    return Answer(
        text=NOT_FOUND if not_found else text,
        citations=[] if not_found else citations,
        grounded=not not_found and bool(citations),
        retrieved_chunk_ids=[c.id for c in chunks],
    )


def answer_from_docs(question: str, prior: list[dict[str, str]] | None = None) -> Answer:
    """plan item 7's path kept as a convenience: one retrieval, then the grounded answer."""
    return answer_grounded(
        question,
        prior or [],
        [ToolResult("search_docs", {"query": question}, search_docs(question))],
    )


def _answer_text(prompt: str, step: str, prior: list[dict[str, str]], user: str) -> str:
    """A free-text answer call with the output scanner applied."""
    result = get_llm_client().complete(
        load_prompt(prompt), [*prior, {"role": "user", "content": user}]
    )
    _audit_model(step, result)
    text, hits = injection.scan_output(result.text)
    for h in hits:
        audit.log_event("injection", where="answer", marker=h.kind, excerpt=h.excerpt)
    return text


def ask(question: str, session_id: str | None = None) -> str:
    """Route → NordDesk tool + answer, or → wiki retrieval + grounded answer.

    With a session_id (ext-history) the prior turns of that session are sent to the router and
    the answer call, and this exchange is recorded afterwards. Without one, stateless as before.
    """
    return ask_traced(question, session_id)[0]


def ask_traced(
    question: str, session_id: str | None = None
) -> tuple[str, str, list[dict[str, Any]]]:
    """ext-trace: like ask(), but also returns (turn_id, the turn's audit events in order)."""
    token = _SESSION.set(session_id or "")
    try:
        prior = history.window(session_id) if session_id else []
        answer, tool_calls = _ask(question, prior, session_id)
        if session_id:
            history.record_turn(session_id, question, answer, tool_calls)
        return answer, "", []
    finally:
        _SESSION.reset(token)


def _ask(
    question: str, prior: list[dict[str, str]], session_id: str | None = None
) -> tuple[str, list[tuple[str, dict, Any]]]:
    decision = classify(question, prior)
    audit.log_event(
        "scope", allowed=decision.allowed, reason=decision.reason, method=decision.method
    )
    if not decision.allowed:
        audit.log_event(
            "refusal", question=question, reason=decision.reason, method=decision.method
        )
        return REFUSAL, []
    # --- the loop: plan a step, execute it, repeat (ext-loop) ---------------------------------
    allowed = injection.allowed_tools(question)

    def execute(step: ToolPlan) -> Any:
        if step.tool not in allowed:
            audit.log_event(
                "refusal",
                question=question,
                reason="write-with-injection-markers",
                method="rule-deny",
            )
            raise ToolBlocked(step.tool)
        try:
            return run_tool(step)
        except ApprovalDenied as err:
            raise ToolDenied(step.tool) from err

    outcome: LoopOutcome = loop.run_loop(
        lambda results: plan_step(question, prior, results), execute
    )
    audit.log_event(
        "loop",
        stop=outcome.stop,
        tool_calls=len(outcome.results),
        planner_calls=outcome.planner_calls,
    )
    if outcome.stop == "blocked":
        return REFUSAL, []
    if outcome.stop == "denied":
        return (
            f"Not done — the {outcome.denied_tool} change was not approved, "
            "so NordDesk is unchanged.",
            [(r.tool, r.args, r.result) for r in outcome.results if r.tool != "search_docs"],
        )
    results = outcome.results

    # the fix that works for stale memory: a state question answered with no lookup re-runs
    # the last lookup instead (the prompt rule alone did not hold; see docs/LOGIC_LOG.md)
    if not results and history.refetch() and history.is_state_question(question):
        last = history.last_tool_call(session_id) if session_id else None
        if last and last[0] in tickets.TOOLS:
            audit.log_event("refetch", question=question, tool=last[0], args=last[1])
            step = ToolPlan(tool=last[0], reason="refetch override", **last[1])  # type: ignore[arg-type]
            results = [ToolResult(step.tool, step.args(), run_tool(step))]

    # --- the answer contract is decided here, not by the model ---------------------------------
    recorded = [(r.tool, r.args, r.result) for r in results if r.tool != "search_docs"]
    if any(r.tool == "search_docs" for r in results):
        answer = answer_grounded(question, prior, results)
        audit.log_event("answer", mode="docs", grounded=answer.grounded, citations=answer.citations)
        return answer.render(), recorded
    if results:
        text = _answer_text(
            "answer_tickets", "answer_tickets", prior, gathered_user_message(question, results)
        )
        audit.log_event("answer", mode="tools", grounded=True, tools=[r.tool for r in results])
        return text, recorded
    if prior:
        # no lookup at all, but there is a conversation: the naive memory path (may go stale)
        text = _answer_text("answer_history", "answer_history", prior, question)
        audit.log_event("answer", mode="memory", grounded=False)
        return text, []
    text = _answer_text("chat", "answer_chat", prior, question)
    audit.log_event("answer", mode="chat", grounded=False)
    return text, []


def tool_user_message(question: str, plan: ToolPlan, tool_result: Any) -> str:
    """Step 3's user turn: the question plus the fresh tool result inside <tool_result> tags."""
    return (
        f'{question}\n\n<tool_result tool="{plan.tool}" args={json.dumps(plan.args())}>\n'
        f"{json.dumps(tool_result, indent=2, ensure_ascii=False)}\n</tool_result>"
    )


@app.command("ask")
def ask_cmd(
    question: Annotated[str, typer.Argument(help="What do you want to know?")],
    session: Annotated[str | None, typer.Option(help="Conversation id (default: current)")] = None,
    new: Annotated[bool, typer.Option("--new", help="Start a new conversation first")] = False,
    no_history: Annotated[bool, typer.Option("--no-history", help="Stateless, as before")] = False,
) -> None:
    """Ask OpsCopilot a question (NordDesk for tickets, Nordwiki for everything else)."""
    sid = None if no_history else current_session(session, new=new)
    typer.echo(ask(question, session_id=sid))


history_app = typer.Typer(help="Conversation history (ext-history).", no_args_is_help=True)
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
def history_purge(
    older_than: Annotated[int, typer.Option(help="days")] = 30,
) -> None:
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
