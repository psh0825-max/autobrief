"""Pure scoring functions for the AutoBrief eval harness.

No network, no model calls — every function is a deterministic comparison of a
prediction against a gold record. Run this module directly to exercise the
inline self-tests:  python eval/scorers.py
"""
from __future__ import annotations

from typing import Any, Iterable, Optional


def archetype_accuracy(pred: Optional[str], gold: dict[str, Any]) -> int:
    """1 if the predicted archetype string equals the gold archetype, else 0.

    Both sides are compared as-is (the rubric keys, e.g. "crud-saas-mvp").
    A gold archetype of None (decline/clarify) only matches a None prediction.
    """
    return int(pred == gold.get("expected_archetype"))


def scope_jaccard(pred_keys: Iterable[str], gold_keys: Iterable[str]) -> float:
    """Jaccard overlap |A ∩ B| / |A ∪ B| of the two feature-key sets.

    Two empty sets are defined as a perfect match (1.0) — both correctly
    selected "no add-ons".
    """
    a, b = set(pred_keys), set(gold_keys)
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def price_in_band(
    pred_estimate: Optional[dict[str, Any]],
    gold: dict[str, Any],
    tol: float = 0.15,
) -> bool:
    """True if the predicted price is consistent with the gold price band.

    Definition (documented): we treat the prediction as in-band if the
    predicted quoted band [pred_low, pred_high] OVERLAPS the gold band
    [gold_low, gold_high] after each band is widened by `tol` (default 15%).
    This is the "overlapping bands with tolerance" rule — chosen over a strict
    midpoint check because the studio always quotes a band to the client, so
    band overlap is the operationally meaningful notion of "we'd quote the
    same ballpark".

    For non-scoring gold cases (no expected band, i.e. decline/clarify) there is
    no price to check, so this returns True iff the prediction also has no band.
    """
    gold_low = gold.get("expected_price_band_low_usd")
    gold_high = gold.get("expected_price_band_high_usd")

    # Decline / clarify gold: no band expected. Pred should also have none.
    if gold_low is None or gold_high is None:
        return not pred_estimate or pred_estimate.get("price_band_low_usd") is None

    if not pred_estimate:
        return False
    pred_low = pred_estimate.get("price_band_low_usd")
    pred_high = pred_estimate.get("price_band_high_usd")
    if pred_low is None or pred_high is None:
        return False

    # Widen each band by the tolerance, then test for interval overlap.
    g_lo = gold_low * (1 - tol)
    g_hi = gold_high * (1 + tol)
    p_lo = pred_low * (1 - tol)
    p_hi = pred_high * (1 + tol)
    return p_lo <= g_hi and g_lo <= p_hi


def routing_accuracy(pred: Optional[str], gold: dict[str, Any]) -> int:
    """1 if the predicted routing decision matches gold, else 0.

    Routing values are "proceed" | "need_clarification" | "decline".
    """
    return int(pred == gold.get("expected_routing"))


def trajectory_valid(events_or_tool_names: Iterable[str], expected_routing: str = "proceed") -> bool:
    """Validate the tool-call trajectory.

    Rules (Day-1 scope):
      * For a "proceed" case the deterministic estimator (`compute_estimate`)
        must have been called exactly once.
      * No delivery/send tool (e.g. an MCP email/deck send) may run — for now
        we just assert that no obviously-named send/deliver tool appears, since
        approval gating is not wired yet.
      * For decline / need_clarification cases, `compute_estimate` should NOT
        have been called (no scoping happens), so we only enforce the no-send
        rule.

    Args:
        events_or_tool_names: iterable of tool-call name strings observed.
        expected_routing: the gold routing for this case.
    """
    names = [str(n) for n in events_or_tool_names]
    estimate_calls = sum(1 for n in names if n == "compute_estimate")

    # Nothing should be sent/delivered without an approval gate (not built yet).
    forbidden_substrings = ("send", "deliver", "create_draft", "export")
    if any(any(sub in n.lower() for sub in forbidden_substrings) for n in names):
        return False

    if expected_routing == "proceed":
        return estimate_calls == 1
    # decline / need_clarification: scoping should not have run.
    return estimate_calls == 0


# --------------------------------------------------------------------------- #
# Inline self-tests — run `python eval/scorers.py` to confirm they pass.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # archetype_accuracy
    assert archetype_accuracy("crud-saas-mvp", {"expected_archetype": "crud-saas-mvp"}) == 1
    assert archetype_accuracy("data-dashboard", {"expected_archetype": "crud-saas-mvp"}) == 0
    assert archetype_accuracy(None, {"expected_archetype": None}) == 1
    assert archetype_accuracy("crud-saas-mvp", {"expected_archetype": None}) == 0

    # scope_jaccard
    assert scope_jaccard([], []) == 1.0
    assert scope_jaccard(["auth_billing"], ["auth_billing"]) == 1.0
    assert scope_jaccard(["auth_billing"], ["auth_billing", "ai_feature"]) == 0.5
    assert scope_jaccard(["x"], ["y"]) == 0.0

    # price_in_band — overlapping bands with tolerance
    gold_proceed = {
        "expected_price_band_low_usd": 14500,
        "expected_price_band_high_usd": 17500,
    }
    # Exact match -> in band.
    assert price_in_band(
        {"price_band_low_usd": 14500, "price_band_high_usd": 17500}, gold_proceed
    ) is True
    # Adjacent-but-within-tolerance band -> overlaps after widening.
    assert price_in_band(
        {"price_band_low_usd": 18000, "price_band_high_usd": 20000}, gold_proceed
    ) is True
    # Way off (10x) -> no overlap.
    assert price_in_band(
        {"price_band_low_usd": 150000, "price_band_high_usd": 180000}, gold_proceed
    ) is False
    # Gold has no band (decline) and pred has none -> True.
    gold_none = {"expected_price_band_low_usd": None, "expected_price_band_high_usd": None}
    assert price_in_band(None, gold_none) is True
    # Gold has no band but pred produced one -> False.
    assert price_in_band(
        {"price_band_low_usd": 14500, "price_band_high_usd": 17500}, gold_none
    ) is False
    # Gold expects a band but pred is missing -> False.
    assert price_in_band(None, gold_proceed) is False

    # routing_accuracy
    assert routing_accuracy("proceed", {"expected_routing": "proceed"}) == 1
    assert routing_accuracy("decline", {"expected_routing": "proceed"}) == 0

    # trajectory_valid
    assert trajectory_valid(["compute_estimate"], "proceed") is True
    assert trajectory_valid([], "proceed") is False              # estimate never called
    assert trajectory_valid(["compute_estimate", "compute_estimate"], "proceed") is False
    assert trajectory_valid([], "decline") is True               # no scoping is correct
    assert trajectory_valid(["compute_estimate"], "decline") is False
    assert trajectory_valid(["compute_estimate", "send_email"], "proceed") is False  # forbidden send

    print("All scorer self-tests passed.")
