"""Shared pydantic contracts passed between AutoBrief sub-agents via session.state.

These are the single source of truth that every sub-agent codes against.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RoutingDecision(str, Enum):
    """Router's top-level decision for an inbound inquiry."""

    proceed = "proceed"                 # enough info -> run the full pipeline
    need_clarification = "need_clarification"  # missing info -> draft questions
    decline = "decline"                 # out of scope / not a fit -> polite no


class ProjectArchetype(str, Enum):
    """Fixed catalogue of project shapes the studio delivers in 2-6 weeks."""

    landing_waitlist = "landing+waitlist"
    crud_saas_mvp = "crud-saas-mvp"
    ai_chat_assistant = "ai-chat-assistant"
    data_dashboard = "data-dashboard"
    mobile_companion = "mobile-companion"
    integration_glue = "integration-glue"


class RouterVerdict(BaseModel):
    """AutoBriefRouter's triage decision for one inbound inquiry."""

    decision: RoutingDecision
    reason: str = Field(
        description="One concise sentence explaining the routing decision."
    )


class ClientInquiry(BaseModel):
    """Structured form extracted from a raw inbound inquiry email."""

    company: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    problem: str = Field(description="The core problem the client wants solved.")
    target_users: Optional[str] = None
    platform: Optional[str] = Field(default=None, description="web | mobile | both")
    budget_signal: Optional[str] = None
    deadline: Optional[str] = None
    must_have_features: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Names of important fields that were absent from the email.",
    )
    raw_excerpt: Optional[str] = None


class ScopeClassification(BaseModel):
    """LLM-only output of ScoperEstimator: classification, never raw prices."""

    archetype: ProjectArchetype
    feature_keys: list[str] = Field(
        default_factory=list,
        description="Keys from rubric.yaml feature_addons that this project needs.",
    )
    complexity: float = Field(ge=1.0, le=1.6, description="Complexity multiplier 1.0-1.6.")
    rush: bool = False
    justification: str = ""


class LineItem(BaseModel):
    key: str
    label: str
    days: float
    price_usd: float


class ScopeEstimate(BaseModel):
    """Deterministic output of estimate_scope(). All numbers trace to the rubric."""

    archetype: str
    currency: str = "KRW"            # display currency (selectable: KRW | USD)
    currency_symbol: str = "₩"
    price_band: str = ""             # preformatted band, ready to quote verbatim
    line_items: list[LineItem] = Field(default_factory=list)
    base_days: float = 0.0
    total_days: float = 0.0
    week_low: int = 2
    week_high: int = 6
    subtotal_usd: float = 0.0
    complexity: float = 1.0
    rush_multiplier: float = 1.0
    contingency_pct: float = 0.0
    total_price_usd: float = 0.0
    price_band_low_usd: int = 0
    price_band_high_usd: int = 0
    confidence: float = 0.0
    notes: list[str] = Field(default_factory=list)


class Proposal(BaseModel):
    """Final assembled proposal authored by ProposalWriter."""

    title: str
    summary: str
    brief_markdown: str
    proposal_markdown: str
    price_band_usd: str          # quoting-currency band, verbatim from the estimate
    timeline_weeks: str          # e.g. "3-4 weeks"
    deck_url: Optional[str] = None
    reply_email_subject: Optional[str] = None
    reply_email_body: Optional[str] = None
