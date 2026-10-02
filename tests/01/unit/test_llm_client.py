"""Unit tests for opscopilot/llm/client.py — the only tested module so far.

Everything here runs with LLM_PROVIDER=fake or with the gateway call stubbed out; nothing
touches the network.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from opscopilot.llm import client as llm


class Verdict(BaseModel):
    label: str
    confidence: float


SYSTEM = "You are a test system prompt."
USER = "Hello?"


def test_get_llm_client_returns_fake_when_provider_is_fake(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    assert isinstance(llm.get_llm_client(), llm.FakeLLMClient)


def test_fake_client_returns_canned_response_for_known_prompt():
    fake = llm.FakeLLMClient(responses={llm.prompt_key(SYSTEM, USER): "canned reply"})
    result = fake.complete(SYSTEM, [{"role": "user", "content": USER}])
    assert result.text == "canned reply"
    assert result.provider == "fake"
    assert result.cost_usd == 0.0
    assert fake.calls == [(SYSTEM, USER)]


def test_fake_client_raises_unknown_prompt_error_on_miss():
    fake = llm.FakeLLMClient(responses={})
    with pytest.raises(llm.UnknownPromptError):
        fake.complete(SYSTEM, [{"role": "user", "content": "never recorded"}])


def test_cost_is_computed_from_token_usage():
    # 1M input tokens at $3 + 500k output tokens at $15 = $10.50
    assert llm._cost(1_000_000, 500_000) == pytest.approx(10.50)
    assert llm._cost(0, 0) == 0.0


class _StubGateway:
    """Captures chat-completion payloads and replays scripted replies (no network)."""

    def __init__(self, replies: list[str], cost: float | None = None) -> None:
        self.replies = list(replies)
        self.cost = cost
        self.payloads: list[dict] = []

    def __call__(self, payload: dict):
        self.payloads.append(payload)
        body = {
            "choices": [{"message": {"role": "assistant", "content": self.replies.pop(0)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        return body, self.cost


def test_request_carries_the_strict_structured_output_schema(monkeypatch):
    stub = _StubGateway(['{"label": "ok", "confidence": 0.9}'])
    monkeypatch.setattr(llm, "_post_chat", stub)

    result = llm.GatewayLLMClient().complete(
        SYSTEM, [{"role": "user", "content": USER}], response_schema=Verdict
    )

    sent = stub.payloads[0]
    assert sent["model"] == llm.MODEL
    assert sent["messages"] == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
    ]
    fmt = sent["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "Verdict"
    assert fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"] == llm.strict_schema(Verdict.model_json_schema())
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert result.parsed == Verdict(label="ok", confidence=0.9)
    assert (result.input_tokens, result.output_tokens) == (10, 5)
    assert result.cost_usd == pytest.approx(llm._cost(10, 5))


def test_the_gateway_reported_cost_wins_over_the_estimate(monkeypatch):
    monkeypatch.setattr(llm, "_post_chat", _StubGateway(["reply"], cost=0.0123))
    result = llm.GatewayLLMClient().complete(SYSTEM, [{"role": "user", "content": USER}])
    assert result.cost_usd == pytest.approx(0.0123)


def test_well_formed_but_wrong_json_is_retried_exactly_once(monkeypatch):
    # valid JSON, wrong shape: the schema check, not the JSON parser, is what catches it
    stub = _StubGateway(['{"label": "ok"}', '{"label": "ok", "confidence": 0.5}'])
    monkeypatch.setattr(llm, "_post_chat", stub)

    result = llm.GatewayLLMClient().complete(
        SYSTEM, [{"role": "user", "content": USER}], response_schema=Verdict
    )

    assert len(stub.payloads) == 2
    retry_text = stub.payloads[1]["messages"][-1]["content"]
    assert "not valid for the required schema" in retry_text
    assert result.parsed == Verdict(label="ok", confidence=0.5)
    assert result.input_tokens == 20  # both attempts are billed


def test_a_second_invalid_reply_raises_instead_of_guessing(monkeypatch):
    stub = _StubGateway(["not json at all", '{"label": 3}'])
    monkeypatch.setattr(llm, "_post_chat", stub)
    with pytest.raises(ValidationError):
        llm.GatewayLLMClient().complete(
            SYSTEM, [{"role": "user", "content": USER}], response_schema=Verdict
        )
    assert len(stub.payloads) == 2  # one retry, no more


def test_prior_turns_are_sent_as_conversation_history(monkeypatch):
    stub = _StubGateway(["reply"])
    monkeypatch.setattr(llm, "_post_chat", stub)
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer one"},
        {"role": "user", "content": "second"},
    ]
    llm.GatewayLLMClient().complete(SYSTEM, history)
    assert stub.payloads[0]["messages"] == [
        {"role": "system", "content": SYSTEM},
        *history,
    ]


def test_a_missing_key_fails_loudly_before_any_request(monkeypatch):
    monkeypatch.setattr(llm.settings, "litellm_virtual_key", "")
    with pytest.raises(RuntimeError, match="LITELLM_VIRTUAL_KEY"):
        llm._post_chat({"model": "x", "messages": []})
