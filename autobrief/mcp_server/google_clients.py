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
service account. Two ways to authorize, tried in this order:

  A. gcloud ADC (easiest — no GCP-console OAuth client to create):
        gcloud auth application-default login --scopes=<...gmail/cal/drive...>
     One browser consent; this module then picks up the ADC credentials
     automatically via ``google.auth.default``.

  B. Installed-app token file (isolated, no gcloud):
        python -m autobrief.mcp_server.google_auth   (writes AUTOBRIEF_GOOGLE_TOKEN)

Scopes are intentionally minimal:
  * gmail.compose  — create DRAFTS only (cannot send mail).
  * calendar.events — create/read events.
  * drive.file     — only files this app creates (no broad Drive access).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional

# --- TLS: trust the OS certificate store ------------------------------------
# The MCP server runs as its own subprocess (and the verifier as its own
# process), so neither imports autobrief.config — they don't inherit its
# truststore injection. Corporate TLS inspection re-signs HTTPS with a local
# root CA that lives in the Windows store but not certifi's bundle; without
# this, requests/httplib2 calls to googleapis.com fail cert verification.
try:  # pragma: no cover - environment dependent
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

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
    """True only if real Google delivery has been explicitly requested.

    Requires AUTOBRIEF_ENABLE_GOOGLE=1. This is an explicit opt-in so eval /
    offline demos never accidentally hit the network. Whether usable credentials
    actually exist is decided by ``load_credentials`` (returns None -> stub).
    """
    return os.environ.get("AUTOBRIEF_ENABLE_GOOGLE", "0") in ("1", "true", "True")


def _load_token_credentials() -> Optional[Any]:
    """Installed-app flow: load + refresh the cached token file, or None."""
    if not os.path.exists(token_path()):
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(token_path(), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path(), "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())
        return creds if (creds and creds.valid) else None
    except Exception:
        return None


def _load_adc_credentials() -> Optional[Any]:
    """gcloud ADC: pick up `application-default login` credentials, or None.

    The user's ADC scopes are fixed at login time, so they must have run
    `gcloud auth application-default login --scopes=...` including the Gmail /
    Calendar / Drive scopes. If a scope is missing the API call later 403s and
    the tool falls back to the stub — never crashes.
    """
    try:
        from google.auth import default as adc_default
        from google.auth.transport.requests import Request

        creds, _ = adc_default(scopes=SCOPES)
        if creds and not creds.valid and getattr(creds, "refresh_token", None):
            creds.refresh(Request())
        return creds
    except Exception:
        return None


def delegated_user() -> str:
    """The Workspace user the delivery actions act as (DWD subject)."""
    return os.environ.get("AUTOBRIEF_DELEGATED_USER", "support@lightonpluslab.com")


def dwd_service_account() -> str:
    """Service account used for domain-wide delegation (keyless impersonation)."""
    return os.environ.get(
        "AUTOBRIEF_DWD_SA",
        "autobrief-delivery@lightonplus-apps.iam.gserviceaccount.com",
    )


def _load_dwd_credentials() -> Optional[Any]:
    """Keyless domain-wide delegation — impersonate ``delegated_user()``.

    No service-account key file (org policy blocks key creation). Instead we use
    the local ADC to call IAM Credentials ``signJwt`` on the delivery SA, minting
    a delegated JWT (sub = the Workspace user), then exchange it for an access
    token scoped to Gmail/Calendar/Drive.

    Prerequisites (one-time):
      1. Local ADC present (``gcloud auth application-default login``).
      2. The ADC principal has ``roles/iam.serviceAccountTokenCreator`` on the SA.
      3. The SA's client id is authorized for SCOPES in the Workspace Admin
         console (Security → API controls → Domain-wide delegation).

    Returns None (→ stub fallback) on any failure, e.g. DWD not yet authorized.
    """
    sa_email = dwd_service_account()
    if not sa_email:
        return None
    try:
        import datetime
        import json as _json

        import requests
        from google.auth import credentials as ga_credentials
        from google.auth import default as adc_default
        from google.auth.transport.requests import AuthorizedSession, Request

        subject = delegated_user()
        scope_str = " ".join(SCOPES)
        sign_url = (
            "https://iamcredentials.googleapis.com/v1/"
            f"projects/-/serviceAccounts/{sa_email}:signJwt"
        )

        class _Dwd(ga_credentials.Credentials):
            def refresh(self, request):  # noqa: D401
                source, _ = adc_default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                payload = _json.dumps(
                    {
                        "iss": sa_email,
                        "sub": subject,
                        "scope": scope_str,
                        "aud": "https://oauth2.googleapis.com/token",
                        "iat": now,
                        "exp": now + 3600,
                    }
                )
                signed = AuthorizedSession(source).post(
                    sign_url, json={"payload": payload}, timeout=20
                )
                signed.raise_for_status()
                assertion = signed.json()["signedJwt"]
                tok = requests.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                    timeout=20,
                )
                tok.raise_for_status()
                body = tok.json()
                self.token = body["access_token"]
                self.expiry = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=int(body.get("expires_in", 3600)) - 60
                )

        creds = _Dwd()
        creds.refresh(Request())
        return creds if creds.token else None
    except Exception:
        return None


@lru_cache(maxsize=1)
def load_credentials() -> Optional[Any]:
    """Resolve delivery credentials, or None if unavailable.

    Order: explicit token file (installed-app) → keyless domain-wide delegation
    → plain gcloud ADC. Never raises — any failure returns None so the caller
    falls back to the local stub.
    """
    if not google_enabled():
        return None
    return (
        _load_token_credentials()
        or _load_dwd_credentials()
        or _load_adc_credentials()
    )


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
