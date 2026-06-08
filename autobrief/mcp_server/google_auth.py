"""One-time OAuth bootstrap for real Gmail / Calendar / Drive delivery.

Run this ONCE on the founder's machine to authorize AutoBrief's delivery tools:

    python -m autobrief.mcp_server.google_auth

Prerequisites
-------------
1. In Google Cloud console, create an OAuth 2.0 Client ID of type
   **Desktop app**, download the JSON, and save it as
   ``autobrief/mcp_server/.google_client_secret.json``
   (or point AUTOBRIEF_GOOGLE_CLIENT_SECRET at it).
2. Make sure the Gmail, Calendar, and Drive APIs are enabled on that project.

What it does
------------
Opens a browser for consent, then writes a refresh-capable token to
``AUTOBRIEF_GOOGLE_TOKEN`` (default ``autobrief/mcp_server/.google_token.json``).
After this, set ``AUTOBRIEF_ENABLE_GOOGLE=1`` and the Studio MCP server's
delivery tools create REAL drafts/events/docs instead of local stubs.

Both the client-secret and token files are gitignored — they are never committed.
"""
from __future__ import annotations

import sys

from .google_clients import SCOPES, client_secrets_path, token_path


def main() -> int:
    import os

    secrets = client_secrets_path()
    if not os.path.exists(secrets):
        print(
            "ERROR: OAuth client secret not found at:\n"
            f"  {secrets}\n\n"
            "Create an OAuth 2.0 Client ID (Desktop app) in the Google Cloud\n"
            "console, download the JSON, and save it to that path (or set\n"
            "AUTOBRIEF_GOOGLE_CLIENT_SECRET).",
            file=sys.stderr,
        )
        return 2

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "ERROR: google-auth-oauthlib is required for the one-time consent.\n"
            "  pip install google-auth-oauthlib",
            file=sys.stderr,
        )
        return 2

    flow = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES)
    # Opens a local browser; falls back to console flow on headless machines.
    creds = flow.run_local_server(port=0)

    out = token_path()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    print(f"OK: authorized. Token saved to {out}")
    print("Now run delivery with: AUTOBRIEF_ENABLE_MCP=1 AUTOBRIEF_ENABLE_GOOGLE=1 adk web .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
