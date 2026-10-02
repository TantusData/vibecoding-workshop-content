"""Agent-level tests: does ask() run the bounded loop — several tools in one turn, the cap, the
repetition guard — and hand *every* gathered result to the answer step?

Companion to tests/unit/test_loop.py: that file proves run_loop() with scripted callables; this
one proves cli.ask() actually uses it. If the unit tests pass and these fail, the loop exists but
the app still routes one tool per question."""

from __future__ import annotations

import pytest

from norddesk_mcp import store
from opscopilot import cli
from helpers import FINAL, ScriptedFake, install, plan


@pytest.fixture
def seeded_store(tmp_path, monkeypatch):
    path = tmp_path / "norddesk.json"
    monkeypatch.setenv("NORDDESK_STORE", str(path))
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "1")
    store.init_store(force=True)
    return path


def test_two_tools_in_one_turn_ticket_then_oncall(seeded_store, monkeypatch):
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[
                plan("get_ticket", ticket_id="INC-1042"),
                plan("get_oncall", shift="night"),
                FINAL,
            ],
            answers={
                "answer_tickets": "INC-1042 is open (P1); tonight OT on-call is Piotr Wiśniewski."
            },
        ),
    )
    out = cli.ask("Check INC-1042 and tell me who is on call tonight.")
    assert out.startswith("INC-1042 is open (P1); tonight OT on-call is Piotr")
    _, answer_user = fake.calls[-1]
    assert '<tool_result tool="get_ticket"' in answer_user
    assert '<tool_result tool="get_oncall"' in answer_user
    assert "Piotr Wiśniewski" in answer_user  # the second tool's real output reached the answer
    # planner asked three times: fresh question, then twice with what was gathered so far
    assert len(fake.planner_prompts) == 3
    assert "Gathered so far" not in fake.planner_prompts[0]
    assert "Gathered so far" in fake.planner_prompts[1] and "INC-1042" in fake.planner_prompts[1]


def test_the_cap_stops_the_loop_and_the_planner_is_not_asked_again(seeded_store, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_MAX_TOOL_CALLS", "3")
    ids = ["INC-1039", "INC-1040", "INC-1042", "INC-1043", "CHG-0310"]
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("get_ticket", ticket_id=i) for i in ids],
            answers={"answer_tickets": "Here is what I found."},
        ),
    )
    assert cli.ask("Summarise every incident.").startswith("Here is what I found.")
    assert len(fake.planner_prompts) == 3  # one per executed call; never a 4th
    _, answer_user = fake.calls[-1]
    assert answer_user.count('<tool_result tool="get_ticket"') == 3
    assert "INC-1043" not in answer_user  # the 4th planned call never ran


def test_a_repeated_identical_call_is_not_executed_twice(seeded_store, monkeypatch):
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[
                plan("get_ticket", ticket_id="INC-1042"),
                plan("get_ticket", ticket_id="INC-1042"),
                plan("get_oncall", shift="night"),
            ],
            answers={"answer_tickets": "INC-1042 is open."},
        ),
    )
    assert cli.ask("Check INC-1042.").startswith("INC-1042 is open.")
    _, answer_user = fake.calls[-1]
    assert answer_user.count("<tool_result") == 1
    assert "get_oncall" not in answer_user  # the loop stopped at the repeat
