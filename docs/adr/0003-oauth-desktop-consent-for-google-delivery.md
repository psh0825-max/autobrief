# 0003. OAuth Desktop-app consent for real Google delivery

- Status: Accepted
- Date: 2026-06-09
- Deciders: Repo owner

## Context
AutoBrief's delivery tools need to create real Gmail drafts, Calendar events, and
Drive docs on the founder's own Google account. This is a single-operator tool, not a
multi-tenant service, and no credential may ever land in the git repo. Norton's local
TLS interception on the dev machine also complicates anything touching HTTPS.

## Decision
We will authorize delivery with a **one-time OAuth 2.0 Desktop-app consent flow**: the
founder runs `python -m autobrief.mcp_server.google_auth` once, which opens a browser,
obtains a refresh-capable token, and writes it to a gitignored
`.google_token.json`. The OAuth client secret and the token file are both gitignored
and never committed. Real delivery activates only when `AUTOBRIEF_ENABLE_GOOGLE=1`;
otherwise the tools return local stubs. (`autobrief/mcp_server/google_auth.py`)

## Alternatives considered
- **Service account + domain-wide delegation** — heavier to set up, oriented at
  workspace-wide impersonation; overkill for a single-operator demo.
- **Paste API keys / tokens into config or env files in the repo** — rejected outright;
  secret-leak risk.

## Consequences
- Positive: no secrets in the repo; minimal setup; refresh token survives restarts;
  delivery is opt-in behind a flag, so eval/demo stays keyless.
- Negative / trade-offs: requires a manual one-time browser consent per machine; tied
  to the founder's personal account rather than a service identity.
- Follow-ups: revisit a service-account path if AutoBrief ever needs to act for
  multiple users.
