"""Verify real Google delivery is authorized — creates then deletes a test draft.

Run after authorizing:
    AUTOBRIEF_ENABLE_GOOGLE=1 python -m autobrief.mcp_server.verify_google

It checks each delivery service (Gmail / Calendar / Drive), creates a throwaway
Gmail DRAFT to prove the gmail.compose scope works, then deletes it so nothing
is left behind. Exit 0 = Gmail draft path verified.
"""
from __future__ import annotations

import base64
import os
import sys
from email.mime.text import MIMEText

# Korean Windows consoles default to cp949, which cannot encode characters like
# the em dash; force UTF-8 output so status prints never crash the run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Make the explicit opt-in true for this verification run if the caller forgot.
os.environ.setdefault("AUTOBRIEF_ENABLE_GOOGLE", "1")

from .google_clients import (  # noqa: E402
    get_calendar_service,
    get_drive_service,
    get_gmail_service,
    load_credentials,
)


def main() -> int:
    creds = load_credentials()
    if creds is None:
        print(
            "NOT AUTHORIZED: no usable credentials.\n"
            "Run:  powershell -ExecutionPolicy Bypass -File .\\authorize_google.ps1\n"
            "(or)  gcloud auth application-default login --scopes=...,gmail.compose,...",
            file=sys.stderr,
        )
        return 2

    acct = getattr(creds, "service_account_email", None) or "(user via ADC/token)"
    print(f"Credentials loaded: {acct}")

    gmail = get_gmail_service()
    cal = get_calendar_service()
    drive = get_drive_service()
    print(f"  Gmail service:    {'OK' if gmail else 'unavailable'}")
    print(f"  Calendar service: {'OK' if cal else 'unavailable'}")
    print(f"  Drive service:    {'OK' if drive else 'unavailable'}")

    if gmail is None:
        print("Gmail service unavailable — cannot verify draft path.", file=sys.stderr)
        return 2

    # Create a throwaway draft, then delete it.
    try:
        mime = MIMEText("AutoBrief delivery verification - safe to ignore.", _charset="utf-8")
        mime["to"] = "verify@example.com"
        mime["subject"] = "[AutoBrief] delivery check (auto-deleted)"
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
        created = (
            gmail.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        )
        draft_id = created.get("id")
        print(f"  Created test draft id={draft_id} (gmail.compose scope works)")
        gmail.users().drafts().delete(userId="me", id=draft_id).execute()
        print("  Deleted test draft — cleanup done.")
    except Exception as exc:
        print(f"Gmail draft create/delete failed: {exc}", file=sys.stderr)
        print(
            "Most likely the gmail.compose scope was not granted. Re-run the\n"
            "authorize script and make sure all scopes are checked.",
            file=sys.stderr,
        )
        return 1

    print("\nVERIFIED: real Gmail draft delivery is working.")
    print("Run the agent with: $env:AUTOBRIEF_ENABLE_MCP='1'; $env:AUTOBRIEF_ENABLE_GOOGLE='1'; adk web .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
