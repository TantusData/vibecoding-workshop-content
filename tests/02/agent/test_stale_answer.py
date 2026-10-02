"""The stale-answer story (S10) at the application level, stateless form.

The tool's own test (tests/unit) proves the server re-reads its file. This proves the *agent*
re-fetches when it does call the tool: ask() twice without a session, the ticket changes on disk
in between, and the second answer step is handed the new state — nothing is cached in the app.
(With a session, ext-history deliberately makes this go stale; see test_ask_with_history.)"""

from __future__ import annotations

import json

import pytest

from norddesk_mcp import store
from opscopilot import cli
from opscopilot.mcp_tickets import client as tickets
from helpers import FINAL, ScriptedFake, install, plan


@pytest.fixture
def seeded_store(tmp_path, monkeypatch):
    path = tmp_path / "norddesk.json"
    monkeypatch.setenv("NORDDESK_STORE", str(path))
    store.init_store(force=True)
    return path


def test_second_ask_refetches_the_ticket(seeded_store, monkeypatch):
    q = "What is the status of INC-1042?"
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[  # one list per turn
                [plan("get_ticket", ticket_id="INC-1042"), FINAL],
                [plan("get_ticket", ticket_id="INC-1042"), FINAL],
            ],
            answers={
                "answer_tickets": lambda m: (
                    "resolved" if '"status": "resolved"' in m[-1]["content"] else "open"
                )
            },
        ),
    )
    calls: list[str] = []
    real_get_ticket = tickets.get_ticket

    async def counting_get_ticket(ticket_id: str):
        calls.append(ticket_id)
        return await real_get_ticket(ticket_id)

    monkeypatch.setitem(tickets.TOOLS, "get_ticket", counting_get_ticket)

    assert cli.ask(q) == "open"
    data = json.loads(seeded_store.read_text())
    next(t for t in data["tickets"] if t["id"] == "INC-1042")["status"] = "resolved"
    seeded_store.write_text(json.dumps(data))
    assert cli.ask(q) == "resolved"
    assert calls == ["INC-1042", "INC-1042"]  # the tool was invoked both times
    assert '"status": "resolved"' in fake.calls[-1][1]
