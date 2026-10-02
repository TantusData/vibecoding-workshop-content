"""Fixed-input tests for the NordDesk MCP *client* — real server subprocess over stdio, no model.

These prove the wire works: each client function, called directly with a fixed input, returns the
same JSON the server's own function returns (see test_norddesk_store.py). The agent is not involved.
"""

from __future__ import annotations

import json

import pytest

from norddesk_mcp import store
from opscopilot.mcp_tickets import approval, client


@pytest.fixture
def seeded_store(tmp_path, monkeypatch):
    path = tmp_path / "norddesk.json"
    monkeypatch.setenv("NORDDESK_STORE", str(path))
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "1")
    store.init_store(force=True)
    approval.approvals.clear()
    return path


def test_get_ticket_over_mcp_matches_the_server_function(seeded_store):
    over_wire = client.run(client.get_ticket("INC-1042"))
    assert over_wire == store.get_ticket("INC-1042")
    assert over_wire["urgency"] == "P1"


def test_get_ticket_unknown_id_is_an_error_dict_not_an_exception(seeded_store):
    assert client.run(client.get_ticket("INC-9999")) == {"error": "ticket 'INC-9999' not found"}


def test_search_and_system_status_over_mcp(seeded_store):
    hits = client.run(client.search_tickets("batch"))
    assert [h["id"] for h in hits] == ["INC-1039", "CHG-0310"]
    assert client.run(client.search_tickets(status="resolved"))[0]["id"] == "INC-1040"
    [status] = client.run(client.get_system_status("palletiser-l3"))
    assert status["open_tickets"] == 1
    assert len(client.run(client.get_system_status())) == 7


def test_writes_pass_the_gate_and_persist(seeded_store):
    created = client.run(client.create_ticket("Wire test", "created over MCP", type="question"))
    assert created["id"] == "Q-0513"
    updated = client.run(client.post_update("Q-0513", "closing", status="closed"))
    assert updated["status"] == "closed"
    assert updated["updates"][-1]["text"] == "closing"
    # persisted on disk, visible to a direct load
    assert store.get_ticket("Q-0513")["status"] == "closed"
    assert [a[0] for a in approval.approvals] == ["create_ticket", "post_update"]
    assert all(a[2] for a in approval.approvals)


def test_writes_are_refused_without_approval(seeded_store, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "0")
    monkeypatch.setattr(approval.typer, "confirm", lambda *a, **k: False)
    with pytest.raises(approval.ApprovalDenied):
        client.run(client.post_update("INC-1042", "should never land"))
    assert store.get_ticket("INC-1042")["updates"][-1]["text"] != "should never land"
    assert approval.approvals[-1][2] is False


def test_reads_never_ask_for_approval(seeded_store, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "0")
    monkeypatch.setattr(approval.typer, "confirm", lambda *a, **k: pytest.fail("asked!"))
    assert client.run(client.get_ticket("INC-1043"))["id"] == "INC-1043"


def test_client_sees_disk_edits_between_calls(seeded_store):
    """The tool side of the stale-answer story: two calls, the file changed in between."""
    assert client.run(client.get_ticket("INC-1042"))["status"] == "open"
    data = json.loads(seeded_store.read_text())
    next(t for t in data["tickets"] if t["id"] == "INC-1042")["status"] = "resolved"
    seeded_store.write_text(json.dumps(data))
    assert client.run(client.get_ticket("INC-1042"))["status"] == "resolved"


def test_writes_are_refused_when_no_terminal_can_ask(seeded_store, monkeypatch):
    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "0")
    monkeypatch.setattr(approval.sys.stdin, "isatty", lambda: False)
    with pytest.raises(approval.ApprovalDenied, match="no terminal"):
        client.run(client.create_ticket("x", "y"))
    assert len(store.load()["tickets"]) == 7
    # a refusal nobody was asked about is still a decision: it is recorded like any other
    assert approval.approvals[-1][0] == "create_ticket" and approval.approvals[-1][2] is False


def test_get_oncall_over_mcp(seeded_store):
    assert client.run(client.get_oncall("day")) == store.get_oncall("day")
    assert len(client.run(client.get_oncall())) == 7
