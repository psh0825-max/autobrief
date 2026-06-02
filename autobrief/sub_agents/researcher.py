"""Researcher: light market/client research via google_search -> session.state['research']."""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from ..config import FLASH

_INSTRUCTION = """You are a research analyst supporting a proposal for an AI MVP studio.

Here is the structured client inquiry:
{inquiry}

Using web search, produce a SHORT research brief (max ~180 words) with:
1. Context on the client/company or their market (only if findable; otherwise say so).
2. 2-3 comparable products or competitors.
3. 1-2 risk flags or technical considerations relevant to scoping the MVP.

Cite every external claim with its source URL inline like [source](url).
Only state facts you found via search; never fabricate. If you cannot find
information, say "No public information found" rather than guessing.
"""

researcher = LlmAgent(
    name="Researcher",
    model=FLASH,
    description="Runs light market/competitor research to inform the proposal.",
    instruction=_INSTRUCTION,
    tools=[google_search],
    output_key="research",
)
