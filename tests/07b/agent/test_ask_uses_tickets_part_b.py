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


@pytest.mark.step(7)
def test_two_tools_in_one_turn_ticket_then_procedure(seeded_store, monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[
                plan("get_ticket", ticket_id="INC-1042"),
                plan("search_docs", query="palletiser lockout procedure"),
                FINAL,
            ],
            answers={"answer": lambda m: _cite_first_doc(m, "Lockout: 20-min cool-down, P3-07.")},
        ),
    )
    out = cli.ask("Check INC-1042 and tell me the lockout procedure for that palletiser.")
    assert out.startswith(
        "Lockout: 20-min cool-down, P3-07.\n\nSources: palletiser-kx90-maintenance#"
    )
    _, answer_user = fake.calls[-1]
    assert (
        '<tool_result tool="get_ticket"' in answer_user
        and '<doc id="palletiser-kx90' in answer_user
    )
    assert len(fake.planner_prompts) == 3 and "Gathered so far" in fake.planner_prompts[2]


def _cite_first_doc(messages, text):
    import re

    from helpers import grounded

    ids = re.findall(r'<doc id="([^"]+)"', messages[-1]["content"])
    return grounded(text, ids[:1])
