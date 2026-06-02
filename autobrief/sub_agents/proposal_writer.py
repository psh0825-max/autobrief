"""ProposalWriter: assemble the brief + client-facing proposal (Pro tier for prose quality).

Reads inquiry, research, and the deterministic estimate from session.state and
produces a structured Proposal in session.state['proposal']. It must reuse the
estimate's price band / week range verbatim (a price guardrail enforced downstream).
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import PRO
from ..schemas import Proposal

_INSTRUCTION = """You are the principal of LightOn Plus Lab writing a client proposal.

Inputs (already gathered):
- Client inquiry: {inquiry}
- Research brief: {research}
- Deterministic estimate (AUTHORITATIVE numbers): {estimate}
- Scope summary: {estimate_summary}

Write a warm, credible, concise proposal. Constraints:
- `price_band_usd` MUST be taken verbatim from the estimate's
  price_band_low_usd .. price_band_high_usd (format like "$11,000 - $13,500").
  Never state any other price.
- `timeline_weeks` MUST come from the estimate's week_low/week_high
  (e.g. "3-4 weeks").
- `brief_markdown`: a crisp product brief (problem, target users, proposed MVP
  scope as bullets mapped to the estimate's line items, success metric).
- `proposal_markdown`: the client-facing proposal — opening that restates their
  problem, the proposed approach across the studio's Brief -> Prototype -> Launch
  -> Improve phases, the line-item scope, timeline, the price band, what's
  included (30 days support, full code ownership), and a clear next step (a
  kickoff call).
- `reply_email_subject` and `reply_email_body`: a friendly reply email (the body
  should reference the attached proposal and propose scheduling a kickoff call).
- `summary`: one sentence the founder can skim.
Ground every claim in the inputs; do not invent client facts.
"""

proposal_writer = LlmAgent(
    name="ProposalWriter",
    model=PRO,
    description="Writes the structured brief and client-facing proposal.",
    instruction=_INSTRUCTION,
    output_schema=Proposal,
    output_key="proposal",
)
