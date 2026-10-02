"""Agent-level test for CP5 (rebased on ext-loop): "Why is INC-1042 P1?" is answered from the
regression's numbers, handed to the model as a tool result — a number it did not invent."""

from __future__ import annotations

import pytest

from norddesk_mcp import store
from opscopilot import cli
from helpers import FINAL, ScriptedFake, install, plan


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDDESK_STORE", str(tmp_path / "norddesk.json"))
    monkeypatch.setenv("OPSCOPILOT_AUDIT_LOG", str(tmp_path / "audit.log"))
    store.init_store(force=True)


def test_why_p1_routes_to_impact_estimate_and_the_numbers_reach_the_answer_prompt(monkeypatch):
    fake = install(
        monkeypatch,
        ScriptedFake(
            plans=[plan("impact_estimate", ticket_id="INC-1042"), FINAL],
            answers={"answer_tickets": "P1: ~115 min, ~EUR 8k."},
        ),
    )
    assert cli.ask("Why is INC-1042 ranked P1?") == "P1: ~115 min, ~EUR 8k."
    _, prompt = fake.calls[-1]
    assert '"downtime_min": 115.0' in prompt and '"eur_impact": 8033.0' in prompt
    assert "category=mechanical" in prompt and "historical-incident regression" in prompt


def test_impact_estimate_for_an_unknown_ticket_is_an_error_not_a_guess():
    assert cli.impact_estimate("INC-9999") == {"error": "ticket 'INC-9999' not found"}


def test_impact_cli_prints_the_explanation():
    from typer.testing import CliRunner

    result = CliRunner().invoke(cli.app, ["impact", "INC-1039"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("Estimated downtime ")
    assert '"orders_at_risk"' in result.output
