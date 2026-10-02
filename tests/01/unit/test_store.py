"""Fixed-input tests for opscopilot.store — SQLite round-trips, redaction on write, purge."""

from __future__ import annotations

import sqlite3

import pytest

from opscopilot import store


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_DB", str(tmp_path / "t.db"))


def test_messages_round_trip_in_order_and_per_session():
    store.add_message("s1", "user", "hello")
    store.add_message("s1", "assistant", "hi")
    store.add_message("s2", "user", "other session")
    rows = store.messages("s1")
    assert [(r["role"], r["content"]) for r in rows] == [("user", "hello"), ("assistant", "hi")]
    assert rows[0]["tokens_est"] == store.estimate_tokens("hello") == 1
    assert [s["session_id"] for s in store.sessions()] == ["s2", "s1"] or len(store.sessions()) == 2


@pytest.mark.step(6)
def test_a_secret_is_redacted_before_it_is_written():
    row = store.add_message("s", "tool_result", '{"text": "admin is mesadmin / Nordf@rm2026! ok"}')
    assert "Nordf@rm2026!" not in row["content"]
    assert row["redacted_kinds"] == "credential"
    raw = sqlite3.connect(store.db_path()).execute("SELECT content FROM messages").fetchone()[0]
    assert "Nordf@rm2026!" not in raw


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        store.add_message("s", "system", "x")


def test_usage_rows_filter_by_session():
    store.add_usage(
        "a",
        step="route",
        provider="fake",
        model="m",
        input_tokens=10,
        output_tokens=2,
        cost_usd=0.001,
    )
    store.add_usage(
        "b",
        step="answer",
        provider="fake",
        model="m",
        input_tokens=5,
        output_tokens=1,
        cost_usd=0.0005,
    )
    assert [r["step"] for r in store.usage_rows("a")] == ["route"]
    assert len(store.usage_rows()) == 2
    assert store.usage_rows("a")[0]["tool"] == ""


def test_purge_removes_only_old_rows(monkeypatch):
    store.add_message("s", "user", "recent")
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, ts, role, content, tokens_est) "
            "VALUES ('s', '2020-01-01T00:00:00+00:00', 'user', 'ancient', 1)"
        )
    assert store.purge(older_than_days=30) == 1
    assert [r["content"] for r in store.messages("s")] == ["recent"]
