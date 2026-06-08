"""Reproducible generator for the AutoBrief eval gold expectations.

Why a generator instead of hand-written JSON: the *numeric* expectations
(price band + week range) must agree with the deterministic rubric. So we keep a
small human-authored table of the qualitative expectations (routing, archetype,
features, complexity, rush) and DERIVE every dollar/week number by actually
calling `autobrief.tools.estimate_scope.estimate_scope(...)`. That guarantees the
gold can never drift from the rubric.

Run:  python eval/_make_gold.py   (from anywhere — sys.path is fixed below)
Output: one eval/gold/<stem>.json per inquiry, plus a consistency confirmation.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

# Make `import autobrief...` work regardless of cwd: repo root is the parent of eval/.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from autobrief.tools.estimate_scope import estimate_scope  # noqa: E402

_GOLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gold")


# --- Human-authored qualitative expectation table ---------------------------
# For decline / need_clarification cases archetype is None and no estimate is
# computed (all numeric fields stay null). For proceed cases we record the
# archetype/features/complexity/rush we expect the LLM to classify; the dollars
# and weeks are filled in from estimate_scope() below.
GOLD_TABLE: list[dict[str, Any]] = [
    {
        "stem": "01_crud_saas_clean",
        "expected_routing": "proceed",
        "expected_archetype": "crud-saas-mvp",
        "expected_feature_keys": ["auth_billing"],
        "expected_complexity": 1.0,
        "expected_rush": False,
        "rationale": "Clean CRUD SaaS with explicit auth+Stripe billing, web, ~5wk, $15-18k.",
    },
    {
        "stem": "02_ai_chat_assistant",
        "expected_routing": "proceed",
        "expected_archetype": "ai-chat-assistant",
        "expected_feature_keys": ["file_upload_storage", "notifications"],
        "expected_complexity": 1.1,
        "expected_rush": False,
        "rationale": "RAG chat over uploaded docs: AI assistant base + file upload + notifications.",
    },
    {
        "stem": "03_data_dashboard",
        "expected_routing": "proceed",
        "expected_archetype": "data-dashboard",
        "expected_feature_keys": ["third_party_integration"],
        "expected_complexity": 1.0,
        "expected_rush": False,
        "rationale": "Read-only analytics dashboard over existing DB + weather API integration.",
    },
    {
        "stem": "04_mobile_companion",
        "expected_routing": "proceed",
        "expected_archetype": "mobile-companion",
        "expected_feature_keys": ["notifications", "admin_dashboard"],
        "expected_complexity": 1.0,
        "expected_rush": False,
        "rationale": "Flutter companion app with push notifications + coach admin dashboard.",
    },
    {
        "stem": "05_landing_waitlist_simple",
        "expected_routing": "proceed",
        "expected_archetype": "landing+waitlist",
        "expected_feature_keys": [],
        "expected_complexity": 1.0,
        "expected_rush": False,
        "rationale": "Simple one-page landing + email waitlist capture, ~2wk, small budget.",
    },
    {
        "stem": "06_vague_clarify",
        "expected_routing": "need_clarification",
        "expected_archetype": None,
        "expected_feature_keys": [],
        "expected_complexity": None,
        "expected_rush": None,
        "rationale": "No platform, budget, deadline, or concrete scope — must clarify before scoping.",
    },
    {
        "stem": "07_rush_job",
        "expected_routing": "proceed",
        "expected_archetype": "crud-saas-mvp",
        "expected_feature_keys": ["auth_billing"],
        "expected_complexity": 1.0,
        "expected_rush": True,
        "rationale": "CRUD SaaS + Stripe with a hard 12-day deadline -> rush multiplier applies.",
    },
    {
        "stem": "08_out_of_scope_decline",
        "expected_routing": "decline",
        "expected_archetype": None,
        "expected_feature_keys": [],
        "expected_complexity": None,
        "expected_rush": None,
        "rationale": "Full licensed retail bank in 2 weeks for $500 — wildly out of the 2-6wk MVP scope.",
    },
]


def _derive_numbers(entry: dict[str, Any]) -> dict[str, Optional[int]]:
    """Fill price band + week range from estimate_scope() for proceed cases.

    For non-proceed cases (no archetype) all numeric fields are null.
    """
    if entry["expected_archetype"] is None:
        return {
            "expected_price_band_low_usd": None,
            "expected_price_band_high_usd": None,
            "expected_week_low": None,
            "expected_week_high": None,
        }
    est = estimate_scope(
        entry["expected_archetype"],
        entry["expected_feature_keys"],
        entry["expected_complexity"],
        entry["expected_rush"],
    )
    return {
        "expected_price_band_low_usd": int(est["price_band_low_usd"]),
        "expected_price_band_high_usd": int(est["price_band_high_usd"]),
        "expected_week_low": int(est["week_low"]),
        "expected_week_high": int(est["week_high"]),
    }


def build_gold() -> list[dict[str, Any]]:
    """Materialize every gold JSON to disk and return the records."""
    os.makedirs(_GOLD_DIR, exist_ok=True)
    records: list[dict[str, Any]] = []
    for entry in GOLD_TABLE:
        record = dict(entry)
        record.update(_derive_numbers(entry))
        # Stable field ordering for readable diffs.
        ordered = {
            "stem": record["stem"],
            "expected_routing": record["expected_routing"],
            "expected_archetype": record["expected_archetype"],
            "expected_feature_keys": record["expected_feature_keys"],
            "expected_complexity": record["expected_complexity"],
            "expected_rush": record["expected_rush"],
            "expected_price_band_low_usd": record["expected_price_band_low_usd"],
            "expected_price_band_high_usd": record["expected_price_band_high_usd"],
            "expected_week_low": record["expected_week_low"],
            "expected_week_high": record["expected_week_high"],
            "rationale": record["rationale"],
        }
        path = os.path.join(_GOLD_DIR, f"{record['stem']}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ordered, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        records.append(ordered)
    return records


def _confirm_consistency(records: list[dict[str, Any]]) -> bool:
    """Re-run estimate_scope and assert the written numbers still match it."""
    all_ok = True
    for rec in records:
        if rec["expected_archetype"] is None:
            continue
        est = estimate_scope(
            rec["expected_archetype"],
            rec["expected_feature_keys"],
            rec["expected_complexity"],
            rec["expected_rush"],
        )
        ok = (
            rec["expected_price_band_low_usd"] == int(est["price_band_low_usd"])
            and rec["expected_price_band_high_usd"] == int(est["price_band_high_usd"])
            and rec["expected_week_low"] == int(est["week_low"])
            and rec["expected_week_high"] == int(est["week_high"])
        )
        all_ok = all_ok and ok
        flag = "OK " if ok else "FAIL"
        print(
            f"  [{flag}] {rec['stem']:<28} "
            f"₩{rec['expected_price_band_low_usd']:,}-₩{rec['expected_price_band_high_usd']:,}  "
            f"{rec['expected_week_low']}-{rec['expected_week_high']}wk"
        )
    return all_ok


if __name__ == "__main__":
    records = build_gold()
    print(f"Wrote {len(records)} gold files to {_GOLD_DIR}\n")
    print("Gold-consistency check (written numbers == estimate_scope output):")
    consistent = _confirm_consistency(records)
    n_numeric = sum(1 for r in records if r["expected_archetype"] is not None)
    n_null = len(records) - n_numeric
    print(
        f"\n{n_numeric} numeric cases verified, {n_null} non-scoring "
        f"(decline/clarify) cases with null numbers."
    )
    if consistent:
        print("CONSISTENT: all gold price bands & week ranges equal estimate_scope output.")
        sys.exit(0)
    print("INCONSISTENT: gold drifted from the rubric — fix the table.")
    sys.exit(1)
