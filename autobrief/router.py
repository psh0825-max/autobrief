"""AutoBriefRouter: a custom orchestrator that triages then runs the right branch.

ADK's LLM-driven `transfer_to_agent` flow cannot be used here: in ADK 2.1.0 an
LlmAgent that has a SequentialAgent peer crashes while computing transfer targets
(`SequentialAgent` has no `.mode`). So instead of LLM transfer, this BaseAgent
orchestrates explicitly:

  1. run RouterClassifier  -> writes state['routing'] = {decision, reason}
  2. branch on the decision:
       proceed            -> AutoBriefPipeline (scope + proposal, +delivery if MCP)
       need_clarification -> ClarifierAgent
       decline            -> DeclineAgent

Deterministic branching is also easier to evaluate and trace than LLM transfer.
"""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from .schemas import RoutingDecision


class AutoBriefRouter(BaseAgent):
    """Triage an inbound inquiry, then run the matching sub-agent branch."""

    router_classifier: BaseAgent
    pipeline: BaseAgent
    clarifier_agent: BaseAgent
    decline_agent: BaseAgent

    def __init__(
        self,
        *,
        name: str,
        router_classifier: BaseAgent,
        pipeline: BaseAgent,
        clarifier_agent: BaseAgent,
        decline_agent: BaseAgent,
    ) -> None:
        super().__init__(
            name=name,
            description=(
                "Triages an inbound client inquiry into proceed / "
                "need_clarification / decline and runs the matching branch."
            ),
            router_classifier=router_classifier,
            pipeline=pipeline,
            clarifier_agent=clarifier_agent,
            decline_agent=decline_agent,
            # Registered so the framework wires parent_agent / lookups correctly.
            sub_agents=[router_classifier, pipeline, clarifier_agent, decline_agent],
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1) Triage.
        async for event in self.router_classifier.run_async(ctx):
            yield event

        verdict = ctx.session.state.get("routing")
        decision = verdict.get("decision") if isinstance(verdict, dict) else verdict
        decision = getattr(decision, "value", decision)  # enum -> str if needed

        # 2) Branch. Unknown/missing decisions fall through to the safe option
        # (decline) rather than spending the full pipeline on a bad parse.
        if decision == RoutingDecision.proceed.value:
            branch = self.pipeline
        elif decision == RoutingDecision.need_clarification.value:
            branch = self.clarifier_agent
        else:
            branch = self.decline_agent

        async for event in branch.run_async(ctx):
            yield event
