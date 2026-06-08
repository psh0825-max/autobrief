"""AutoBrief Studio MCP server — a well-defined tool server for delivery actions.

This is a custom Model Context Protocol (stdio) server exposing the studio's
client-facing "delivery" actions as clean, typed tools. It is intentionally
self-contained and demoable: every action writes a real artifact under
``outbox/`` so the agent's work is visible without any external OAuth setup.

Each write tool returns a short receipt string. Swapping the stub bodies for the
real Gmail / Google Calendar / Google Drive / Canva APIs is a localized change
(see the TODO markers) — the tool *contract* the agent sees stays identical.

Run standalone:  python autobrief/mcp_server/studio_server.py
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import re
from email.mime.text import MIMEText

from mcp.server.fastmcp import FastMCP

# This module is launched as a standalone script (see tools/mcp_toolsets.py),
# so a package-relative import won't resolve. Try relative first (when imported
# as part of the package), then fall back to the sibling module on sys.path.
try:
    from .google_clients import (  # type: ignore
        get_calendar_service,
        get_drive_service,
        get_gmail_service,
    )
except ImportError:  # run as `python studio_server.py`
    from google_clients import (  # type: ignore
        get_calendar_service,
        get_drive_service,
        get_gmail_service,
    )

# outbox lives at the repo root (…/autobrief/outbox)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTBOX = os.path.join(_REPO_ROOT, "outbox")

mcp = FastMCP("autobrief-studio")


def _ensure(subdir: str) -> str:
    path = os.path.join(OUTBOX, subdir)
    os.makedirs(path, exist_ok=True)
    return path


def _slug(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s or "untitled")[:maxlen]


def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@mcp.tool()
def create_gmail_draft(to: str, subject: str, body: str) -> str:
    """Create a Gmail DRAFT reply to the client (never auto-sends).

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.

    Returns:
        A receipt with the local draft id/path. The draft is NOT sent.
    """
    # Always keep a local audit copy (offline demo + traceability).
    folder = _ensure("drafts")
    draft_id = f"draft-{_stamp()}"
    path = os.path.join(folder, f"{draft_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"to": to, "subject": subject, "body": body}, fh, ensure_ascii=False, indent=2)

    gmail = get_gmail_service()
    if gmail is not None:
        try:
            mime = MIMEText(body, _charset="utf-8")
            mime["to"] = to
            mime["subject"] = subject
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
            created = (
                gmail.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            gid = created.get("id", "?")
            # gmail.compose scope can create drafts but NOT send — send is
            # structurally impossible with these credentials.
            return (
                f"REAL Gmail draft created (NOT sent): id={gid} -> to={to!r}, "
                f"subject={subject!r}. Review at https://mail.google.com/mail/u/0/#drafts "
                f"(local audit copy: {path})"
            )
        except Exception as exc:  # fall back to the local stub on any API error
            return (
                f"Gmail API unavailable ({exc!s:.120}); saved LOCAL draft "
                f"{draft_id} -> to={to!r}, subject={subject!r}. Saved at {path}"
            )

    return f"Draft created (NOT sent, local): {draft_id} -> to={to!r}, subject={subject!r}. Saved at {path}"


@mcp.tool()
def create_calendar_event(title: str, start_iso: str, duration_minutes: int, attendee: str) -> str:
    """Create a TENTATIVE kickoff calendar event.

    Args:
        title: Event title.
        start_iso: ISO-8601 start datetime (e.g. "2026-06-10T10:00:00").
        duration_minutes: Event length in minutes.
        attendee: Attendee email.

    Returns:
        A receipt with the local event id/path.
    """
    folder = _ensure("calendar")
    event_id = f"evt-{_stamp()}"
    path = os.path.join(folder, f"{event_id}.json")
    record = {
        "title": title,
        "start": start_iso,
        "duration_minutes": duration_minutes,
        "attendee": attendee,
        "status": "tentative",
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)

    cal = get_calendar_service()
    if cal is not None:
        try:
            start_dt = datetime.datetime.fromisoformat(start_iso)
            end_dt = start_dt + datetime.timedelta(minutes=int(duration_minutes))
            body = {
                "summary": title,
                "start": {"dateTime": start_dt.isoformat()},
                "end": {"dateTime": end_dt.isoformat()},
                "attendees": [{"email": attendee}],
                "status": "tentative",
            }
            created = (
                cal.events()
                # sendUpdates="none": the client is NOT emailed automatically;
                # the founder reviews/sends after approval (no auto-notify).
                .insert(calendarId="primary", body=body, sendUpdates="none")
                .execute()
            )
            link = created.get("htmlLink", "(no link)")
            return (
                f"REAL tentative event '{title}' at {start_iso} ({duration_minutes}m) "
                f"for {attendee} (no invite sent). {link} (local audit copy: {path})"
            )
        except Exception as exc:
            return (
                f"Calendar API unavailable ({exc!s:.120}); saved LOCAL event "
                f"'{title}' at {start_iso}. Saved at {path}"
            )

    return f"Tentative event (local) '{title}' at {start_iso} ({duration_minutes}m) for {attendee}. Saved at {path}"


@mcp.tool()
def save_to_drive(title: str, markdown: str) -> str:
    """Save a document (brief or proposal) to the studio Drive as markdown.

    Args:
        title: Document title (used for the filename).
        markdown: Full markdown content.

    Returns:
        A receipt with a Drive-style URL and the local path.
    """
    folder = _ensure("drive")
    name = f"{_slug(title)}.md"
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown)

    drive = get_drive_service()
    if drive is not None:
        try:
            from googleapiclient.http import MediaInMemoryUpload

            media = MediaInMemoryUpload(
                markdown.encode("utf-8"), mimetype="text/markdown", resumable=False
            )
            # Convert to a native Google Doc so it's readable in Drive.
            meta = {"name": title, "mimeType": "application/vnd.google-apps.document"}
            created = (
                drive.files()
                .create(body=meta, media_body=media, fields="id,webViewLink")
                .execute()
            )
            link = created.get("webViewLink", "(no link)")
            return f"REAL Drive doc saved: '{title}' -> {link} (local audit copy: {path})"
        except Exception as exc:
            return (
                f"Drive API unavailable ({exc!s:.120}); saved LOCAL doc "
                f"'{title}' at {path}"
            )

    return f"Saved to Drive (local): '{title}' -> {path}"


@mcp.tool()
def generate_proposal_deck(title: str, bullets: list[str]) -> str:
    """Generate a simple proposal deck (HTML slides) from a title and bullets.

    Args:
        title: Deck title.
        bullets: Slide bullet points (one slide per bullet group line).

    Returns:
        A receipt with the deck URL and local path.
    """
    folder = _ensure("decks")
    name = f"{_slug(title)}.html"
    path = os.path.join(folder, name)
    slides = "\n".join(f"<section><h2>{b}</h2></section>" for b in bullets)
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
        "<style>section{padding:6vh 8vw;border-bottom:1px solid #eee;font-family:sans-serif}"
        "h1{font-family:sans-serif;padding:6vh 8vw}</style></head>"
        f"<body><h1>{title}</h1>{slides}</body></html>"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    # TODO(real): Canva MCP generate-design-structured + export-design.
    return f"Deck generated: '{title}' ({len(bullets)} slides) -> https://canva.example/{name} (local: {path})"


@mcp.tool()
def suggest_kickoff_slot(after_iso: str | None = None) -> str:
    """Suggest the next Tuesday or Thursday 10:00 kickoff slot (read-only).

    Args:
        after_iso: Optional ISO date to search after; defaults to today.

    Returns:
        An ISO-8601 datetime string for the proposed kickoff.
    """
    if after_iso:
        base = datetime.date.fromisoformat(after_iso[:10])
    else:
        base = datetime.date.today()
    # Tuesday=1, Thursday=3 (Mon=0)
    for delta in range(1, 9):
        day = base + datetime.timedelta(days=delta)
        if day.weekday() in (1, 3):
            return datetime.datetime(day.year, day.month, day.day, 10, 0, 0).isoformat()
    return datetime.datetime(base.year, base.month, base.day, 10, 0, 0).isoformat()


if __name__ == "__main__":
    mcp.run()
