"""Generate sample demo outputs for three representative inquiries.

Runs proceed / clarify / decline cases through root_agent on Vertex and writes
judge-facing sample artifacts to docs/demo_outputs/. Not part of the package;
a one-off helper (kept in the repo root, ignorable).
"""
from __future__ import annotations

import asyncio
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from autobrief.agent import root_agent
from autobrief.config import APP_NAME

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "docs", "demo_outputs")
INQ = os.path.join(REPO, "eval", "inquiries")
FENCE = "```"

CASES = [
    ("01_crud_saas_clean", "proceed"),
    ("06_vague_clarify", "clarify"),
    ("08_out_of_scope_decline", "decline"),
]


async def run_one(stem: str) -> tuple[str, dict]:
    ss = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=ss)
    s = await ss.create_session(app_name=APP_NAME, user_id="demo", state={})
    inq = open(os.path.join(INQ, f"{stem}.txt"), encoding="utf-8").read()
    msg = types.Content(role="user", parts=[types.Part(text=inq)])
    async for _ in runner.run_async(user_id=s.user_id, session_id=s.id, new_message=msg):
        pass
    f = await ss.get_session(app_name=APP_NAME, user_id=s.user_id, session_id=s.id)
    return inq, dict(f.state)


def fmt_proceed(st: dict) -> str:
    est = st.get("estimate") or {}
    prop = st.get("proposal") or {}
    lines = [li for li in est.get("line_items", [])]
    items = "\n".join(
        f"  - {li['label']}: {li['days']}d, ${li['price_usd']:,}" for li in lines
    )
    return (
        "## Deterministic estimate (from rubric.yaml — the LLM never prices)\n\n"
        f"- archetype: **{est.get('archetype')}**\n"
        f"- line items:\n{items}\n"
        f"- price band: **${est.get('price_band_low_usd'):,} - ${est.get('price_band_high_usd'):,}**\n"
        f"- timeline: **{est.get('week_low')}-{est.get('week_high')} weeks** "
        f"| confidence {est.get('confidence')}\n\n"
        f"## Proposal — price band verbatim from the estimate: "
        f"{prop.get('price_band_usd')}, {prop.get('timeline_weeks')}\n\n"
        f"{prop.get('proposal_markdown', '')}\n\n"
        "---\n\n### Reply email draft (created as a draft only — never auto-sent)\n\n"
        f"**Subject:** {prop.get('reply_email_subject', '')}\n\n"
        f"{prop.get('reply_email_body', '')}\n"
    )


async def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for stem, kind in CASES:
        inq, st = await run_one(stem)
        routing = st.get("routing") or {}
        decision = routing.get("decision")
        decision = getattr(decision, "value", decision)
        body = [
            f"# Demo output — {stem}  (routed: **{decision}**)\n",
            "## Inbound inquiry\n",
            f"{FENCE}\n{inq.strip()}\n{FENCE}\n",
        ]
        if kind == "proceed":
            body.append(fmt_proceed(st))
        elif kind == "clarify":
            body.append("## Clarifying reply draft\n\n" + (st.get("clarification") or "") + "\n")
        else:
            body.append("## Polite decline reply\n\n" + (st.get("decline_reply") or "") + "\n")
        path = os.path.join(OUT, f"{stem}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(body))
        print("wrote", path, "| routed", decision)


if __name__ == "__main__":
    asyncio.run(main())
