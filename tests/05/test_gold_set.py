"""Step 05 — the guardrail gold set: a decision, written down as data, before any guardrail code.

`data/eval/guardrail_gold.jsonl` — one JSON object per line. Step 06's tests read this file and
expect, per category, a specific KIND of decision (see specs/05/spec.md), so the categories and
the refuse/allow verdicts must agree with that table. These tests check the shape and the
coverage of the set, never whether the model agrees with it."""

from __future__ import annotations

import json
from pathlib import Path

GOLD = Path("data/eval/guardrail_gold.jsonl")
ALLOW = {
    "ticket",
    "ticket-write",
    "system-status",
    "ops-howto",
    "ops-procedure",
    "ops-ambiguous",
    "handover",
}
REFUSE_BY_RULE = {"policy-circumvention", "injection", "restricted-data", "personal-data"}
REFUSE_BY_MODEL = {"off-topic"}


def rows() -> list[dict]:
    lines = [ln for ln in GOLD.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for i, line in enumerate(lines, 1):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as err:
            raise AssertionError(f"line {i} is not valid JSON: {err}") from None
    return out


def test_the_set_has_fifteen_to_thirty_lines():
    n = len(rows())
    assert 15 <= n <= 30, f"{n} lines — the room writes 15–20"


def test_every_line_has_the_four_fields_and_a_unique_id():
    seen = set()
    for r in rows():
        assert isinstance(r.get("id"), str) and r["id"], r
        assert isinstance(r.get("prompt"), str) and r["prompt"].strip(), r
        assert isinstance(r.get("should_refuse"), bool), f"{r['id']}: should_refuse true/false"
        assert r["id"] not in seen, f"duplicate id {r['id']}"
        seen.add(r["id"])


def test_categories_come_from_the_table_and_agree_with_the_verdict():
    for r in rows():
        cat = r.get("category")
        assert cat in ALLOW | REFUSE_BY_RULE | REFUSE_BY_MODEL, f"{r['id']}: category {cat!r}"
        expected = cat not in ALLOW
        assert r["should_refuse"] is expected, (
            f"{r['id']}: category {cat} means should_refuse={expected}"
        )


def test_the_set_covers_what_step_06_must_handle():
    cats = [r["category"] for r in rows()]
    assert sum(c in ALLOW for c in cats) >= 5, "at least 5 normal ops questions that must pass"
    for needed in ("policy-circumvention", "off-topic", "injection"):
        assert needed in cats, f"no '{needed}' example"
    assert {"restricted-data", "personal-data"} & set(cats), "no restricted or personal data ask"
    assert "ticket-write" in cats, "no write request (e.g. 'add a comment to INC-1042')"
