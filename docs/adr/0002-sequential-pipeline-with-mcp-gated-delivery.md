# 0002. Sequential reasoning spine with MCP-gated delivery

- Status: Accepted
- Date: 2026-06-09
- Deciders: Repo owner

## Context
The core of AutoBrief is a reproducible flow: intake -> research -> scope/estimate ->
proposal. Real delivery (Gmail draft / Calendar event / Drive doc) is also wanted, but
those tools are human-in-the-loop (HITL) gated and pause for approval — which would
stall a headless evaluation run. We need one architecture that serves both the
deterministic demo/eval path and the interactive/deployed path.

## Decision
We will model the reasoning spine as a `SequentialAgent` (`AutoBriefPipeline`) of four
sub-agents, and append the HITL-gated delivery agent to the stage list **only when
`ENABLE_MCP` is on**. State flows implicitly between stages via `output_key`. The eval
path (MCP off) stops at the proposal; interactive runs continue to delivery.
(`autobrief/pipeline.py`)

## Alternatives considered
- **Always include delivery** — would stall headless eval on the HITL approval pause.
- **A newer ADK composition primitive instead of SequentialAgent** — `SequentialAgent`
  is deprecated in 2.1.0 but still functional and gives the simplest reproducible flow;
  migrating now adds risk for no demo-stage benefit.

## Consequences
- Positive: one codebase serves both eval and interactive; eval stays fully automated.
- Negative / trade-offs: depends on a deprecated primitive (`SequentialAgent`); a
  DeprecationWarning is suppressed at import.
- Follow-ups: migrate off `SequentialAgent` when a stable replacement is adopted.
