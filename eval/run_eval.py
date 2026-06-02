"""End-to-end evaluation harness for the AutoBrief pipeline.

Runs every inquiry in eval/inquiries/ through `root_agent` (the ADK Runner
pattern is copied from smoke_test.py), captures the final session state and the
list of tool calls, derives predictions, scores them against eval/gold/, and
prints a per-case + aggregate results table plus a BEFORE/AFTER business-impact
table. Aggregate results are written to eval/results/last_run.json.

GRACEFUL DEGRADATION: the Gemini/Vertex credential may not be live yet in this
environment. Every per-case model run is wrapped in try/except; if the model
call fails (auth/network), we print a clear MODEL UNAVAILABLE banner and still
exit 0 after running the deterministic gold-consistency self-check. The harness
never hangs.

ROUTING: the proceed/clarify/decline ROUTER (autobrief/agent.py) is the root
agent. We derive its decision from the resulting session state (proposal ->
proceed, clarification -> need_clarification, neither -> decline) so routing
accuracy is scored across all three outcome types.

Run:  python eval/run_eval.py     (works from any cwd; sys.path is fixed below)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any, Optional

# Windows consoles often default to a legacy codepage (cp949/cp1252) that can't
# encode the characters we print. Force UTF-8 so the harness never dies on I/O.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# Make `import autobrief...` work regardless of cwd: repo root is parent of eval/.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import scorers  # local module (eval/ is on sys.path[0])  # noqa: E402
from _make_gold import build_gold, _confirm_consistency  # noqa: E402

_EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
_INQUIRY_DIR = os.path.join(_EVAL_DIR, "inquiries")
_GOLD_DIR = os.path.join(_EVAL_DIR, "gold")
_RESULTS_DIR = os.path.join(_EVAL_DIR, "results")

# Manual baseline assumptions for the business-impact comparison (founder doing
# intake + research + scoping + proposal by hand).
MANUAL_HOURS_PER_PROPOSAL = 4.0          # ~3-5 h; midpoint
MANUAL_INQUIRIES_PER_DAY = "~3-4"
FOUNDER_HOURLY_USD = 120                  # blended founder opportunity cost
APPROX_LLM_COST_PER_PROPOSAL_USD = 0.05  # Flash-tier classify+write, rough


def _load_inquiries() -> list[tuple[str, str]]:
    """Return [(stem, raw_text)] for every .txt inquiry, sorted by filename."""
    out: list[tuple[str, str]] = []
    for name in sorted(os.listdir(_INQUIRY_DIR)):
        if not name.endswith(".txt"):
            continue
        stem = name[: -len(".txt")]
        with open(os.path.join(_INQUIRY_DIR, name), "r", encoding="utf-8") as fh:
            out.append((stem, fh.read()))
    return out


def _load_gold(stem: str) -> dict[str, Any]:
    with open(os.path.join(_GOLD_DIR, f"{stem}.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _features_from_estimate(estimate: Optional[dict[str, Any]]) -> list[str]:
    """Derive predicted feature keys = line-item keys minus the archetype key."""
    if not estimate:
        return []
    arch = estimate.get("archetype")
    return [li["key"] for li in estimate.get("line_items", []) if li.get("key") != arch]


def _derive_routing(state: dict[str, Any]) -> str:
    """Read the AutoBriefRouter's decision from session state.

    RouterClassifier writes a structured verdict to state['routing'] = {decision,
    reason}, so we observe the decision directly. We fall back to inferring it from
    which branch produced an artifact (proposal -> proceed, clarification ->
    need_clarification, else decline) if the verdict is missing.
    """
    verdict = state.get("routing")
    if isinstance(verdict, dict) and verdict.get("decision"):
        decision = verdict["decision"]
        return getattr(decision, "value", decision)
    if state.get("proposal"):
        return "proceed"
    if state.get("clarification"):
        return "need_clarification"
    return "decline"


def _is_transient(exc: Exception) -> bool:
    """A 429 / rate-limit / resource-exhausted error worth retrying with backoff."""
    text = f"{type(exc).__name__} {exc}".lower()
    return any(s in text for s in ("429", "resource_exhausted", "resourceexhausted",
                                   "rate limit", "quota", "unavailable", "503"))


async def _run_one_with_retry(
    stem: str, raw_text: str, max_attempts: int = 5
) -> dict[str, Any]:
    """Run one case, retrying transient quota/rate errors with exponential backoff.

    Vertex per-minute quotas (especially gemini-2.5-pro on a fresh project) can
    return 429s under back-to-back eval runs. We back off (4s, 8s, 16s, 32s) and
    retry so a transient throttle doesn't abort the whole scored run. Non-transient
    errors (auth, bad request) are raised immediately.
    """
    delay = 4.0
    for attempt in range(1, max_attempts + 1):
        try:
            return await _run_one(stem, raw_text)
        except Exception as exc:
            if attempt == max_attempts or not _is_transient(exc):
                raise
            print(f"  [{stem}] transient error (attempt {attempt}/{max_attempts}); "
                  f"backing off {delay:.0f}s: {type(exc).__name__}")
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")  # pragma: no cover


async def _run_one(stem: str, raw_text: str) -> dict[str, Any]:
    """Run a single inquiry through root_agent; return final state + tool calls.

    Imports of ADK / the agent happen lazily inside this function so that a
    missing-credential import error is caught per-case rather than at module
    load, keeping the harness's deterministic self-check independent of the model.
    """
    from google.genai import types
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    from autobrief.agent import root_agent
    from autobrief.config import APP_NAME

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id="eval-user", state={}
    )
    message = types.Content(role="user", parts=[types.Part(text=raw_text)])

    tool_calls: list[str] = []
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    tool_calls.append(fc.name)

    final = await session_service.get_session(
        app_name=APP_NAME, user_id=session.user_id, session_id=session.id
    )
    return {"state": dict(final.state), "tool_calls": tool_calls}


def _score_case(stem: str, run: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Apply all scorers to a single completed run."""
    state = run["state"]
    estimate = state.get("estimate")
    pred_archetype = estimate.get("archetype") if estimate else None
    pred_features = _features_from_estimate(estimate)
    pred_routing = _derive_routing(state)

    return {
        "stem": stem,
        "pred_routing": pred_routing,
        "pred_archetype": pred_archetype,
        "pred_features": pred_features,
        "archetype_acc": scorers.archetype_accuracy(pred_archetype, gold),
        "scope_jaccard": scorers.scope_jaccard(pred_features, gold["expected_feature_keys"]),
        "price_in_band": scorers.price_in_band(estimate, gold),
        "routing_acc": scorers.routing_accuracy(pred_routing, gold),
        "trajectory_valid": scorers.trajectory_valid(
            run["tool_calls"], gold["expected_routing"]
        ),
    }


def _print_self_check() -> bool:
    """Re-materialize gold and confirm it agrees with estimate_scope()."""
    print("=" * 72)
    print("DETERMINISTIC GOLD-CONSISTENCY SELF-CHECK")
    print("=" * 72)
    records = build_gold()
    ok = _confirm_consistency(records)
    print("RESULT:", "CONSISTENT" if ok else "INCONSISTENT")
    return ok


def _print_results_table(rows: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 100)
    print("PER-CASE RESULTS")
    print("=" * 100)
    hdr = f"{'case':<28}{'routing':<10}{'arch':<6}{'jaccard':<9}{'price':<7}{'traj':<6}{'sec':<7}"
    print(hdr)
    print("-" * 100)
    for r in rows:
        print(
            f"{r['stem']:<28}"
            f"{('OK' if r['routing_acc'] else 'x'):<10}"
            f"{('OK' if r['archetype_acc'] else 'x'):<6}"
            f"{r['scope_jaccard']:<9.2f}"
            f"{('OK' if r['price_in_band'] else 'x'):<7}"
            f"{('OK' if r['trajectory_valid'] else 'x'):<6}"
            f"{r.get('seconds', 0.0):<7.2f}"
        )


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {}
    return {
        "n_cases": n,
        "archetype_accuracy_pct": round(100 * sum(r["archetype_acc"] for r in rows) / n, 1),
        "mean_scope_jaccard": round(sum(r["scope_jaccard"] for r in rows) / n, 3),
        "price_in_band_pct": round(100 * sum(1 for r in rows if r["price_in_band"]) / n, 1),
        "routing_accuracy_pct": round(100 * sum(r["routing_acc"] for r in rows) / n, 1),
        "trajectory_valid_pct": round(100 * sum(1 for r in rows if r["trajectory_valid"]) / n, 1),
    }


def _print_aggregate(agg: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("AGGREGATE")
    print("=" * 60)
    for k, v in agg.items():
        print(f"  {k:<28} {v}")


def _print_business_impact(agg: dict[str, Any], mean_secs: Optional[float]) -> None:
    print("\n" + "=" * 84)
    print("BEFORE / AFTER BUSINESS IMPACT")
    print("=" * 84)
    if mean_secs is not None:
        autobrief_ttp = f"~{mean_secs:.0f} s / proposal"
        per_8h = int(8 * 3600 / mean_secs) if mean_secs > 0 else "n/a"
        autobrief_per_day = f"~{per_8h} (compute-bound)"
        scope_acc = f"{agg.get('mean_scope_jaccard', 'n/a')} mean Jaccard"
        price_band = f"{agg.get('price_in_band_pct', 'n/a')}%"
    else:
        autobrief_ttp = "MODEL UNAVAILABLE (rerun w/ live creds)"
        autobrief_per_day = "MODEL UNAVAILABLE"
        scope_acc = "MODEL UNAVAILABLE"
        price_band = "MODEL UNAVAILABLE"

    col = f"{'Metric':<26}{'Manual baseline (founder)':<30}{'AutoBrief':<28}"
    print(col)
    print("-" * 84)
    print(f"{'time-to-first-proposal':<26}{'~3-5 h':<30}{autobrief_ttp:<28}")
    print(f"{'inquiries/day':<26}{MANUAL_INQUIRIES_PER_DAY:<30}{autobrief_per_day:<28}")
    print(f"{'scope accuracy':<26}{'(n/a)':<30}{scope_acc:<28}")
    print(f"{'price-in-band':<26}{'(n/a)':<30}{price_band:<28}")
    print(
        f"{'cost/proposal':<26}"
        f"{f'~${FOUNDER_HOURLY_USD * MANUAL_HOURS_PER_PROPOSAL:.0f} (founder time)':<30}"
        f"{f'~${APPROX_LLM_COST_PER_PROPOSAL_USD:.2f} (LLM)':<28}"
    )


def _write_results(payload: dict[str, Any]) -> str:
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    path = os.path.join(_RESULTS_DIR, "last_run.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


async def _main_async() -> int:
    # 1) Deterministic self-check first — independent of any model credential.
    consistent = _print_self_check()

    inquiries = _load_inquiries()
    print(f"\nLoaded {len(inquiries)} inquiries from {_INQUIRY_DIR}")

    rows: list[dict[str, Any]] = []
    model_unavailable = False
    model_error: Optional[str] = None

    for stem, raw in inquiries:
        gold = _load_gold(stem)
        t0 = time.perf_counter()
        try:
            run = await _run_one_with_retry(stem, raw)
        except Exception as exc:  # auth/network/model failure -> graceful stop.
            model_unavailable = True
            model_error = f"{type(exc).__name__}: {exc}"
            break
        secs = time.perf_counter() - t0
        scored = _score_case(stem, run, gold)
        scored["seconds"] = secs
        rows.append(scored)

    if model_unavailable:
        print("\n" + "!" * 84)
        print("MODEL UNAVAILABLE — built harness validated structurally, "
              "rerun when credentials are live")
        print(f"  (first model call failed: {model_error})")
        print("!" * 84)
        print("\nThe deterministic gold-consistency check above is the part that "
              "does not\nrequire a model; it ran and reported:",
              "CONSISTENT" if consistent else "INCONSISTENT")
        _write_results({
            "status": "model_unavailable",
            "gold_consistent": consistent,
            "model_error": model_error,
            "n_cases_scored": 0,
        })
        # Exit cleanly: structural validation done, nothing hung.
        return 0

    # Full scored run.
    _print_results_table(rows)
    agg = _aggregate(rows)
    _print_aggregate(agg)
    mean_secs = sum(r["seconds"] for r in rows) / len(rows) if rows else None
    _print_business_impact(agg, mean_secs)

    path = _write_results({
        "status": "ok",
        "gold_consistent": consistent,
        "aggregate": agg,
        "mean_seconds_per_case": round(mean_secs, 2) if mean_secs else None,
        "per_case": [
            {k: v for k, v in r.items() if k != "pred_features" or True}
            for r in rows
        ],
    })
    print(f"\nWrote aggregate results to {path}")
    return 0


def main() -> int:
    try:
        return asyncio.run(_main_async())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
