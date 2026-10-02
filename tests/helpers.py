"""Shared test double for agent-level tests since ext-loop: the planner is called repeatedly, so
a plain prompt-keyed fake is not enough. `ScriptedFake` pops a queued ToolPlan for every planner
call, answers scope verdicts, and maps each answer prompt to a canned text (or a callable that
sees the messages). Everything it was handed is recorded in `.calls` / `.seen_messages`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from opscopilot import cli
from opscopilot.govern import scope
from opscopilot.llm import client as llm
from opscopilot.schema import GroundedAnswer, ToolPlan

FINAL = ToolPlan(tool="final", reason="enough")
PROMPTS = {
    name: cli.load_prompt(name)
    for name in ("answer", "answer_tickets", "answer_history", "chat")
    if (cli.PROMPTS_DIR / f"{name}.md").exists()  # a course step may not have all prompts yet
}
SCOPE_PROMPT = (
    scope.PROMPT_PATH.read_text().strip() if scope.PROMPT_PATH.exists() else "<no scope.md yet>"
)
# course step 1 builds route_system(); until then the agent tests are skipped, not collected-out
ROUTE_PREFIX = cli.route_system()[:40] if hasattr(cli, "route_system") else None


def plan(tool: str, **args: Any) -> ToolPlan:
    return ToolPlan(tool=tool, reason="scripted", **args)


class ScriptedFake(llm.FakeLLMClient):
    def __init__(
        self,
        plans: list[ToolPlan] | list[list[ToolPlan]] | None = None,
        answers: dict[str, str | Callable[[list[dict[str, str]]], str]] | None = None,
        in_scope: bool = True,
    ) -> None:
        """`plans` is either one flat list of steps (a single turn) or a list of per-turn lists.
        A planner call that carries no "Gathered so far" block starts the next turn, so the same
        script works whether the app asks the planner once per turn (course step 1) or loops."""
        if ROUTE_PREFIX is None:
            raise RuntimeError(
                "opscopilot.cli.route_system() is missing — agent tests recognise planner calls "
                "by the first 40 characters of the router's system prompt. Define route_system() "
                "(docs/steps/01-tickets.md)."
            )
        super().__init__(responses={})
        plans = list(plans or [])
        self.turns: list[list[ToolPlan]] = (
            [list(t) for t in plans] if plans and isinstance(plans[0], list) else [plans]  # type: ignore[list-item]
        )
        self.turn = -1
        self.answers = dict(answers or {})
        self.in_scope = in_scope
        self.planner_prompts: list[str] = []  # the user turn of every planner call

    @property
    def plans(self) -> list[ToolPlan]:
        return self.turns[self.turn] if 0 <= self.turn < len(self.turns) else []

    def complete(self, system, messages, response_schema=None):
        self.calls.append((system, messages[-1]["content"]))
        self.seen_messages.append(list(messages))
        if system.startswith(ROUTE_PREFIX):
            user = messages[-1]["content"]
            if "Gathered so far in this turn" not in user:
                self.turn += 1
            self.planner_prompts.append(user)
            step = self.plans.pop(0) if self.plans else FINAL
            return llm.LLMResult(step.model_dump_json(), step, 10, 5, 0.00001, "fake", "fake")
        if system == SCOPE_PROMPT:
            v = scope.ScopeVerdict(in_scope=self.in_scope, reason="scripted")
            return llm.LLMResult(v.model_dump_json(), v, 10, 5, 0.00001, "fake", "fake")
        for name, text in self.answers.items():
            if system == PROMPTS.get(name):
                out = text(messages) if callable(text) else text
                parsed = (
                    GroundedAnswer.model_validate_json(out)
                    if response_schema is GroundedAnswer
                    else None
                )
                return llm.LLMResult(out, parsed, 12, 3, 0.0001, "fake", "fake")
        return super().complete(system, messages, response_schema)  # canned via .add(), or raise


def grounded(text: str, citations: list[str] | None = None) -> str:
    return GroundedAnswer(text=text, citations=citations or []).model_dump_json()


def install(monkeypatch, fake: ScriptedFake) -> ScriptedFake:
    monkeypatch.setattr(cli, "get_llm_client", lambda: fake)
    monkeypatch.setattr(scope, "get_llm_client", lambda: fake, raising=False)
    return fake
