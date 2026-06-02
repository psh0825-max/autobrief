"""ADK entrypoint. `adk web` / `adk api_server` discover `root_agent` here.

The root is the **AutoBriefRouter** (autobrief/router.py): a custom orchestrator
that triages the raw inbound inquiry and runs exactly one branch —

  * proceed            -> AutoBriefPipeline (scope + proposal, +delivery if MCP)
  * need_clarification -> ClarifierAgent (draft a few questions)
  * decline            -> DeclineAgent (polite, brief decline)

The triage decision is written to session.state['routing'] by RouterClassifier,
so routing is directly observable (see eval/run_eval.py:_derive_routing).
"""
from __future__ import annotations

from . import config  # noqa: F401  (normalizes env: Vertex vs API key, TLS trust)
from .pipeline import autobrief_pipeline
from .router import AutoBriefRouter
from .sub_agents.clarifier import clarifier_agent
from .sub_agents.decline import decline_agent
from .sub_agents.router_classifier import router_classifier

root_agent = AutoBriefRouter(
    name="AutoBriefRouter",
    router_classifier=router_classifier,
    pipeline=autobrief_pipeline,
    clarifier_agent=clarifier_agent,
    decline_agent=decline_agent,
)
