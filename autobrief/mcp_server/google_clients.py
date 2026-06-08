"""Real Google API plumbing for the Studio MCP server.

This module turns the studio's delivery tools from local stubs into *real*
Gmail / Google Calendar / Google Drive actions — while degrading gracefully:
if no OAuth token is present, ``get_*_service()`` returns ``None`` and the
caller falls back to the offline ``outbox/`` stub. That keeps the eval harness
and the no-network demo working unchanged, and makes the real integration a
drop-in once the founder authorizes once (see ``google_auth.py``).

Credential model
----------------
User-data APIs (Gmail/Calendar/Drive) require OAuth *user* consent, not a
service account. We use the installed-app flow:

  1. Founder runs ``python -m autobrief.mcp_server.google_auth`` once.
  2. That writes a cached token (refresh-capable) to ``AUTOBRIEF_GOOGLE_TOKEN``.
  3. From then on this module loads + auto-refreshes that token; no browser.

Scopes are intentionally minimal:
  * gmail.compose  — create DRAFTS only (cannot send mail).
  * calendar.events — create/read events.
  * drive.file     — only files this app creates (no broad Drive access).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional

# Minimal scopes. gmail.compose deliberately cannot *send* — only draft.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.file",
]

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# Cached OAuth token (refresh token). Override with AUTOBRIEF_GOOGLE_TOKEN.
DEFAULT_TOKEN_PATH = os.path.join(_MODULE_DIR, ".google_token.json")
# OAuth *client* (Desktop app) credentials downloaded from GCP console.
DEFAULT_CLIENT_SECRETS_PATH = os.path.join(_MODULE_DIR, ".google_client_secret.json")


def token_path() -> str:
    return os.environ.get("AUTOBRIEF_GOOGLE_TOKEN", DEFAULT_TOKEN_PATH)


def client_secrets_path() -> str:
    return os.environ.get("AUTOBRIEF_GOOGLE_CLIENT_SECRET", DEFAULT_CLIENT_SECRETS_PATH)


def google_enabled() -> bool:
    """True only if real Google delivery is both requested and possible.

    Requires AUTOBRIEF_ENABLE_GOOGLE=1 *and* a token file present. This is an
    explicit opt-in so eval / offline demos never accidentally hit the network.
    """
    if os.environ.get("AUTOBRIEF_ENABLE_GOOGLE", "0") not in ("1", "true", "True"):
        return False
    return os.path.exists(token_path())


@lru_cache(maxsize=1)
def load_credentials() -> Optional[Any]:
    """Load + refresh cached OAuth user credentials, or None if unavailable.

    Never raises — any failure (missing libs, missing/invalid token, refresh
    error) returns None so the caller falls back to the local stub.
    """
    if not google_enabled():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(token_path(), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist the refreshed token so the next process reuses it.
            with open(token_path(), "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())
        if creds and creds.valid:
            return creds
        return None
    except Exception:
        return None


@lru_cache(maxsize=3)
def _service(api: str, version: str) -> Optional[Any]:
    creds = load_credentials()
    if creds is None:
        return None
    try:
        from googleapiclient.discovery import build

        return build(api, version, credentials=creds, cache_discovery=False)
    except Exception:
        return None


def get_gmail_service() -> Optional[Any]:
    return _service("gmail", "v1")


def get_calendar_service() -> Optional[Any]:
    return _service("calendar", "v3")


def get_drive_service() -> Optional[Any]:
    return _service("drive", "v3")
