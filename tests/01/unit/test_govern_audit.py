"""Fixed-input tests for opscopilot.govern.audit — every line redacted, append-only."""

from __future__ import annotations

import json

import pytest

from opscopilot.govern import audit


@pytest.fixture(autouse=True)
def log_path(tmp_path, monkeypatch):
    path = tmp_path / "audit.log"
    monkeypatch.setenv("OPSCOPILOT_AUDIT_LOG", str(path))
    return path


def test_events_are_appended_as_json_lines(log_path):
    audit.log_event("tool_call", tool="get_ticket", args={"ticket_id": "INC-1042"})
    audit.log_event("approval", action="post_update", approved=False)
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert first["kind"] == "tool_call" and first["args"] == {"ticket_id": "INC-1042"}
    assert second["approved"] is False
    assert "ts" in first
    assert audit.read_events() == [first, second]


@pytest.mark.step(6)
def test_a_secret_never_reaches_the_log_in_the_clear(log_path):
    record = audit.log_event(
        "tool_call",
        tool="get_ticket",
        result={"updates": [{"text": "admin is mesadmin / Nordf@rm2026! ok"}]},
    )
    raw = log_path.read_text()
    assert "Nordf@rm2026!" not in raw
    assert record["redacted"] == [{"kind": "credential", "count": 1}]


def test_unknown_kinds_are_rejected():
    with pytest.raises(ValueError):
        audit.log_event("guess", x=1)


def test_events_inside_a_turn_carry_turn_id_and_ms_and_are_collected(log_path):
    audit.log_event("answer", grounded=True)  # outside any turn: no turn_id
    with audit.turn() as (tid, events):
        audit.log_event("tool_call", tool="get_ticket")
        audit.log_event("answer", grounded=True)
    assert [e["kind"] for e in events] == ["tool_call", "answer"]
    assert all(e["turn_id"] == tid and isinstance(e["ms"], int) and e["ms"] >= 0 for e in events)
    on_disk = audit.read_events()
    assert "turn_id" not in on_disk[0] and on_disk[1]["turn_id"] == tid
    assert audit.current_turn_id() is None


def test_nested_turns_do_not_mix(log_path):
    with audit.turn("outer") as (_, outer):
        audit.log_event("answer", grounded=True)
        with audit.turn("inner") as (_, inner):
            audit.log_event("tool_call", tool="x")
        audit.log_event("refusal", reason="r")
    assert [e["kind"] for e in inner] == ["tool_call"]
    assert [e["kind"] for e in outer] == ["answer", "refusal"]
