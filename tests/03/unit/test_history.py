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


def test_record_turn_stores_user_tools_and_assistant_in_order():
    seed_ticket_turn()
    assert [r["role"] for r in store.messages("s")] == [
        "user",
        "tool_call",
        "tool_result",
        "assistant",
    ]


def test_replay_mode_puts_the_old_tool_result_into_the_assistant_turn(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_TOOL_RESULTS", "replay")
    seed_ticket_turn()
    w = history.window("s")
    assert [m["role"] for m in w] == ["user", "assistant"]
    assert '<tool_result tool="get_ticket"' in w[1]["content"]
    assert '"status": "open"' in w[1]["content"]
    assert w[1]["content"].endswith("INC-1042 is open, P1.")


def test_drop_mode_keeps_text_only(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_TOOL_RESULTS", "drop")
    seed_ticket_turn()
    w = history.window("s")
    assert w[1]["content"] == "INC-1042 is open, P1."


def test_summarise_mode_keeps_a_one_line_trace(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_TOOL_RESULTS", "summarise")
    seed_ticket_turn()
    w = history.window("s")
    assert w[1]["content"].startswith('(looked up get_ticket {"ticket_id": "INC-1042"} at ')
    assert '"status": "open"' not in w[1]["content"]


def test_bad_mode_is_an_error(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_TOOL_RESULTS", "cache")
    with pytest.raises(ValueError):
        history.window("s")


def test_message_cap_keeps_the_newest_and_starts_with_a_user_turn(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_MESSAGES", "3")
    for i in range(4):
        history.record_turn("s", f"q{i}", f"a{i}")
    w = history.window("s")
    # last 3 of [q0 a0 q1 a1 q2 a2 q3 a3] = [a2 q3 a3] -> leading assistant dropped
    assert [m["content"] for m in w] == ["q3", "a3"]


def test_token_cap_drops_oldest_whole_messages(monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_HISTORY_TOKENS", "30")  # ~120 chars
    history.record_turn("s", "x" * 200, "long answer " * 5)  # far over budget on its own
    history.record_turn("s", "short q", "short a")
    w = history.window("s")
    assert [m["content"] for m in w] == ["short q", "short a"]


def test_empty_session_is_an_empty_window():
    assert history.window("nope") == []


def test_state_questions_are_recognised():
    for q in (
        "Is it still open?",
        "What's the status now?",
        "Who is working on it?",
        "any update?",
    ):
        assert history.is_state_question(q), q
    for q in ("What did you say the panel number was?", "Summarise our conversation."):
        assert not history.is_state_question(q), q
    for q in ("Czy jest nadal otwarte?", "Kto nad nim teraz pracuje?", "Jaki jest status?"):
        assert history.is_state_question(q), q
    for q in ("Jaki był numer panelu z tamtej odpowiedzi?", "Streść naszą rozmowę."):
        assert not history.is_state_question(q), q


