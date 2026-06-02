"""Deterministic scope/price estimator — the business-case credibility core.

The LLM only *classifies* (archetype, feature keys, complexity, rush). Every
number a client ever sees is computed here from rubric.yaml, so prices can never
be hallucinated and always trace to a line-item breakdown.
"""
from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Any

import yaml

_RUBRIC_PATH = os.path.join(os.path.dirname(__file__), "rubric.yaml")


@lru_cache(maxsize=1)
def _load_rubric() -> dict[str, Any]:
    with open(_RUBRIC_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


def estimate_scope(
    archetype: str,
    feature_keys: list[str],
    complexity: float = 1.0,
    rush: bool = False,
) -> dict[str, Any]:
    """Compute a transparent scope + price estimate from the rubric.

    Args:
        archetype: One of the keys under `archetypes` in rubric.yaml
            (e.g. "crud-saas-mvp").
        feature_keys: Keys under `feature_addons` to include
            (e.g. ["auth_billing", "ai_feature"]). Unknown keys are ignored
            and noted.
        complexity: Complexity multiplier, clamped to the rubric's
            [complexity_min, complexity_max] range.
        rush: Whether the client deadline forces a rush (applies rush multiplier).

    Returns:
        A ScopeEstimate-shaped dict with a full line-item breakdown, day and
        week ranges (clamped to the studio's 2-6 week promise), the point price,
        and a quoted price band. All values are deterministic.
    """
    rubric = _load_rubric()
    archetypes = rubric["archetypes"]
    addons = rubric["feature_addons"]
    mult = rubric["multipliers"]
    bands = rubric["bands"]

    notes: list[str] = []

    # --- Resolve archetype (fall back to the most common MVP shape) ---
    if archetype not in archetypes:
        notes.append(f"Unknown archetype '{archetype}'; defaulted to 'crud-saas-mvp'.")
        archetype = "crud-saas-mvp"
    arch = archetypes[archetype]

    # --- Clamp complexity into the allowed range ---
    c_min, c_max = mult["complexity_min"], mult["complexity_max"]
    clamped_complexity = max(c_min, min(c_max, float(complexity)))
    if clamped_complexity != complexity:
        notes.append(f"Complexity {complexity} clamped to {clamped_complexity}.")

    rush_multiplier = float(mult["rush"]) if rush else 1.0

    # --- Build line items: base archetype + each valid add-on ---
    line_items: list[dict[str, Any]] = [
        {
            "key": archetype,
            "label": arch["label"],
            "days": float(arch["base_days"]),
            "price_usd": float(arch["base_price_usd"]),
        }
    ]
    for key in feature_keys:
        if key not in addons:
            notes.append(f"Ignored unknown feature '{key}'.")
            continue
        a = addons[key]
        line_items.append(
            {
                "key": key,
                "label": a["label"],
                "days": float(a["days"]),
                "price_usd": float(a["price_usd"]),
            }
        )

    base_days = sum(li["days"] for li in line_items)
    subtotal = sum(li["price_usd"] for li in line_items)

    # --- Apply multipliers + contingency ---
    contingency_pct = float(bands["contingency_pct"])
    total_price_raw = subtotal * clamped_complexity * rush_multiplier * (1 + contingency_pct)
    total_days = base_days * clamped_complexity

    # --- Weeks: solo utilization, clamped to the studio promise ---
    utilization = float(bands["utilization"])
    raw_weeks = total_days / 5.0 / utilization
    week_low = max(bands["week_min"], math.floor(raw_weeks))
    week_high = min(bands["week_max"], math.ceil(raw_weeks) + 1)
    if week_low > week_high:
        week_low = week_high
    if raw_weeks > bands["week_max"]:
        notes.append(
            f"Estimated {raw_weeks:.1f} weeks exceeds the 6-week studio ceiling; "
            "consider phasing the scope."
        )

    # --- Quoted price band around the point estimate ---
    rounding = int(bands["band_rounding_usd"])
    spread = float(bands["band_spread_pct"])
    total_price = _round_to(total_price_raw, rounding)
    price_band_low = _round_to(total_price_raw * (1 - spread), rounding)
    price_band_high = _round_to(total_price_raw * (1 + spread), rounding)

    # --- Confidence: high for simple/typical, lower for complex/rush ---
    confidence = 0.9 - (clamped_complexity - 1.0) * 0.5
    if rush:
        confidence -= 0.1
    confidence = round(max(0.5, min(0.95, confidence)), 2)

    return {
        "archetype": archetype,
        "line_items": line_items,
        "base_days": round(base_days, 1),
        "total_days": round(total_days, 1),
        "week_low": int(week_low),
        "week_high": int(week_high),
        "subtotal_usd": round(subtotal, 2),
        "complexity": clamped_complexity,
        "rush_multiplier": rush_multiplier,
        "contingency_pct": contingency_pct,
        "total_price_usd": total_price,
        "price_band_low_usd": price_band_low,
        "price_band_high_usd": price_band_high,
        "confidence": confidence,
        "notes": notes,
    }


if __name__ == "__main__":
    import json

    print("== crud-saas-mvp + auth_billing + ai_feature, complexity 1.2 ==")
    print(json.dumps(
        estimate_scope("crud-saas-mvp", ["auth_billing", "ai_feature"], 1.2, False),
        indent=2,
    ))
    print("\n== landing+waitlist, rush ==")
    print(json.dumps(estimate_scope("landing+waitlist", [], 1.0, True), indent=2))
    print("\n== unknown archetype + bad feature (guardrail) ==")
    print(json.dumps(estimate_scope("build-me-a-bank", ["nonsense"], 2.5, False), indent=2))
