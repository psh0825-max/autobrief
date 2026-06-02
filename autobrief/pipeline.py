"""AutoBriefPipeline: the deterministic intake -> research -> scope -> proposal spine.

SequentialAgent is deprecated in ADK 2.1.0 but still functional; we use it here for
a reproducible demo flow. State flows implicitly between sub-agents via output_key.
"""
from __future__ import annotations

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from google.adk.agents import SequentialAgent

from .sub_agents.intake_parser import intake_parser
from .sub_agents.proposal_writer import proposal_writer
from .sub_agents.researcher import researcher
from .sub_agents.scoper_estimator import scoper_estimator

autobrief_pipeline = SequentialAgent(
    name="AutoBriefPipeline",
    description=(
        "Turns a raw client inquiry into a scoped, priced proposal: "
        "intake -> research -> scope/estimate -> proposal."
    ),
    sub_agents=[intake_parser, researcher, scoper_estimator, proposal_writer],
)
