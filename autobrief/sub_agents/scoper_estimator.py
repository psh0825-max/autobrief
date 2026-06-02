"""ScoperEstimator: classify the project (LLM) then compute a deterministic estimate (tool).

The model only chooses the archetype, feature add-ons, complexity, and rush flag.
All pricing/timeline math happens inside estimate_scope() so prices are never
hallucinated. The tool writes the structured estimate to session.state['estimate'].
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

from ..config import FLASH
from ..tools.estimate_scope import estimate_scope


def compute_estimate(
    archetype: str,
    feature_keys: list[str],
    complexity: float,
    rush: bool,
    tool_context: ToolContext,
) -> dict:
    """Compute the deterministic scope, timeline, and price estimate from the rubric.

    Call this exactly once after you have classified the project. The returned
    numbers are authoritative — never invent or alter prices yourself.

    Args:
        archetype: One of "landing+waitlist", "crud-saas-mvp", "ai-chat-assistant",
            "data-dashboard", "mobile-companion", "integration-glue".
        feature_keys: Subset of "auth_billing", "ai_feature",
            "third_party_integration", "admin_dashboard", "realtime",
            "file_upload_storage", "multilingual", "analytics", "notifications".
        complexity: Complexity multiplier between 1.0 (simple) and 1.6 (very complex).
        rush: True if the client's deadline is tighter than a normal timeline.

    Returns:
        The full estimate breakdown (line items, days, week range, price band).
    """
    result = estimate_scope(archetype, feature_keys, complexity, rush)
    tool_context.state["estimate"] = result
    return result


_INSTRUCTION = """You are the scoping lead for LightOn Plus Lab (solo AI MVP studio).

Structured client inquiry:
{inquiry}

Steps:
1. Classify the project into exactly one archetype.
2. Select add-on feature keys — but be CONSERVATIVE. The archetype's base price
   ALREADY includes its defining capability plus a standard auth/data/dashboard
   layer, so never add a key that merely restates the archetype's core. In
   particular:
     - crud-saas-mvp already includes basic sign-up/login and a standard
       list/pipeline dashboard. Add `auth_billing` only for paid billing
       (e.g. Stripe); add `admin_dashboard` only for a SEPARATE privileged admin
       area, not the normal user dashboard.
     - ai-chat-assistant already includes the chat/RAG itself. Add `ai_feature`
       only for an EXTRA AI capability beyond the core chat.
     - data-dashboard already includes charts/visualization/filtering. `analytics`
       means separate product-usage instrumentation, NOT the dashboard's own charts.
   Select a key ONLY when the inquiry explicitly asks for that distinct capability.
   Prefer the smallest correct set; do not infer features the client never mentioned.
3. Estimate a complexity multiplier (1.0 typical, up to 1.6 for novel/complex work).
4. Set rush=true only if the stated deadline is clearly tighter than a normal
   2-6 week build (the tool applies a rush multiplier — a tight deadline is priced,
   never a reason to refuse the work).
5. Call `compute_estimate` once with those values. Do NOT guess any price or
   number yourself — the tool is the only source of pricing truth.
6. After the tool returns, write a concise scope summary: the chosen archetype,
   the included features, the week range, the quoted price band, and a one-line
   justification. If the tool's notes mention exceeding the 6-week ceiling, flag
   that phasing may be needed.
"""

scoper_estimator = LlmAgent(
    name="ScoperEstimator",
    model=FLASH,
    description="Classifies the project and computes a deterministic scope/price estimate.",
    instruction=_INSTRUCTION,
    tools=[compute_estimate],
    output_key="estimate_summary",
)
