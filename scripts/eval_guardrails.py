"""scripts/eval_guardrails.py — grade the scope guardrail against data/eval/guardrail_gold.jsonl.

Purpose:      `python scripts/eval_guardrails.py`. For every gold prompt, run `scope.classify()`
              (rules first, the model for the undecided) and compare with `should_refuse`. Also
              reports how many were decided by rules alone — the "rules baseline before reaching for
              the LLM" lesson. With LLM_PROVIDER=fake only the rule-decided prompts are graded (the
              rest are reported as SKIP) so the script is runnable offline.
Entry points: main()
Depends on:   opscopilot.govern.scope
Used by:      Makefile `eval`
Invariants:   Never calls ask(); grades the guardrail, not the answer. Exits 1 on any FAIL.
"""

from __future__ import annotations

import sys
from pathlib import Path

# run as `python scripts/<name>.py` from the project folder, with nothing installed: make the
# project importable (under uv it already is; this line then changes nothing)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent / "data" / "eval" / "guardrail_gold.jsonl"


def main() -> int:
    from opscopilot.govern import scope

    items = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line]
    offline = os.environ.get("LLM_PROVIDER", "litellm").lower() == "fake"
    passed = failed = skipped = by_rule = 0
    print(f"{'id':28s} {'expect':8s} {'got':8s} {'via':11s} result")
    for item in items:
        expect = "refuse" if item["should_refuse"] else "allow"
        decision = scope.rules(item["prompt"])
        if decision is None:
            if offline:
                skipped += 1
                print(f"{item['id']:28s} {expect:8s} {'-':8s} {'llm':11s} SKIP (fake provider)")
                continue
            decision = scope.classify(item["prompt"])
        else:
            by_rule += 1
        got = "allow" if decision.allowed else "refuse"
        ok = got == expect
        passed += ok
        failed += not ok
        verdict = "PASS" if ok else "FAIL"
        print(f"{item['id']:28s} {expect:8s} {got:8s} {decision.method:11s} {verdict}")
    graded = passed + failed
    print(
        f"\nguardrails: {passed}/{graded} passed, {by_rule}/{len(items)} decided by rules, "
        f"{skipped} skipped"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
