"""Central configuration for AutoBrief.

Importing this module normalizes the environment so the rest of the package
can run identically in local (Google AI Studio) and Vertex AI modes.
"""
from __future__ import annotations

import os

# --- TLS: trust the OS certificate store ------------------------------------
# Corporate TLS inspection (e.g. Norton) re-signs HTTPS with a local root CA
# that is in the Windows trust store but not in certifi's bundle, which breaks
# the genai SDK's aiohttp calls. truststore makes Python use the OS store.
try:  # pragma: no cover - environment dependent
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

# --- Auth normalization -----------------------------------------------------
USE_VERTEX = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "0").lower() in ("1", "true", "yes")

if USE_VERTEX:
    # Vertex AI uses Application Default Credentials, not an API key. Drop any
    # API keys so the SDK doesn't warn or accidentally fall back to AI Studio.
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
else:
    # AI Studio path: the SDK reads GOOGLE_API_KEY. Map GEMINI_API_KEY over if
    # that's the only one set.
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")

# --- Model tiers ------------------------------------------------------------
# Overridable via env so a live demo can downgrade Pro -> Flash under rate limits.
FLASH = os.environ.get("AUTOBRIEF_FLASH_MODEL", "gemini-2.5-flash")
FLASH_LITE = os.environ.get("AUTOBRIEF_FLASH_LITE_MODEL", "gemini-2.5-flash-lite")
PRO = os.environ.get("AUTOBRIEF_PRO_MODEL", "gemini-2.5-pro")

APP_NAME = "autobrief"

# --- Feature flags ----------------------------------------------------------
# When MCP servers are not wired (e.g. unauthenticated CI), the delivery agent
# falls back to printing drafts instead of calling MCP tools.
ENABLE_MCP = os.environ.get("AUTOBRIEF_ENABLE_MCP", "0").lower() in ("1", "true", "yes")
