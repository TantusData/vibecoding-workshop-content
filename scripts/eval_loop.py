"""scripts/eval_loop.py — grade the tool loop against data/eval/loop_gold.jsonl (real model).

Purpose:      `python scripts/eval_loop.py`. For each question: run ask_traced() statelessly,
              collect the tools the loop actually called (from the turn's audit events), and check
              that every `expected_tools` entry was called, that no more than `max_tools` (default
              5) were, and that the answer contains each `must_include` string. Prints the tool
              sequence and cost per question so the planner's behaviour is visible, not inferred.
Entry points: main()
Depends on:   opscopilot.cli.ask_traced, norddesk_mcp.store (seeded per run)
Used by:      Makefile `eval-loop`
Invariants:   Never part of the tests; refuses LLM_PROVIDER=fake. Store re-seeded first.
"""

from __future__ import annotations

import sys
from pathlib import Path

# run as `python scripts/<name>.py` from the project folder, with nothing installed: make the
# project importable (under uv it already is; this line then changes nothing)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import os
import sys
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent / "data" / "eval" / "loop_gold.jsonl"


def main() -> int:
    if os.environ.get("LLM_PROVIDER", "litellm").lower() == "fake":
        print("eval-loop needs a real LLM_PROVIDER", file=sys.stderr)
        return 2
    from norddesk_mcp import store
    from opscopilot.cli import ask_traced

    store.init_store(force=True)
    items = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line]
    passed = 0
    print(f"{'id':26s} {'result':7s} tools called · cost · notes")
    for item in items:
        answer, _, events = ask_traced(item["question"])
        tools = [e["tool"] for e in events if e["kind"] == "tool_call"]
        cost = sum(e.get("cost_usd", 0.0) for e in events)
        low = answer.lower()
        problems = []
        for t in item["expected_tools"]:
            if t not in tools:
                problems.append(f"missing {t}")
        if len(tools) > item.get("max_tools", 5):
            problems.append(f"{len(tools)} tools > max")
        for s in item.get("must_include", []):
            if s.lower() not in low:
                problems.append(f"answer lacks {s!r}")
        ok = not problems
        passed += ok
        verdict = "PASS" if ok else "FAIL"
        print(f"{item['id']:26s} {verdict:7s} {tools} · ${cost:.4f} · {'; '.join(problems)}")
    print(f"\nloop: {passed}/{len(items)}")
    return 0 if passed == len(items) else 1


if __name__ == "__main__":
    raise SystemExit(main())
