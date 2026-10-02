"""Agent-level tests: does ask() actually call the NordDesk tool and answer from its output?

Second layer, deliberately separate from tests/unit/: the model is scripted (ScriptedFake), the
MCP server is real. If tests/unit/ pass and these fail, the bug is in how the agent uses the
tool, not in the tool."""

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


def test_ticket_question_calls_get_ticket_and_answers_from_the_result(seeded_store, monkeypatch):
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("get_ticket", ticket_id="INC-1042"), FINAL],
            answers={"answer_tickets": "INC-1042 is open, P1, OT team."},
        ),
    )
    assert cli.ask("Check ticket INC-1042.") == "INC-1042 is open, P1, OT team."
    # the answer step was given the live ticket, not a memory of it
    _, answer_user = fake.calls[-1]
    assert '"status": "open"' in answer_user and '"urgency": "P1"' in answer_user
    assert fake.calls[-1][0] == cli.load_prompt("answer_tickets")  # answered from the tool


def test_general_question_needs_no_ticket_tool(seeded_store, monkeypatch):
    fake = install(
        monkeypatch, ScriptedFake(plans=[FINAL], answers={"chat": "Hi, I'm OpsCopilot."})
    )
    assert cli.ask("Hello, who are you?") == "Hi, I'm OpsCopilot."
    assert fake.calls[-1][0] == cli.load_prompt("chat")  # no tool, no ticket answer


def test_write_request_goes_through_the_tool_and_lands_in_norddesk(seeded_store, monkeypatch):
    install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("post_update", ticket_id="INC-1043", text="ribbon re-seated"), FINAL],
            answers={"answer_tickets": "Done, comment added."},
        ),
    )
    assert (
        cli.ask("Add a comment to INC-1043: ribbon re-seated, printing OK")
        == "Done, comment added."
    )
    assert store.get_ticket("INC-1043")["updates"][-1]["text"] == "ribbon re-seated"


def test_denied_write_changes_nothing(seeded_store, monkeypatch):
    from opscopilot.mcp_tickets import approval

    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "0")
    monkeypatch.setattr(approval.typer, "confirm", lambda *a, **k: False)
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("post_update", ticket_id="INC-1043", text="closing", status="closed")]
        ),
    )
    assert "not approved" in cli.ask("Close INC-1043")
    assert store.get_ticket("INC-1043")["status"] == "open"
    assert len(fake.calls) == 1  # no answer step was even attempted


def test_the_tool_result_reaches_the_model_inside_the_users_message(seeded_store, monkeypatch):
    # the answer call gets ONE user message: the question plus the fresh <tool_result>. Sent as
    # the model's own (assistant) message instead, a real model carries on "its" text: it invents
    # tool calls and contradicts the data ("INC-1042 does not exist") — while every other test
    # here, which only looks at what reached the model, stays green
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("get_ticket", ticket_id="INC-1042"), FINAL],
            answers={"answer_tickets": "INC-1042 is open, P1."},
        ),
    )
    cli.ask("Check ticket INC-1042.")
    messages = fake.seen_messages[-1]
    assert messages[-1]["role"] == "user", [m["role"] for m in messages]
    assert "Check ticket INC-1042." in messages[-1]["content"]
    assert "<tool_result" in messages[-1]["content"]
    assert not [m for m in messages if m["role"] == "assistant" and "<tool_result" in m["content"]]


def test_a_write_asked_from_the_chat_page_is_refused_with_a_sentence(seeded_store, monkeypatch):
    # the chat page calls ask_traced() and has no terminal: nobody can say "y", so the write is
    # refused — with an answer, not an error page — and NordDesk stays as it was
    from opscopilot.mcp_tickets import approval

    monkeypatch.setenv("OPSCOPILOT_AUTO_APPROVE", "0")
    monkeypatch.setattr(approval.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(approval.typer, "confirm", lambda *a, **k: pytest.fail("asked!"))
    install(
        monkeypatch,
        ScriptedFake(plans=[plan("post_update", ticket_id="INC-1042", text="test from the page")]),
    )
    before = store.get_ticket("INC-1042")["updates"]
    answer, _, _ = cli.ask_traced("Add a comment to INC-1042: test from the page")
    assert "not approved" in answer
    assert store.get_ticket("INC-1042")["updates"] == before
    assert approval.approvals[-1][2] is False


def test_planner_output_is_validated_as_toolplan(seeded_store, monkeypatch):
    from pydantic import ValidationError

    from opscopilot.llm.client import FakeLLMClient

    raw = FakeLLMClient(responses={})
    raw.add(cli.route_system(), "Check ticket INC-1042.", '{"tool": "teleport", "reason": "?"}')
    monkeypatch.setattr(cli, "get_llm_client", lambda: raw)
    with pytest.raises(ValidationError):
        cli.ask("Check ticket INC-1042.")


def test_planner_is_given_every_system_id(seeded_store):
    # users name systems in Polish ("MES linii pakowania"); the `system` filter needs the exact id,
    # so the planner must see every id — without them a search finds nothing and the answer says
    # "no problems" while there is one
    prompt = cli.route_system()
    missing = [s["id"] for s in store.load()["systems"] if s["id"] not in prompt]
    assert not missing, f"route_system() does not name these system ids: {missing}"


@pytest.mark.parametrize(
    ("tool", "args"),
    [("search_docs", {"query": "restart MES"}), ("impact_estimate", {"ticket_id": "INC-1042"})],
)
def test_a_tool_the_app_cannot_run_yet_does_not_crash_ask(
    seeded_store, monkeypatch, tmp_path, tool, args
):
    # the planner's schema already offers tools that arrive later; picking one must never end in
    # a traceback (KeyError on the ticket tools) — the user gets an answer either way
    from helpers import grounded

    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))
    install(
        monkeypatch,
        ScriptedFake(
            plans=[plan(tool, **args), FINAL],
            answers={
                name: "Nie mogę tego jeszcze sprawdzić."
                for name in ("chat", "answer_tickets", "answer_history")
            }
            | {"answer": grounded("Nie mogę tego jeszcze sprawdzić.")},
        ),
    )
    assert isinstance(cli.ask("Jak zrestartować MES linii pakowania?"), str)


def _cite_first_doc(messages, text):
    import re

    from helpers import grounded

    ids = re.findall(r'<doc id="([^"]+)"', messages[-1]["content"])
    return grounded(text, ids[:1])
