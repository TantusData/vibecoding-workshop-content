"""Fixed-input tests for opscopilot.report — real servers, fake embedder, NO model.

gather() is a tool composition and must be deterministic; check_template() is a pure function.
The model-facing draft() is covered at the agent layer (tests/agent/test_report_uses_tools.py).
"""

from __future__ import annotations

import pytest

from norddesk_mcp import store
from opscopilot import report

FULL_DOC = """# Shift handover — day 2026-09-11

## 1. Open incidents (P1/P2 first)
| INC-1042 |
## 2. Tickets needing follow-up on the next shift
- REQ-2201
## 3. Anything flagged sensitive
- INC-1039
## 4. On-call for the next shift
| OT | Piotr |
## 5. One-paragraph summary for management
Fine.
"""


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    path = tmp_path / "norddesk.json"
    monkeypatch.setenv("NORDDESK_STORE", str(path))
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "fake")
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "idx"))
    store.init_store(force=True)


def test_check_template_accepts_a_conforming_document():
    assert report.check_template(FULL_DOC) == []


def test_check_template_reports_missing_and_reordered_headings():
    assert report.check_template("# nothing here") == report.REQUIRED_HEADINGS
    # heading 3 dropped, heading 4 renamed to 3 -> only 4 is missing
    swapped = FULL_DOC.replace("## 3. Anything flagged sensitive", "## X").replace(
        "## 4. On-call for the next shift", "## 3. Anything flagged sensitive"
    )
    assert report.check_template(swapped) == ["## 4. On-call for the next shift"]
    # heading 1 moved to the end -> 2, 3, 4 now precede it and count as out of order
    reordered = (
        FULL_DOC.replace("## 1. Open incidents (P1/P2 first)\n| INC-1042 |\n", "")
        + "## 1. Open incidents (P1/P2 first)\n"
    )
    assert report.check_template(reordered) == report.REQUIRED_HEADINGS[1:]


def test_check_template_wants_exact_headings():
    assert "## 1. Open incidents (P1/P2 first)" in report.check_template(
        FULL_DOC.replace("## 1. Open incidents (P1/P2 first)", "## 1. Open incidents")
    )


def test_gather_composes_tickets_runbooks_and_oncall():
    data = report.gather("day", date="2026-09-11")
    assert data.next_shift == "night"
    assert data.outgoing_lead == "Marek Zieliński" and data.incoming_lead == "Piotr Wiśniewski"
    # incidents: open/in_progress, P1/P2 first; resolved INC-1040 excluded
    assert [t["id"] for t in data.open_incidents] == ["INC-1042", "INC-1039", "INC-1043"]
    assert [t["id"] for t in data.follow_ups] == ["CHG-0310", "Q-0512", "REQ-2201"]
    assert data.stats == {
        "open_incidents": 3,
        "p1_p2_incidents": 2,
        "follow_ups": 3,
        "tickets_seen": 6,
    }
    # one runbook per incident, from retrieval over the incident summary
    assert data.runbooks["INC-1042"] == "palletiser-kx90-maintenance"
    assert data.runbooks["INC-1039"] == "mes-restart-packing-line"
    assert data.runbooks["INC-1043"] == "label-printer-zebra-troubleshooting"
    assert [r["team"] for r in data.oncall] == ["ot", "infra", "servicedesk"]
    assert all(r["shift"] == "night" for r in data.oncall)
    # the pasted password in INC-1039 is redacted before the model sees it; the kind is kept
    inc_1039 = data.open_incidents[1]
    assert not any("Nordf@rm2026!" in u["text"] for u in inc_1039["updates"])
    assert any("[REDACTED:credential]" in u["text"] for u in inc_1039["updates"])
    assert inc_1039["sensitive"] == ["credential"]


def test_gather_is_live_not_cached():
    assert len(report.gather("night").open_incidents) == 3
    store.post_update("INC-1043", "fixed", status="resolved")
    assert len(report.gather("night").open_incidents) == 2


def test_user_message_carries_template_stats_and_context():
    data = report.gather("day", date="2026-09-11")
    msg = report.user_message(data)
    assert "<template>" in msg and "## 4. On-call for the next shift" in msg
    assert '"open_incidents": 3' in msg
    assert "INC-1042" in msg and "palletiser-kx90-maintenance" in msg
