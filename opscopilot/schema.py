"""opscopilot/schema.py — the shared pydantic v2 data models (contract-first).

Purpose:      Every module speaks these types: incoming requests, triaged tickets, incident rows
              for the impact model, impact estimates and grounded answers. Agreed with the
              servicedesk before any pipeline code existed; treat field changes as API changes.
Entry points: Request, Ticket, Incident, ImpactEstimate, Answer, GroundedAnswer, ToolPlan
Depends on:   pydantic
Used by:      opscopilot.cli (ToolPlan, GroundedAnswer as structured outputs; Answer); llm.client
Invariants:   Ticket.summary <= 200 chars; datetimes are tz-aware (Europe/Warsaw).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Channel = Literal["email", "portal", "phone", "chat"]
TicketType = Literal["incident", "access_request", "change_request", "question", "vendor", "other"]
Urgency = Literal["P1", "P2", "P3", "P4"]
Team = Literal["infra", "apps", "servicedesk", "ot", "security", "unassigned"]
Sensitivity = Literal["public", "internal", "confidential", "restricted"]


class Request(BaseModel):
    """A raw support request as it arrives, before triage."""

    id: str
    channel: Channel
    received_at: datetime  # tz-aware, Europe/Warsaw
    raw_text: str
    language: Literal["en", "pl", "other"]
    reporter_name: str | None = None
    reporter_badge: str | None = None


class Ticket(BaseModel):
    """The triage result for one Request — what gets written to NordDesk."""

    request_id: str
    type: TicketType
    system: str | None = None  # free text, normalised against the NordDesk seed "systems"
    urgency: Urgency
    team: Team
    summary: str = Field(max_length=200)
    sla_business_hours: int
    sla_breach_at: datetime | None = None
    needs_human_review: bool
    evidence: list[str] = []


class Incident(BaseModel):
    """One historical production incident — the feature row for the impact model."""

    line: Literal["L1", "L2", "L3"]
    shift: Literal["day", "night"]
    category: Literal["mechanical", "electrical", "software", "material", "other"]
    machine_age_years: float
    part_cost_eur: float
    crew_size: int
    time_of_day_hours: int
    historical_mtbf_days: float


class ImpactEstimate(BaseModel):
    """What the impact model returns for an incident."""

    downtime_min: float
    eur_impact: float
    orders_at_risk: int
    drivers: list[tuple[str, float]]


class GroundedAnswer(BaseModel):
    """What the model returns for a doc-grounded question (structured output)."""

    text: str
    citations: list[str] = []


class Answer(BaseModel):
    """A (possibly grounded) answer to an operator question."""

    text: str
    citations: list[str]
    grounded: bool
    retrieved_chunk_ids: list[str]

    def render(self) -> str:
        """CLI/web form: the text plus a Sources line when something was cited."""
        if not self.citations:
            return self.text
        return f"{self.text}\n\nSources: {', '.join(self.citations)}"


ToolName = Literal[
    "get_ticket",
    "search_tickets",
    "get_system_status",
    "get_oncall",
    "create_ticket",
    "post_update",
    "impact_estimate",
    "search_docs",
    "final",
]


class ToolPlan(BaseModel):
    """One planning step of the tool loop: which tool to call next and its arguments, or `final`
    (enough information gathered — or none needed — go and answer).

    Flat optional fields instead of a free-form dict so native Structured Outputs can enforce it.
    Before ext-loop this was the one-shot router's decision (`none` = wiki retrieval,
    `from_history` = answer from the conversation); both are now `search_docs` / `final`.
    """

    tool: ToolName
    reason: str
    ticket_id: str | None = None
    query: str | None = None
    status: str | None = None
    system: str | None = None
    summary: str | None = None
    description: str | None = None
    text: str | None = None
    shift: str | None = None
    type: TicketType | None = None
    urgency: Urgency | None = None

    def args(self) -> dict:
        """Only the arguments the chosen tool accepts, without the Nones."""
        accepted = {
            "get_ticket": ("ticket_id",),
            "search_tickets": ("query", "status", "system"),
            "get_system_status": ("system",),
            "create_ticket": ("summary", "description", "type", "urgency", "system"),
            "post_update": ("ticket_id", "text", "status"),
            "impact_estimate": ("ticket_id",),
            "search_docs": ("query",),
            "get_oncall": ("shift",),
            "final": (),
        }[self.tool]
        return {k: getattr(self, k) for k in accepted if getattr(self, k) is not None}
