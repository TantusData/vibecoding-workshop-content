"""Fixed-input tests for opscopilot.loop — the controller's rules with scripted callables.
No model, no MCP: `plan` returns a queued ToolPlan, `execute` returns canned results."""

from __future__ import annotations

from opscopilot import loop
from opscopilot.schema import ToolPlan

GET = ToolPlan(tool="get_ticket", reason="r", ticket_id="INC-1042")
DOCS = ToolPlan(tool="search_docs", reason="r", query="lockout")
FINAL = ToolPlan(tool="final", reason="enough")


def scripted(*plans):
    queue = list(plans)

    def plan(results):
        return queue.pop(0)

    return plan


def executor(results_by_tool, raise_on=None):
    def execute(step):
        if raise_on and step.tool == raise_on[0]:
            raise raise_on[1]
        return results_by_tool[step.tool]

    return execute


def test_stops_on_final_and_collects_results_in_order():
    out = loop.run_loop(
        scripted(GET, DOCS, FINAL),
        executor({"get_ticket": {"id": "INC-1042"}, "search_docs": ["c1"]}),
    )
    assert out.stop == "final"
    assert [(r.tool, r.args) for r in out.results] == [
        ("get_ticket", {"ticket_id": "INC-1042"}),
        ("search_docs", {"query": "lockout"}),
    ]
    assert out.results[0].result == {"id": "INC-1042"}
    assert out.planner_calls == 3


def test_final_first_means_no_tool_calls():
    out = loop.run_loop(scripted(FINAL), executor({}))
    assert out.stop == "final" and out.results == [] and out.planner_calls == 1


def test_never_exceeds_max_calls_and_does_not_ask_the_planner_again(monkeypatch):
    calls = []

    def plan(results):
        calls.append(len(results))
        return ToolPlan(tool="search_tickets", reason="r", query=f"q{len(results)}")

    out = loop.run_loop(plan, executor({"search_tickets": []}), max_calls=3)
    assert out.stop == "max" and len(out.results) == 3
    assert calls == [0, 1, 2]  # not called a 4th time
    monkeypatch.setenv("OPSCOPILOT_MAX_TOOL_CALLS", "2")
    assert loop.max_tool_calls() == 2
    assert len(loop.run_loop(plan, executor({"search_tickets": []})).results) == 2


def test_a_repeated_identical_call_stops_the_loop_without_executing_it():
    executed = []

    def execute(step):
        executed.append(step.tool)
        return {}

    out = loop.run_loop(scripted(GET, GET, FINAL), execute)
    assert out.stop == "repeat" and executed == ["get_ticket"] and len(out.results) == 1


def test_same_tool_with_different_args_is_not_a_repeat():
    a = ToolPlan(tool="get_ticket", reason="r", ticket_id="INC-1042")
    b = ToolPlan(tool="get_ticket", reason="r", ticket_id="INC-1043")
    out = loop.run_loop(scripted(a, b, FINAL), executor({"get_ticket": {}}))
    assert out.stop == "final" and len(out.results) == 2


def test_blocked_and_denied_tools_end_the_loop_with_the_reason():
    write = ToolPlan(tool="post_update", reason="r", ticket_id="INC-1043", text="x")
    out = loop.run_loop(
        scripted(GET, write, FINAL),
        executor({"get_ticket": {}}, ("post_update", loop.ToolBlocked())),
    )
    assert out.stop == "blocked" and out.denied_tool == "post_update" and len(out.results) == 1
    out = loop.run_loop(scripted(write), executor({}, ("post_update", loop.ToolDenied())))
    assert out.stop == "denied" and out.results == []


def test_plan_user_message_shows_gathered_results_briefly():
    from opscopilot.rag.retrieve import Chunk

    assert loop.plan_user_message("q", []) == "q"
    results = [
        loop.ToolResult(
            "get_ticket", {"ticket_id": "INC-1042"}, {"id": "INC-1042", "status": "open"}
        ),
        loop.ToolResult(
            "search_docs", {"query": "lockout"}, [Chunk(id="p#7", page_id="p", text="x" * 300)]
        ),
    ]
    msg = loop.plan_user_message("q", results)
    assert msg.startswith("q\n\nGathered so far in this turn:")
    assert '<tool_result tool="get_ticket" args={"ticket_id": "INC-1042"}>' in msg
    assert '"status": "open"' in msg
    assert "- p#7: " + "x" * 120 + "…" in msg  # docs are summarised for the planner, not pasted


def test_long_tool_results_are_truncated_for_the_planner():
    big = loop.ToolResult("search_tickets", {}, [{"summary": "y" * 2000}])
    assert "…(truncated)" in loop.plan_user_message("q", [big])
