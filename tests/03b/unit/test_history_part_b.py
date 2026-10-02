"""Fixed-input tests for opscopilot.history — the window and the three tool-result modes."""

from __future__ import annotations

import pytest

from opscopilot import history, store


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_DB", str(tmp_path / "t.db"))


def seed_ticket_turn(session="s"):
    history.record_turn(
        session,
        "Check INC-1042.",
        "INC-1042 is open, P1.",
        tool_calls=[
            ("get_ticket", {"ticket_id": "INC-1042"}, {"id": "INC-1042", "status": "open"})
        ],
    )


def test_last_tool_call_is_the_most_recent_one():
    assert history.last_tool_call("s") is None
    history.record_turn("s", "q1", "a1", [("search_tickets", {"query": "MES"}, [])])
    history.record_turn("s", "q2", "a2", [("get_ticket", {"ticket_id": "INC-1042"}, {})])
    assert history.last_tool_call("s") == ("get_ticket", {"ticket_id": "INC-1042"})


def test_router_option_is_naive_by_default_and_guarded_with_refetch(monkeypatch):
    assert "no new lookup" in history.router_history_option()
    monkeypatch.setenv("OPSCOPILOT_HISTORY_REFETCH", "1")
    assert "always needs a fresh\n  tool call" in history.router_history_option()
