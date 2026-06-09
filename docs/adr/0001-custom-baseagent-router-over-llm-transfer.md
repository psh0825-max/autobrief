# 0001. Custom BaseAgent router instead of ADK LLM transfer

- Status: Accepted
- Date: 2026-06-09
- Deciders: Repo owner

## Context
AutoBrief must triage each inbound inquiry into one of three branches — proceed,
need_clarification, or decline — and then run the matching flow. ADK 2.1.0's
idiomatic mechanism for this is an `LlmAgent` using `transfer_to_agent`. In
practice that path crashes: an `LlmAgent` that has a `SequentialAgent` peer fails
while computing transfer targets (`'SequentialAgent' object has no attribute 'mode'`).
The triage also needs to be cheap to evaluate and trace deterministically.

## Decision
We will implement triage as a custom `AutoBriefRouter(BaseAgent)` that orchestrates
explicitly: it runs a `RouterClassifier` to write `state['routing']`, then branches
in plain Python to the pipeline, clarifier, or decline agent. Unknown or unparseable
decisions fall through to the safe option (decline) rather than spending the full
pipeline. (`autobrief/router.py`)

## Alternatives considered
- **ADK `LlmAgent` + `transfer_to_agent`** — the idiomatic approach, but crashes in
  2.1.0 when a `SequentialAgent` is a peer; also harder to evaluate deterministically.
- **Flatten everything into one SequentialAgent with internal guards** — would run
  scope/proposal work even for inquiries that should decline; wasteful and less clear.

## Consequences
- Positive: deterministic, traceable branching; eval-friendly; safe default on bad parses.
- Negative / trade-offs: we hand-wire orchestration instead of using the framework's
  LLM transfer, so we own the branching logic.
- Follow-ups: revisit if a later ADK release fixes LLM transfer with Sequential peers.
