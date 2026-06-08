# AutoBrief — Challenge Submission Package (copy-paste ready)

> Google for Startups AI Agents Challenge · **Track 1 (new autonomous agent)**.
> Fill the submission form with the blocks below. Deadline: **2026-06-05 17:00**.

---

## Required links

| Field | Value |
|---|---|
| **Deployed URL** | https://autobrief-g36me2m3ca-uc.a.run.app/dev-ui/?app=autobrief |
| **GitHub repo** | https://github.com/psh0825-max/autobrief |
| **Demo video** | https://storage.googleapis.com/lightonplus-apps-autobrief-demo/autobrief-demo.mp4 (2:26, narrated) |
| **Track** | Track 1 — build a new autonomous agent |

---

## Project name
**AutoBrief**

## One-line tagline
Autonomous client-intake & proposal agent that turns an inbound inquiry into a scoped, priced, human-approved proposal for a solo AI MVP studio.

## Short description (≈100 words)
AutoBrief is a multi-agent system (Google ADK + Gemini on Vertex AI) for LightOn Plus Lab, a one-person AI-MVP studio. A raw client email goes in; AutoBrief triages it (proceed / clarify / decline), extracts a structured brief, researches the client with cited web search, classifies the project and prices it with a **deterministic rubric** (never the LLM), writes a client-ready proposal, and — only after human approval — drafts the reply email, a kickoff calendar invite, a Drive doc, and a proposal deck. It collapses 3–5 hours of unbilled intake into ~1 minute of compute plus a quick review, and scores 100% on routing, scope, and price-in-band across an 8-case eval.

## Problem & business case
A solo studio's revenue bottleneck isn't building — it's *winning* the work. Every inbound inquiry is 3–5 hours of reading, researching, scoping, pricing, and proposal-writing before any contract, capping the founder at ~3–4 serious inquiries/day. AutoBrief automates that funnel end-to-end with a human-approval gate on anything client-facing, and is directly resellable as SaaS to other agencies with the same bottleneck.

## How it works (technical)
- **Architecture:** a triage `LlmAgent` (RouterClassifier, structured `output_schema` verdict) drives a custom `BaseAgent` orchestrator that runs one of three branches: a `SequentialAgent` pipeline (IntakeParser → Researcher[`google_search`] → ScoperEstimator → ProposalWriter → DeliveryAgent), a ClarifierAgent, or a DeclineAgent. State is handed off via `output_key` + instruction templating.
- **Model tiers:** flash-lite (clarify/decline) · flash (triage/intake/research/scope) · pro (proposal prose). Config-overridable for live rate-limit fallback.
- **Deterministic pricing:** the LLM only classifies (archetype, feature add-ons, complexity, rush); all dollar/timeline math is a Python tool over `rubric.yaml`. Prices are reproducible and auditable — no hallucinated quotes.
- **Custom MCP server:** a self-contained Studio MCP server exposes the 5 delivery actions as typed tools; swapping stubs for real Gmail/Calendar/Drive/Canva APIs is a localized change.
- **Guardrails:** HITL `require_confirmation` on every write action (verified: all 4 write tools gate, the read-only slot helper doesn't); Gmail only ever *drafts* (no auto-send); proposal price must equal the rubric output; PII redaction before research; prompt-injection framing (inbound email treated as untrusted data).
- **Observability:** Cloud Run + Cloud Trace/Logging — every step, tool call, and HITL pause is traced.

## Evaluation results (scored on Vertex AI, 8 gold-labeled inquiries)
| Metric | Result |
|---|---|
| Routing accuracy (proceed/clarify/decline) | **100%** (8/8) |
| Archetype accuracy | **100%** |
| Scope accuracy (mean feature-key Jaccard) | **1.0** |
| Price-in-band (±15% band overlap) | **100%** |
| Tool-trajectory valid (zero un-approved sends) | **100%** |
| Mean time per case | ~66 s |

### Before / after
| Metric | Manual (founder) | AutoBrief |
|---|---|---|
| Time to first proposal | ~3–5 hours | ~1 min compute + quick review |
| Inquiries/day | ~3–4 | dozens (compute-bound) |
| Scope accuracy | (baseline) | 1.0 mean Jaccard |
| Price-in-band | — | 100% |
| Cost/proposal | ~$480 (founder time) | ~$0.05 (LLM) |

## Tech stack
Google ADK 2.1.0 · Gemini 2.5 (pro/flash/flash-lite) on Vertex AI · Model Context Protocol (custom stdio server) · Cloud Run (`--with_ui`) · Cloud Trace/Logging · Python 3.12 / Pydantic.

---

## Demo-day checklist (before recording / before judging)
1. Service warm: `min-instances=1` is set (already). Open https://autobrief-g36me2m3ca-uc.a.run.app/dev-ui/?app=autobrief
2. To show the **HITL approval gates live**, either:
   - run locally: `AUTOBRIEF_ENABLE_MCP=1 adk web C:\Users\rnd\autobrief` (UI surfaces Approve/Reject for each write tool), **or**
   - enable on the deployed service: `gcloud run services update autobrief --region=us-central1 --update-env-vars=AUTOBRIEF_ENABLE_MCP=1` (revert with `--remove-env-vars=AUTOBRIEF_ENABLE_MCP`).
3. Three inquiries to paste (from `eval/inquiries/`): `01_crud_saas_clean.txt` (proceed), `06_vague_clarify.txt` (clarify), `08_out_of_scope_decline.txt` (decline).
4. Record per `docs/demo_script.md`; show the Cloud Trace view in the console.
5. After the demo, to cut cost: `gcloud run services update autobrief --region=us-central1 --min-instances=0`.
