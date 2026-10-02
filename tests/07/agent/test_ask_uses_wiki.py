"""Agent-level tests: does ask() ground doc questions in retrieved chunks and cite them?

Scripted model + fake embedder + the real Nordwiki server. Retrieval quality itself is graded by
`make eval`; this checks the *use* of retrieval (search_docs as a loop tool since ext-loop)."""

from __future__ import annotations

import re

import pytest

from opscopilot import cli
from opscopilot.govern import injection
from opscopilot.rag.retrieve import retrieve as _retrieve
from helpers import FINAL, ScriptedFake, grounded, install, plan


@pytest.fixture(autouse=True)
def fake_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))


def retrieve(q):
    """What ask() actually hands the model: retrieved chunks after injection sanitisation."""
    chunks, _ = injection.sanitize_docs(_retrieve(q))
    return chunks


def doc_ids(messages):
    return re.findall(r'<doc id="([^"]+)"', messages[-1]["content"])


def test_doc_question_is_answered_from_retrieved_chunks_with_citations(monkeypatch):
    q = "VPN setup: which client do we use?"
    top = retrieve(q)[0].id
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("search_docs", query=q), FINAL],
            answers={"answer": lambda m: grounded("FortiClient.", [top])},
        ),
    )
    assert cli.ask(q) == f"FortiClient.\n\nSources: {top}"
    # the model was handed the chunks as <doc> data, not as instructions
    _, user = fake.calls[-1]
    assert f'<doc id="{top}"' in user and "</doc>" in user


def test_in_scope_but_out_of_corpus_question_gets_the_exact_not_found(monkeypatch):
    q = "How do I reset my ERP password?"  # in scope (ERP, password reset), not in any doc
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("search_docs", query="ERP password reset"), FINAL],
            answers={"answer": grounded(cli.NOT_FOUND)},
        ),
    )
    assert cli.ask(q) == cli.NOT_FOUND
    assert doc_ids(fake.seen_messages[-1])  # retrieval still happened; the model said not found


def test_citations_the_model_invents_are_dropped(monkeypatch):
    q = "How long are backups kept?"
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("search_docs", query="backup retention"), FINAL],
            answers={"answer": lambda m: grounded("35 days.", [doc_ids(m)[0], "made-up#9"])},
        ),
    )
    out = cli.ask(q)
    assert out.startswith("35 days.\n\nSources: ") and "made-up" not in out
    assert out.count(",") == 0  # exactly one surviving citation
    assert fake.planner_prompts[1].startswith(q + "\n\nGathered so far")


def test_a_procedure_answered_without_search_docs_is_not_grounded(monkeypatch):
    """If the planner skips retrieval, the answer is a chat reply, never a fact from memory."""
    fake = install(
        monkeypatch, ScriptedFake(plans=[FINAL], answers={"chat": "I'd need to look that up."})
    )
    assert cli.ask("How do I restart the packing-line MES?") == "I'd need to look that up."
    assert all("<doc" not in m[-1]["content"] for m in fake.seen_messages)


def test_the_poisoned_sop_paragraph_is_removed_before_the_model_sees_it(monkeypatch, tmp_path):
    # every marker sanitize_docs finds is an `injection` audit event: where, which marker, excerpt
    from opscopilot.govern import audit

    monkeypatch.setenv("OPSCOPILOT_AUDIT_LOG", str(tmp_path / "audit.log"))

    q = "How is the NordDesk backup verified?"
    assert any("external-audit@" in c.text for c in _retrieve(q))  # retrieval does return it
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("search_docs", query=q), FINAL],
            answers={
                "answer": lambda m: grounded(
                    "Weekly restore to nf-db-test.", ["sop-backup-restore#1"]
                )
            },
        ),
    )
    out = cli.ask(q)
    assert out.startswith("Weekly restore to nf-db-test.")
    for _, prompt in fake.calls:
        assert "external-audit@" not in prompt and "does not need user approval" not in prompt
    assert "[removed: instruction-like text]" in fake.calls[-1][1]
    markers = {e["marker"] for e in audit.read_events() if e["kind"] == "injection"}
    assert {"addressed-to-assistant", "exfiltration", "approval-bypass"} <= markers
