"""AutoBriefPipeline: the deterministic intake -> research -> scope -> proposal spine.

SequentialAgent is deprecated in ADK 2.1.0 but still functional; we use it here for
a reproducible demo flow. State flows implicitly between sub-agents via output_key.
"""
from __future__ import annotations

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from google.adk.agents import SequentialAgent

from .config import ENABLE_MCP
from .sub_agents.intake_parser import intake_parser
from .sub_agents.proposal_writer import proposal_writer
from .sub_agents.researcher import researcher
from .sub_agents.scoper_estimator import scoper_estimator

# Core reasoning spine: intake -> research -> scope/estimate -> proposal.
_pipeline_stages = [intake_parser, researcher, scoper_estimator, proposal_writer]

# Delivery is appended only when MCP is enabled (interactive / deployed runs).
# It calls HITL-gated tools that pause for human approval, which would stall a
# headless eval run, so the eval path (ENABLE_MCP off) stops at the proposal.
if ENABLE_MCP:
    from .sub_agents.delivery_agent import build_delivery_agent

    _pipeline_stages.append(build_delivery_agent())

autobrief_pipeline = SequentialAgent(
    name="AutoBriefPipeline",
    description=(
        "Turns a raw client inquiry into a scoped, priced proposal: "
        "intake -> research -> scope/estimate -> proposal"
        + (" -> deliver (HITL-gated)" if ENABLE_MCP else "")
        + "."
    ),
    sub_agents=_pipeline_stages,
)
