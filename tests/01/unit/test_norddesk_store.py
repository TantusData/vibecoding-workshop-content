"""Fixed-input tests for the NordDesk server's tool functions — no MCP, no model, no agent.

Each test calls the plain Python function in norddesk_mcp.store with a fixed input and asserts an
exact output. If one of these fails, the *tool* is broken; if these pass and an agent still answers
wrongly, the bug is in how the agent uses the tool (see tests/agent/).
"""

from __future__ import annotations

import json

import pytest

from norddesk_mcp import store


@pytest.fixture
def seeded_store(tmp_path, monkeypatch):
    """A fresh copy of the committed seed in a temp file; NORDDESK_STORE points at it."""
    path = tmp_path / "norddesk.json"
    monkeypatch.setenv("NORDDESK_STORE", str(path))
    store.init_store(force=True)
    return path


def test_get_ticket_returns_exact_seed_record(seeded_store):
    ticket = store.get_ticket("INC-1042")
    expected = next(
        t for t in json.loads(store.SEED_PATH.read_text())["tickets"] if t["id"] == "INC-1042"
    )
    assert ticket == expected
    assert ticket["urgency"] == "P1"
    assert ticket["system"] == "palletiser-l3"
    assert ticket["status"] == "open"
    assert len(ticket["updates"]) == 3


def test_get_ticket_is_case_insensitive_and_reports_unknown_ids(seeded_store):
    assert store.get_ticket("inc-1042")["id"] == "INC-1042"
    assert store.get_ticket("INC-9999") == {"error": "ticket 'INC-9999' not found"}


def test_search_tickets_by_text_returns_brief_records_newest_first(seeded_store):
    hits = store.search_tickets("batch")
    assert [h["id"] for h in hits] == ["INC-1039", "CHG-0310"]
    # plain substring matching, by design: "mes" also hits "comes" in INC-1040's last comment
    assert [h["id"] for h in store.search_tickets("MES")] == ["INC-1039", "CHG-0310", "INC-1040"]
    assert set(hits[0]) == {"id", "type", "system", "urgency", "status", "summary", "updated_at"}


def test_search_tickets_filters_by_status_and_system(seeded_store):
    assert [t["id"] for t in store.search_tickets(status="resolved")] == ["INC-1040"]
    assert [t["id"] for t in store.search_tickets(system="vpn")] == ["Q-0512", "REQ-2201"]
    assert store.search_tickets("nothing matches this") == []


def test_get_system_status_counts_open_tickets(seeded_store):
    [status] = store.get_system_status("palletiser-l3")
    assert status["status"] == "degraded"
    assert status["open_tickets"] == 1
    [mes] = store.get_system_status("Packing-line MES")  # by name, case-insensitive
    assert mes["id"] == "mes-packing"
    assert mes["open_tickets"] == 2  # INC-1039 (in_progress) + CHG-0310 (open)
    assert len(store.get_system_status()) == 7


def test_create_ticket_assigns_next_padded_id_and_persists(seeded_store):
    ticket = store.create_ticket("Test summary", "Test description", type="question")
    assert ticket["id"] == "Q-0513"
    assert ticket["status"] == "open"
    assert ticket["team"] == "unassigned"
    assert ticket["updates"] == []
    # persisted: a fresh load sees it
    assert store.get_ticket("Q-0513")["summary"] == "Test summary"
    assert json.loads(seeded_store.read_text())["tickets"][-1]["id"] == "Q-0513"


def test_create_ticket_rejects_bad_type_and_urgency(seeded_store):
    assert "unknown type" in store.create_ticket("s", "d", type="bug")["error"]
    assert "unknown urgency" in store.create_ticket("s", "d", urgency="P9")["error"]
    assert len(store.load()["tickets"]) == 7  # nothing written


def test_post_update_appends_comment_sets_status_and_touches_updated_at(seeded_store):
    before = store.get_ticket("INC-1043")["updated_at"]
    ticket = store.post_update("INC-1043", "Ribbon re-seated, printing OK", status="resolved")
    assert ticket["status"] == "resolved"
    assert ticket["updates"][-1]["text"] == "Ribbon re-seated, printing OK"
    assert ticket["updates"][-1]["author"] == "opscopilot"
    assert ticket["updated_at"] > before
    assert store.get_ticket("INC-1043")["status"] == "resolved"
    assert store.post_update("INC-0000", "x") == {"error": "ticket 'INC-0000' not found"}


def test_every_call_rereads_the_file(seeded_store):
    """The stale-answer mechanism: an edit on disk is visible on the very next call."""
    assert store.get_ticket("INC-1042")["status"] == "open"
    data = json.loads(seeded_store.read_text())
    next(t for t in data["tickets"] if t["id"] == "INC-1042")["status"] = "resolved"
    seeded_store.write_text(json.dumps(data))
    assert store.get_ticket("INC-1042")["status"] == "resolved"


def test_seed_is_never_written(seeded_store):
    seed_before = store.SEED_PATH.read_bytes()
    store.create_ticket("s", "d")
    store.post_update("INC-1042", "x")
    assert store.SEED_PATH.read_bytes() == seed_before


def test_get_oncall_filters_by_shift(seeded_store):
    night = store.get_oncall("night")
    assert [(r["team"], r["name"]) for r in night] == [
        ("ot", "Piotr Wiśniewski"),
        ("infra", "Tomasz Lewandowski"),
        ("servicedesk", "Kamil Wójcik"),
    ]
    assert len(store.get_oncall()) == 7
    assert store.get_oncall("weekend") == []
