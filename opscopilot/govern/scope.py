"""opscopilot/govern/scope.py — is this something OpsCopilot should answer at all?

Purpose:      Rules first, model second: deny patterns (policy circumvention, credentials,
              restricted/personal data, safety overrides) and allow patterns (our systems,
              ticket ids, ops vocabulary) decide most requests without a model call; only the
              ambiguous remainder goes to a structured classification with `scope.md`.
              Same rules -> LLM -> both progression as the rest of the app.
Entry points: classify(question, prior) -> ScopeDecision, rules(question) -> ScopeDecision | None,
              REFUSAL (the fixed reply), ScopeDecision
Depends on:   re (stdlib), pydantic, opscopilot.llm.client, opscopilot/llm/prompts/scope.md
Used by:      opscopilot.cli (first step of ask), scripts/eval_guardrails.py
Invariants:   A deny rule beats an allow rule. rules() never calls the model. The refusal text
              is one fixed string so tests and the gold set can match it exactly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from opscopilot.llm.client import get_llm_client

PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "scope.md"

REFUSAL = (
    "I can only help with Nordfarm Foods IT/OT operations — tickets, our systems and our "
    "documented procedures — and I can't help route around a policy or share restricted data."
)

_TICKET = r"(?:INC|REQ|CHG|Q)-\d{3,5}"
_ALL_TICKETS = r"\b(?:all|every)\s+(?:open\s+)?tickets?\b"
_SEND = r"\b(?:e-?mail|send|forward|export)\b"
# Polish: the plant staff type Polish, so every rule has a Polish twin (stems, not words —
# Polish inflects: "zgłoszenie / zgłoszenia / zgłoszeń").
_PL_TICKETS = r"\b(?:wszystkie|każde)\s+(?:otwarte\s+)?zgłosze\w*"
_PL_SEND = r"\b(?:wyślij|prześlij|wysłać|przesłać|wyeksportuj|mailem|e-?mailem)\b"

DENY: list[tuple[str, re.Pattern[str]]] = [
    (
        "override",
        re.compile(
            r"(?i)\bignore\s+(?:all\s+|any\s+)?(?:your|the|previous|prior|above)\s+\w*\s*"
            r"instructions?\b"
            r"|\bzignoruj\w*\s+(?:\w+\s+){0,2}(?:instrukcj\w*|polece\w*|zasad\w*)"
        ),
    ),
    (
        "exfiltration",
        re.compile(
            rf"(?i){_SEND}.{{0,60}}{_ALL_TICKETS}|{_ALL_TICKETS}.{{0,60}}{_SEND}"
            rf"|{_PL_SEND}.{{0,60}}{_PL_TICKETS}|{_PL_TICKETS}.{{0,60}}{_PL_SEND}"
        ),
    ),
    (
        "credential-request",
        re.compile(
            r"(?i)\b(?:give|tell|send|show)\b.{0,40}\b(?:password|passwd|credentials?|admin pw)\b"
            rf"|\bpassword\b.{{0,30}}\b(?:that is|from|in)\s+{_TICKET}"
            r"|\b(?:daj|dajcie|podaj|pokaż|wyślij|powiedz|zdradź|dostać|dostanę)\b.{0,40}"
            r"\b(?:has[łl]\w*|dan\w* logowania)"
            rf"|\bhas[łl]\w*.{{0,30}}\b(?:z|ze|w|we)\s+{_TICKET}"
        ),
    ),
    (
        "policy-bypass",
        re.compile(
            r"(?i)\b(?:get around|bypass|circumvent|skip|disable|turn off|work around)\b.{0,60}"
            r"\b(?:2fa|mfa|two[- ]factor|authenticator|approval|lockout|light curtain|safety|"
            r"interlock|guard)\b"
            r"|\b(?:obej\w*|obchodz\w*|omin\w*|wyłącz\w*|pomi\w*|dezaktyw\w*)\b.{0,60}"
            r"\b(?:2fa|mfa|dwuskładnik\w*|uwierzytelni\w*|zatwierdz\w*|blokad\w*|kurtyn\w*|"
            r"zabezpiecze\w*|osłon\w*|bezpieczeństw\w*)"
        ),
    ),
    (
        "restricted-data",
        re.compile(
            r"(?i)\b(?:salary|salaries|pay band|payroll|compensation)\b"
            r"|\b(?:wynagrodze\w*|pensj\w*|zarobk\w*|ile zarabia\w*|siatk\w* płac|widełk\w*)"
        ),
    ),
    (
        "personal-data",
        re.compile(
            r"(?i)\b(?:home address|private (?:phone|number|address)|date of birth|pesel)\b"
            r"|\badres\w* domow\w*|\bprywatn\w* (?:telefon\w*|numer\w*|adres\w*)"
            r"|\bdat\w* urodzenia"
        ),
    ),
]

ALLOW: list[tuple[str, re.Pattern[str]]] = [
    ("ticket-id", re.compile(rf"\b{_TICKET}\b")),
    (
        "our-systems",
        re.compile(
            r"(?i)\b(?:norddesk|nordwiki|mes|palletis[eo]r|kx-?90|scada|erp|dynamics|vpn|"
            r"forticlient|zebra|label printer|printer|wi-?fi|wireless|cold store|line [123]|"
            r"hmi|plc)\b"
            r"|\b(?:drukark\w*|paletyzator\w*|chłodni\w*|lini[aięi]\s*[123])"
        ),
    ),
    (
        "ops-vocabulary",
        re.compile(
            r"(?i)\b(?:ticket|incident|outage|restart|reboot|backup|restore|runbook|sop|procedure|"
            r"lockout|fault|error|on[- ]call|handover|shift|servicedesk|service desk|"
            r"password reset|access request|change request)\b"
            r"|\b(?:zgłosze\w*|incydent\w*|awari\w*|usterk\w*|z?restartow\w*|restart\w*|"
            r"kopi\w* zapasow\w*|backup\w*|odtworz\w*|odtwórz|przywróc\w*|procedur\w*|"
            r"dyżur\w*|przekazani\w* zmiany|raport\w* ze? zmiany|z?resetow\w* has[łl]\w*|"
            r"wniosek o dostęp)"
        ),
    ),
]


class ScopeDecision(BaseModel):
    allowed: bool
    reason: str
    method: Literal["rule-deny", "rule-allow", "llm"]


class ScopeVerdict(BaseModel):
    in_scope: bool
    reason: str


def rules(question: str) -> ScopeDecision | None:
    """Deny beats allow; None means the rules could not decide."""
    for name, pattern in DENY:
        if pattern.search(question):
            return ScopeDecision(allowed=False, reason=name, method="rule-deny")
    for name, pattern in ALLOW:
        if pattern.search(question):
            return ScopeDecision(allowed=True, reason=name, method="rule-allow")
    return None


def classify(question: str, prior: list[dict[str, str]] | None = None) -> ScopeDecision:
    """Rules on the current message, then the model — with the conversation so far, if any —
    for whatever the rules left undecided (a follow-up like "and who is on it?" has no keyword)."""
    decided = rules(question)
    if decided is not None:
        return decided
    system = PROMPT_PATH.read_text(encoding="utf-8").strip()
    messages = [*(prior or []), {"role": "user", "content": question}]
    result = get_llm_client().complete(system, messages, ScopeVerdict)
    assert isinstance(result.parsed, ScopeVerdict)
    return ScopeDecision(allowed=result.parsed.in_scope, reason=result.parsed.reason, method="llm")
