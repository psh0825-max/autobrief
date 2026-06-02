"""DeliveryAgent: turns the approved proposal into real artifacts via the Studio MCP server.

Every write action (Drive doc, deck, calendar event, Gmail draft) is gated by
human-in-the-loop confirmation (see mcp_toolsets.studio_write_toolset). The agent
never sends an email — it only ever creates a draft.

Exposed as a factory so the MCP server subprocess is spawned only when delivery
is actually wired in (keeps pipeline-only / eval runs free of MCP).
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import FLASH
from ..tools.mcp_toolsets import studio_toolsets

_INSTRUCTION = """You are the delivery coordinator for LightOn Plus Lab.

The proposal is ready:
- Client inquiry (for the contact email): {inquiry}
- Proposal (authoritative content): {proposal}

Carry out delivery using your tools, IN THIS ORDER. Each client-facing action
requires the founder's approval before it executes — that is expected; just call
the tool and let the approval happen.

1. Call `suggest_kickoff_slot` to get a proposed kickoff datetime.
2. Call `save_to_drive` with the proposal title and the proposal_markdown.
3. Call `generate_proposal_deck` with the title and 4-6 short slide bullets
   summarizing problem, approach, scope, timeline, and price band.
4. Call `create_calendar_event` for a 30-minute tentative kickoff at the
   suggested slot, with the client's contact_email as attendee.
5. Call `create_gmail_draft` to the client's contact_email using the proposal's
   reply_email_subject and reply_email_body. NEVER send — only draft.

After all steps, summarize what was created and what is awaiting the founder's
review. Use the proposal's price band and timeline verbatim; never invent numbers.
"""


def build_delivery_agent() -> LlmAgent:
    return LlmAgent(
        name="DeliveryAgent",
        model=FLASH,
        description="Creates Drive doc, deck, tentative kickoff event, and Gmail draft (all HITL-gated).",
        instruction=_INSTRUCTION,
        tools=studio_toolsets(),
        output_key="delivery_log",
    )
