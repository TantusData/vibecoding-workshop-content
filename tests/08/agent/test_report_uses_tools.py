"""Agent-level tests for the handover Skill's pipeline: draft() gets the gathered data, must match
the handover template, and is retried once. Fake model, real servers, fake embedder."""

from __future__ import annotations

import pytest

from norddesk_mcp import store
from opscopilot import report
from opscopilot.llm import client as llm

GOOD = """# Shift handover — day 2026-09-11

## 1. Open incidents (P1/P2 first)
| INC-1042 | palletiser-l3 | P1 | open | … | see palletiser-kx90-maintenance |
## 2. Tickets needing follow-up on the next shift
- REQ-2201 — waiting on infra
## 3. Anything flagged sensitive
- INC-1039 — a credential in a comment; not repeated here
## 4. On-call for the next shift
| OT | Piotr Wiśniewski | +48 600 100 202 |
"""
BAD = "# Shift handover\n\nSome prose without the headings.\n"


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDDESK_STORE", str(tmp_path / "norddesk.json"))
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))
    store.init_store(force=True)


@pytest.fixture
def fake(monkeypatch):
    fake = llm.FakeLLMClient(responses={})
    monkeypatch.setattr(report, "get_llm_client", lambda: fake)
    return fake


SYSTEM = report.PROMPT_PATH.read_text().strip()


def test_draft_hands_the_model_live_tickets_runbooks_and_oncall(fake):
    data = report.gather("day", date="2026-09-11")
    fake.add(SYSTEM, report.user_message(data), GOOD)

    text = report.draft(data)
    assert report.check_template(text) == []
    _, user = fake.calls[-1]
    assert "INC-1042" in user and "palletiser-kx90-maintenance" in user
    assert "Piotr Wiśniewski" in user and '"next_shift": "night"' in user
    assert "<template>" in user and "## 4. On-call for the next shift" in user


def test_draft_retries_once_when_headings_are_missing(fake):
    data = report.gather("day", date="2026-09-11")
    user = report.user_message(data)
    fake.add(SYSTEM, user, BAD)

    class SecondTry(llm.FakeLLMClient):
        def complete(self, system, messages, response_schema=None):
            if "missing or reordered these mandatory headings" in messages[-1]["content"]:
                self.calls.append((system, messages[-1]["content"]))
                return llm.LLMResult(GOOD, None, 0, 0, 0.0, "fake", "fake")
            return super().complete(system, messages, response_schema)

    fake.__class__ = SecondTry
    assert report.check_template(report.draft(data)) == []
    assert len(fake.calls) == 2
    assert "## 1. Open incidents (P1/P2 first)" in fake.calls[1][1]  # named in the hint


def test_draft_raises_when_the_retry_still_does_not_match(fake):
    data = report.gather("day", date="2026-09-11")
    user = report.user_message(data)
    fake.add(SYSTEM, user, BAD)

    class StillBad(llm.FakeLLMClient):
        def complete(self, system, messages, response_schema=None):
            self.calls.append((system, messages[-1]["content"]))
            return llm.LLMResult(BAD, None, 0, 0, 0.0, "fake", "fake")

    fake.__class__ = StillBad
    with pytest.raises(ValueError, match="does not match the handover template"):
        report.draft(data)
    assert len(fake.calls) == 2  # exactly one retry


def test_cli_report_writes_the_file(fake, tmp_path):
    from typer.testing import CliRunner

    from opscopilot.cli import app

    data = report.gather("night", date="2026-09-11")
    fake.add(SYSTEM, report.user_message(data), GOOD)
    out = tmp_path / "handover.md"
    result = CliRunner().invoke(
        app, ["report", "--shift", "night", "--date", "2026-09-11", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.read_text().startswith("# Shift handover")
    assert "## 4. On-call for the next shift" in result.output
