"""scripts/eval_rag.py — grade retrieval (and optionally answers) against data/eval/rag_gold.jsonl.

Purpose:      `python scripts/eval_rag.py`. Retrieval grading needs no model call: for every gold
              question the expected page must appear in the top-k chunks and every `must_include`
              string must occur in the retrieved text. With EVAL_ANSWERS=1 (and a real LLM_PROVIDER)
              it also runs the full `ask()` path and checks must_include / the exact refusal string
              in the answer. Exits 1 if any retrieval check fails, so it can gate CI.
Entry points: main(), grade_retrieval(item), grade_answer(item)
Depends on:   opscopilot.rag.retrieve, opscopilot.cli (answer grading only)
Used by:      Makefile `eval`
Invariants:   Never called from the tests; uses whatever EMBEDDINGS_BACKEND is set (real by
              default). Matching is case-insensitive.
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

GOLD = Path(__file__).resolve().parent.parent / "data" / "eval" / "rag_gold.jsonl"
K = 4


def load_gold() -> list[dict]:
    return [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line]


def grade_retrieval(item: dict) -> tuple[bool, str]:
    from opscopilot.rag.retrieve import retrieve

    chunks = retrieve(item["question"], k=K)
    pages = [c.page_id for c in chunks]
    text = " ".join(c.text for c in chunks).lower()
    if item.get("must_refuse"):
        return True, f"top={pages[0] if pages else '-'} score={chunks[0].score:.2f} (n/a)"
    hit = item["expected_doc"] in pages
    missing = [s for s in item.get("must_include", []) if s.lower() not in text]
    ok = hit and not missing
    note = f"top={pages[0]} score={chunks[0].score:.2f}"
    if not hit:
        note += " EXPECTED DOC NOT IN TOP-K"
    if missing:
        note += f" MISSING {missing}"
    return ok, note


def grade_answer(item: dict) -> tuple[bool, str]:
    from opscopilot.cli import NOT_FOUND, answer_from_docs

    answer = answer_from_docs(item["question"])
    if item.get("must_refuse"):
        ok = answer.text == NOT_FOUND
        return ok, "refused" if ok else f"ANSWERED: {answer.text[:60]!r}"
    low = answer.text.lower()
    missing = [s for s in item.get("must_include", []) if s.lower() not in low]
    ok = not missing and answer.grounded
    note = f"cited={len(answer.citations)}"
    if missing:
        note += f" MISSING {missing}"
    if not answer.grounded:
        note += " NOT GROUNDED"
    return ok, note


def main() -> int:
    gold = load_gold()
    with_answers = os.environ.get("EVAL_ANSWERS") == "1"
    if with_answers and os.environ.get("LLM_PROVIDER", "litellm").lower() == "fake":
        print("EVAL_ANSWERS=1 needs a real LLM_PROVIDER", file=sys.stderr)
        return 2
    r_pass = a_pass = 0
    print(f"{'id':22s} {'retrieval':10s} {'answer':10s} notes")
    for item in gold:
        r_ok, r_note = grade_retrieval(item)
        r_pass += r_ok
        a_str, a_note = "-", ""
        if with_answers:
            a_ok, a_note = grade_answer(item)
            a_pass += a_ok
            a_str = "PASS" if a_ok else "FAIL"
        print(f"{item['id']:22s} {'PASS' if r_ok else 'FAIL':10s} {a_str:10s} {r_note} {a_note}")
    summary = f"\nretrieval: {r_pass}/{len(gold)}"
    if with_answers:
        summary += f"   answers: {a_pass}/{len(gold)}"
    print(summary)
    return 0 if r_pass == len(gold) and (not with_answers or a_pass == len(gold)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
