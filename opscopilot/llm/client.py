"""opscopilot/llm/client.py — the one door to the language model (the gateway) and its test double.

Purpose:      Wraps the company's LiteLLM gateway (OpenAI-compatible `/chat/completions`, model
              alias `bedrock-claude`, structured output via `response_format: json_schema`,
              strict) behind a tiny `LLMClient` protocol, and provides a deterministic
              `FakeLLMClient` keyed by prompt hash so nothing in `pytest` ever calls a real model.
              This is the part of the prototype that is finished and tested — build on it.
Entry points: get_llm_client(), LLMClient.complete(), GatewayLLMClient, FakeLLMClient,
              LLMResult, UnknownPromptError, prompt_key(), strict_schema(), _post_chat()
Depends on:   httpx, pydantic, opscopilot.config
Used by:      opscopilot.cli (ask), opscopilot.webapp.app (via cli.ask)
Invariants:   LLM_PROVIDER=fake never opens a network connection. A missing canned response
              raises UnknownPromptError (never a silent fallback). Every model reply is treated
              as untrusted input: structured output is validated against the pydantic model and
              retried exactly once on validation failure — well-formed JSON is not the same as
              correct JSON. Prior user/assistant turns in `messages` are sent as conversation
              history; the fake keys on (system, last user message) only. The virtual key is
              read from the environment and never logged or written to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from opscopilot.config import settings

# --------------------------------------------------------------------------------------------
# Gateway adapter. Every model call in this app goes through LiteLLM with the user's
# own virtual key, so spend is attributed to them. The base URL and the key come from the
# environment (LITELLM_BASE_URL, LITELLM_VIRTUAL_KEY); the model is an alias the key allows.
# --------------------------------------------------------------------------------------------

MODEL = settings.llm_model
# Sonnet 4.5 list price, USD per million tokens — used only when the gateway does not report
# the call's cost itself (LiteLLM sends it in the `x-litellm-response-cost` header).
INPUT_COST_PER_MTOK = 3.00
OUTPUT_COST_PER_MTOK = 15.00


def _cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * INPUT_COST_PER_MTOK + output_tokens * OUTPUT_COST_PER_MTOK) / 1_000_000


def _post_chat(payload: dict) -> tuple[dict, float | None]:
    """POST one chat completion to the gateway. Returns (response JSON, reported cost or None)."""
    import httpx

    key = settings.litellm_virtual_key
    if not key:
        raise RuntimeError("LITELLM_VIRTUAL_KEY is not set — the model gateway needs it")
    response = httpx.post(
        settings.litellm_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    reported = response.headers.get("x-litellm-response-cost")
    return response.json(), (float(reported) if reported else None)


def _call_model(
    system: str,
    messages: list[dict],
    *,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    json_schema: dict | None = None,
) -> tuple[str, int, int, float | None]:
    """Returns (reply_text, input_tokens, output_tokens, reported_cost_or_None).
    `messages` = [{"role": "user"|"assistant", "content": str}, ...];
    json_schema = {"name": str, "schema": <JSON-Schema dict>} -> structured output (strict)."""
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": json_schema["name"],
                "schema": json_schema["schema"],
                "strict": True,
            },
        }
    data, reported = _post_chat(payload)
    reply = (data["choices"][0]["message"].get("content") or "").strip()
    usage = data.get("usage") or {}
    return reply, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), reported


# --------------------------------------------------------------------------------------------
# The protocol the rest of the app talks to
# --------------------------------------------------------------------------------------------

Message = dict[str, str]  # {"role": "user" | "assistant", "content": str}


class UnknownPromptError(KeyError):
    """FakeLLMClient has no canned response for this (system, last user message) pair."""


@dataclass
class LLMResult:
    """What every `complete()` returns, regardless of provider."""

    text: str
    parsed: BaseModel | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model: str
    provider: str


class LLMClient(Protocol):
    def complete(
        self,
        system: str,
        messages: list[Message],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResult: ...


def prompt_key(system: str, last_user: str) -> str:
    """The key the fake client (and the recorder) index canned responses by."""
    return hashlib.sha256((system + "\n" + last_user).encode("utf-8")).hexdigest()


def _last_user(messages: list[Message]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m["content"]
    raise ValueError("messages must contain at least one user message")


def strict_schema(schema: dict) -> dict:
    """Strict structured output rejects any object without `additionalProperties: false`."""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "additionalProperties" not in node:
                node["additionalProperties"] = False
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    out = json.loads(json.dumps(schema))
    walk(out)
    return out


def _parse(text: str, response_schema: type[BaseModel] | None) -> BaseModel | None:
    if response_schema is None:
        return None
    return response_schema.model_validate_json(text)


class GatewayLLMClient:
    """The real thing. One retry on structured-output validation failure, cost per call."""

    provider = "litellm"

    def __init__(self, *, temperature: float | None = None, max_tokens: int | None = None) -> None:
        self.temperature = settings.llm_temperature if temperature is None else temperature
        self.max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    def complete(
        self,
        system: str,
        messages: list[Message],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResult:
        user = _last_user(messages)
        json_schema = None
        if response_schema is not None:
            json_schema = {
                "name": response_schema.__name__,
                "schema": strict_schema(response_schema.model_json_schema()),
            }

        total_in = total_out = 0
        total_cost = 0.0
        attempt_user = user
        last_error: ValidationError | None = None
        prior = [m for m in messages[:-1] if m.get("role") in ("user", "assistant")]
        for _attempt in range(2):  # one retry, no more
            text, n_in, n_out, reported = _call_model(
                system,
                [*prior, {"role": "user", "content": attempt_user}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                json_schema=json_schema,
            )
            total_in += n_in
            total_out += n_out
            total_cost += reported if reported is not None else _cost(n_in, n_out)
            try:
                parsed = _parse(text, response_schema)
            except ValidationError as err:
                last_error = err
                attempt_user = (
                    f"{user}\n\nYour previous reply was not valid for the required schema:\n"
                    f"{err}\nReply again with JSON that matches the schema exactly."
                )
                continue
            _maybe_record(system, user, text)
            return LLMResult(
                text=text,
                parsed=parsed,
                input_tokens=total_in,
                output_tokens=total_out,
                cost_usd=total_cost,
                model=MODEL,
                provider=self.provider,
            )
        assert last_error is not None
        raise last_error


class FakeLLMClient:
    """Deterministic double: prompt hash -> canned text. Raises on a miss, never guesses.

    Responses come from an in-memory dict and/or a JSON file (`FAKE_LLM_RESPONSES`, default
    `tests/fixtures/llm_responses.json`) shaped `{<sha256>: {"note": str, "text": str}}`.
    Record real replies into that file with `RECORD=1 LLM_PROVIDER=litellm`.
    """

    provider = "fake"

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        path: str | Path | None = None,
    ) -> None:
        self._responses: dict[str, str] = dict(responses or {})
        self.path = Path(path) if path is not None else Path(settings.fake_llm_responses)
        if self.path.exists():
            for key, entry in json.loads(self.path.read_text(encoding="utf-8")).items():
                self._responses.setdefault(key, entry["text"] if isinstance(entry, dict) else entry)
        self.calls: list[tuple[str, str]] = []
        self.seen_messages: list[list[Message]] = []  # full message lists, for history tests

    def add(self, system: str, user: str, text: str) -> None:
        self._responses[prompt_key(system, user)] = text

    def complete(
        self,
        system: str,
        messages: list[Message],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResult:
        user = _last_user(messages)
        key = prompt_key(system, user)
        self.calls.append((system, user))
        self.seen_messages.append(list(messages))
        if key not in self._responses:
            raise UnknownPromptError(
                f"no canned response for prompt {key[:12]}… "
                f"(system starts {system[:40]!r}, user starts {user[:40]!r}). "
                "Record one with RECORD=1 LLM_PROVIDER=litellm or add it via FakeLLMClient.add()."
            )
        text = self._responses[key]
        return LLMResult(
            text=text,
            parsed=_parse(text, response_schema),
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            model="fake",
            provider=self.provider,
        )


def _maybe_record(system: str, user: str, text: str) -> None:
    """RECORD=1: append the real reply to the fake client's fixture file (seeds future tests)."""
    if not settings.record:
        return
    path = Path(settings.fake_llm_responses)
    data: dict[str, Any] = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data[prompt_key(system, user)] = {"note": user[:80], "text": text}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_llm_client() -> LLMClient:
    """Provider factory. `LLM_PROVIDER=fake` -> FakeLLMClient (no network); else -> the gateway."""
    provider = os.environ.get("LLM_PROVIDER", settings.llm_provider).lower()
    if provider == "fake":
        return FakeLLMClient()
    return GatewayLLMClient()
