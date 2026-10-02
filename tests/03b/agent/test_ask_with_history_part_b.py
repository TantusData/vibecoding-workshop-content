"""Agent-level tests for ext-history (rebased on ext-loop): what the model is handed on a
follow-up turn, in each tool-result mode. Scripted model, real servers, temp DB. The stale answer
is shown as a *mechanism* (the replayed old status is in the prompt; no lookup happens); the live
demo (`make demo-stale`) shows the model acting on it."""

from __future__ import annotations

import json
import re

import pytest

from norddesk_mcp import store as norddesk
from opscopilot import cli, store
from helpers import FINAL, ScriptedFake, install, plan


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDDESK_STORE", str(tmp_path / "norddesk.json"))
    monkeypatch.setenv("OPSCOPILOT_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("OPSCOPILOT_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "1")
    norddesk.init_store(force=True)


def first_turn(monkeypatch, *follow_up_plans):
    """Turn 1 looks INC-1042 up; then the ticket is resolved behind the agent's back.
    The follow-up turn's planner steps are given by `follow_up_plans`."""
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[[plan("get_ticket", ticket_id="INC-1042"), FINAL], list(follow_up_plans)],
            answers={"answer_tickets": "Status noted.", "answer_history": "From memory."},
        ),
    )
    assert cli.ask("Check INC-1042.", session_id="s") == "Status noted."
    norddesk.post_update("INC-1042", "Sensor realigned, line running", status="resolved")
    return fake


def prior_of(fake, call_index):
    return fake.seen_messages[call_index][:-1]


def planner_calls(fake):
    """Indices of the planner's calls, in order (robust to whether a scope call happened)."""
    return [
        i for i, (system, _) in enumerate(fake.calls) if system.startswith(cli.route_system()[:40])
    ]


def tool_calls(session):
    return sum(1 for m in store.messages(session) if m["role"] == "tool_call")


def test_refetch_override_reruns_the_last_lookup_for_a_state_question(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_REFETCH", "1")
    fake = first_turn(monkeypatch, FINAL)
    assert cli.ask("Is it still open?", session_id="s") == "Status noted."
    assert tool_calls("s") == 2  # re-ran get_ticket despite the planner's `final`
    assert '"status": "resolved"' in fake.calls[-1][1]  # the answer step got the fresh state


def test_refetch_override_leaves_non_state_follow_ups_to_memory(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_REFETCH", "1")
    first_turn(monkeypatch, FINAL)
    assert cli.ask("What did you say the summary was?", session_id="s") == "From memory."
    assert tool_calls("s") == 1


