"""Fixed-input tests for opscopilot.govern.redact — pure functions, exact outputs."""

from __future__ import annotations

import json

from norddesk_mcp import store
from opscopilot.govern.redact import redact, redact_obj

INC_1039_COMMENT = (
    "For whoever picks this up on day shift: the local admin on NF-SRV-MES-01 is "
    "mesadmin / Nordf@rm2026! — I know, I know, will rotate it after. Don't restart during a "
    "running batch."
)


def test_the_pasted_admin_password_is_redacted_and_named_by_kind_only():
    r = redact(INC_1039_COMMENT)
    assert "Nordf@rm2026!" not in r.text
    assert "mesadmin / [REDACTED:credential]" in r.text
    assert r.text.endswith("Don't restart during a running batch.")
    assert [f.model_dump() for f in r.findings] == [{"kind": "credential", "count": 1}]


def test_password_keywords_in_several_spellings():
    for text in (
        "password: hunter22",
        "Password = hunter22",
        "pw hunter22",
        "hasło: hunter22",
        "the pass is hunter22",
    ):
        assert redact(text).text.endswith("[REDACTED:credential]"), text


def test_keys_tokens_pesel_and_badges():
    r = redact("key AKIAIOSFODNN7EXAMPLE, Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123")
    assert r.text == "key [REDACTED:aws-key], Authorization: Bearer [REDACTED:bearer-token]"
    assert redact("PESEL 90010112345 and badge 20477").text == (
        "PESEL [REDACTED:pesel] and badge [REDACTED:badge]"
    )


def test_plain_ops_text_is_untouched():
    for text in (
        "Marek Zieliński, +48 600 100 201, OT on-call tonight.",
        "Restart MES Core Service, then Batch Scheduler; wait ~30 s.",
        "VPN gateway vpn2.nordfarm.example port 443, MFA via Authenticator.",
        "Ticket INC-1042 P1 palletiser-l3 panel P3-07 after the 20-minute cool-down.",
    ):
        r = redact(text)
        assert r.text == text and r.findings == [], text


def test_redaction_is_idempotent():
    once = redact(INC_1039_COMMENT).text
    assert redact(once).text == once
    assert redact(once).findings == []


def test_redact_obj_walks_a_whole_ticket(tmp_path, monkeypatch):
    monkeypatch.setenv("NORDDESK_STORE", str(tmp_path / "s.json"))
    store.init_store(force=True)
    ticket = store.get_ticket("INC-1039")
    clean, findings = redact_obj(ticket)
    assert "Nordf@rm2026!" not in json.dumps(clean, ensure_ascii=False)
    assert clean["id"] == "INC-1039" and clean["updates"][0]["author"] == "Tomasz Lewandowski"
    assert [f.model_dump() for f in findings] == [{"kind": "credential", "count": 1}]
    assert "Nordf@rm2026!" in json.dumps(ticket)  # the input was not mutated
