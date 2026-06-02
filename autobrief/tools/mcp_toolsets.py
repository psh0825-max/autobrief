"""Factories that wire the AutoBrief Studio MCP server into ADK as toolsets.

Write actions (Gmail draft, calendar event, Drive doc, deck) are gated behind
human-in-the-loop confirmation; the read-only slot suggestion is not. Splitting
into two toolsets keeps the HITL gate precise (the MCP require_confirmation flag
applies to every tool in a toolset).
"""
from __future__ import annotations

import os
import sys

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

_SERVER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "mcp_server", "studio_server.py")
)

# Irreversible / client-facing actions -> always require approval.
WRITE_TOOLS = [
    "create_gmail_draft",
    "create_calendar_event",
    "save_to_drive",
    "generate_proposal_deck",
]
# Safe, read-only helper -> no approval needed.
READ_TOOLS = ["suggest_kickoff_slot"]


def _connection() -> StdioConnectionParams:
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_SERVER_PATH],
        ),
        timeout=20.0,
    )


def studio_write_toolset() -> McpToolset:
    """Studio delivery actions, each gated by human approval (HITL)."""
    return McpToolset(
        connection_params=_connection(),
        tool_filter=WRITE_TOOLS,
        require_confirmation=True,
    )


def studio_read_toolset() -> McpToolset:
    """Read-only studio helpers (no approval needed)."""
    return McpToolset(
        connection_params=_connection(),
        tool_filter=READ_TOOLS,
        require_confirmation=False,
    )


def studio_toolsets() -> list[McpToolset]:
    """Both toolsets, ready to drop into an agent's `tools=` list."""
    return [studio_read_toolset(), studio_write_toolset()]
