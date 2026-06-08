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


def _resolve_currency(rubric: dict[str, Any], currency: str | None) -> tuple[str, dict[str, Any]]:
    """Pick the display currency (arg > AUTOBRIEF_CURRENCY env > rubric base).

    Returns (code, config). Falls back to the base currency if the requested one
    is unknown. An optional ``AUTOBRIEF_FX_<CODE>`` env var overrides the rate.
    """
    base = rubric.get("currency", "KRW")
    table = rubric.get("display_currencies", {}) or {}
    requested = (currency or os.environ.get("AUTOBRIEF_CURRENCY") or base).upper()
    if requested not in table:
        requested = base
    cfg = dict(table.get(requested) or {})
    # Sensible defaults if the rubric entry is sparse.
    cfg.setdefault("symbol", "")
    cfg.setdefault("rate", 1.0)
    cfg.setdefault("rounding", 1000)
    cfg.setdefault("line_rounding", 1000)
    cfg.setdefault("decimals", 0)
    rate_override = os.environ.get(f"AUTOBRIEF_FX_{requested}")
    if rate_override:
        try:
            cfg["rate"] = float(rate_override)
        except ValueError:
            pass
    return requested, cfg


def _fmt_money(value: float, symbol: str, decimals: int) -> str:
    if decimals:
        return f"{symbol}{value:,.{decimals}f}"
    return f"{symbol}{int(round(value)):,}"


def estimate_scope(
    archetype: str,
    feature_keys: list[str],
    complexity: float = 1.0,
    rush: bool = False,
    currency: str | None = None,
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

    # Display currency (selectable): all rubric amounts are in the base currency
    # and get converted to this for every money field returned.
    ccy_code, ccy = _resolve_currency(rubric, currency)
    fx = float(ccy["rate"])
    symbol = ccy["symbol"]
    line_rounding = int(ccy["line_rounding"])
    decimals = int(ccy["decimals"])

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

    # --- Quoted price band around the point estimate (converted to display ccy) ---
    rounding = int(ccy["rounding"])
    spread = float(bands["band_spread_pct"])
    total_price = _round_to(total_price_raw * fx, rounding)
    price_band_low = _round_to(total_price_raw * (1 - spread) * fx, rounding)
    price_band_high = _round_to(total_price_raw * (1 + spread) * fx, rounding)

    # Convert each line item + subtotal into the display currency.
    for li in line_items:
        li["price_usd"] = _round_to(li["price_usd"] * fx, line_rounding)
    subtotal = _round_to(subtotal * fx, line_rounding)

    price_band = f"{_fmt_money(price_band_low, symbol, decimals)} - {_fmt_money(price_band_high, symbol, decimals)}"

    # --- Confidence: high for simple/typical, lower for complex/rush ---
    confidence = 0.9 - (clamped_complexity - 1.0) * 0.5
    if rush:
        confidence -= 0.1
    confidence = round(max(0.5, min(0.95, confidence)), 2)

    return {
        "archetype": archetype,
        "currency": ccy_code,
        "currency_symbol": symbol,
        "price_band": price_band,  # preformatted, ready to quote verbatim
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
