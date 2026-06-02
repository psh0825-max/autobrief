"""ADK entrypoint. `adk web` / `adk api_server` discover `root_agent` here."""
from __future__ import annotations

from . import config  # noqa: F401  (normalizes env: GEMINI_API_KEY -> GOOGLE_API_KEY)
from .pipeline import autobrief_pipeline

# For Day 1 the pipeline is the root. A proceed/clarify/decline router is layered
# on top in a later step.
root_agent = autobrief_pipeline
