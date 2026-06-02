"""Programmatic end-to-end smoke test for the AutoBrief pipeline.

Faster than `adk web` for verification: feeds a sample inquiry through the full
pipeline and prints each agent's output plus the final structured proposal.

Usage:  python smoke_test.py
"""
from __future__ import annotations

import asyncio
import json
import sys

# Windows consoles default to cp949 here; force UTF-8 so em-dashes etc. print.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google.genai import types

from autobrief.agent import root_agent
from autobrief.config import APP_NAME
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

SAMPLE_INQUIRY = """Subject: Need an MVP for a tutoring marketplace

Hi, I'm Sarah Kim, founder of TutorLoop (tutorloop.io). We want to launch an MVP
in about 5 weeks for a marketplace connecting high-school students with vetted
tutors. Students should sign up, search tutors, book and pay for sessions, and
leave reviews. Tutors need a profile and a calendar. We'd love an AI feature that
recommends tutors based on a student's needs. Budget is flexible but lean.
Can you send a proposal? Thanks!
"""


async def main() -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name=APP_NAME, user_id="demo-user", state={}
    )

    message = types.Content(role="user", parts=[types.Part(text=SAMPLE_INQUIRY)])

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=message,
    ):
        author = getattr(event, "author", "?")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(f"\n===== [{author}] =====\n{part.text}")
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    print(f"\n----- [{author}] tool call: {fc.name}({dict(fc.args)})")

    final = await session_service.get_session(
        app_name=APP_NAME, user_id=session.user_id, session_id=session.id
    )
    print("\n\n########## FINAL STATE ##########")
    for key in ("inquiry", "research", "estimate", "estimate_summary", "proposal"):
        val = final.state.get(key)
        print(f"\n--- state['{key}'] ---")
        if isinstance(val, (dict, list)):
            print(json.dumps(val, indent=2, ensure_ascii=False))
        else:
            print(val)


if __name__ == "__main__":
    asyncio.run(main())
