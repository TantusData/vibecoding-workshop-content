"""opscopilot/loop.py — the bounded tool loop: plan a step, execute it, repeat, stop on `final`.

Purpose:      Replaces the one-shot router (ext-loop). Pure control flow with two injected
              callables — `plan(results) -> ToolPlan` (a model call in production, a script in
              tests) and `execute(plan) -> result` (MCP / retrieval in production) — so the loop's
              own rules can be unit-tested without a model or a server. Rules: stop when the
              planner says `final`; never run the same (tool, args) twice (stop instead); never
              exceed `max_calls` tool calls; a blocked or denied tool ends the loop with that
              reason. Everything else — guardrails, redaction, audit — lives in the callables.
Entry points: run_loop(plan, execute, max_calls) -> LoopOutcome, ToolResult, LoopOutcome,
              ToolBlocked, max_tool_calls(), plan_user_message(question, results)
Depends on:   opscopilot.schema.ToolPlan; json/os (stdlib)
Used by:      opscopilot.cli (_ask)
Invariants:   len(outcome.results) <= max_calls. The planner is called at most max_calls + 1
              times. A repeated (tool, args) is never executed. `stop` is always one of
              final | max | repeat | blocked | denied.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from opscopilot.schema import ToolPlan

StopReason = Literal["final", "max", "repeat", "blocked", "denied"]


class ToolBlocked(PermissionError):
    """A guardrail refused this tool call (e.g. a write while the request carries injection
    markers). The loop ends and the caller returns the fixed refusal."""


class ToolDenied(PermissionError):
    """The human did not approve a write. The loop ends; the caller reports it."""


@dataclass
class ToolResult:
    tool: str
    args: dict[str, Any]
    result: Any  # redacted JSON for MCP tools; list[Chunk] for search_docs


@dataclass
class LoopOutcome:
    results: list[ToolResult] = field(default_factory=list)
    stop: StopReason = "final"
    planner_calls: int = 0
    denied_tool: str | None = None


def max_tool_calls() -> int:
    return int(os.environ.get("OPSCOPILOT_MAX_TOOL_CALLS", "5"))


def run_loop(
    plan: Callable[[list[ToolResult]], ToolPlan],
    execute: Callable[[ToolPlan], Any],
    max_calls: int | None = None,
) -> LoopOutcome:
    """Plan → execute → plan … until `final`, the cap, a repeat, a block or a denial."""
    cap = max_tool_calls() if max_calls is None else max_calls
    out = LoopOutcome()
    seen: set[str] = set()
    while True:
        if len(out.results) >= cap:
            out.stop = "max"
            return out
        step = plan(out.results)
        out.planner_calls += 1
        if step.tool == "final":
            out.stop = "final"
            return out
        key = json.dumps([step.tool, step.args()], sort_keys=True)
        if key in seen:
            out.stop = "repeat"
            return out
        seen.add(key)
        try:
            result = execute(step)
        except ToolBlocked:
            out.stop = "blocked"
            out.denied_tool = step.tool
            return out
        except ToolDenied:
            out.stop = "denied"
            out.denied_tool = step.tool
            return out
        out.results.append(ToolResult(tool=step.tool, args=step.args(), result=result))


def _brief_result(r: ToolResult, limit: int = 1500) -> str:
    if r.tool == "search_docs":
        lines = [f"- {c.id}: {c.text[:120].replace(chr(10), ' ')}…" for c in r.result]
        return "\n".join(lines) if lines else "(no chunks)"
    text = json.dumps(r.result, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + " …(truncated)"


def plan_user_message(question: str, results: list[ToolResult]) -> str:
    """The planner's user turn: the question plus what this turn has gathered so far."""
    if not results:
        return question
    blocks = [
        f'<tool_result tool="{r.tool}" args={json.dumps(r.args, ensure_ascii=False)}>\n'
        f"{_brief_result(r)}\n</tool_result>"
        for r in results
    ]
    return f"{question}\n\nGathered so far in this turn:\n" + "\n".join(blocks)
