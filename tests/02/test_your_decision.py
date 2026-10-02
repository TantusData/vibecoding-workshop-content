"""Step 02 — the owner's decision: what the assistant says when it cannot check something.

opscopilot/llm/prompts/chat.md answers every question that needs no NordDesk tool (and, until the
wiki is searchable, every question about procedures). Tomasz's draft says "answer as best you
can" — so the assistant invents procedures with full confidence. What it says instead is the
project owner's decision, written by them; a catch-up never overwrites a chat.md they changed."""

from __future__ import annotations

from pathlib import Path

WS = Path(__file__).resolve().parent.parent.parent
CHAT = Path("opscopilot/llm/prompts/chat.md")


def test_chat_md_is_the_owners_decision_not_tomasz_draft():
    mine = CHAT.read_text(encoding="utf-8").strip()
    draft = (WS / "seed" / CHAT).read_text(encoding="utf-8").strip()
    assert mine, "chat.md is empty"
    assert mine != draft, (
        "chat.md is still Tomasz's draft ('answer as best you can'). What the assistant says when "
        "it cannot check something is the project owner's decision: ask them to write it — do not "
        "write it yourself."
    )
