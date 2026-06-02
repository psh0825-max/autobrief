# AutoBrief — Submission Narrative

> Google for Startups AI Agents Challenge · Track 1 (new autonomous agent) ·
> Built on Google ADK + Vertex AI.

## The problem (business case)

LightOn Plus Lab is a **one-person AI MVP studio** in Anyang, Korea. It ships
focused web/mobile MVPs in 2–6 weeks. For a solo founder, the binding constraint
on revenue isn't building — it's **winning the work**. Every inbound inquiry
demands 3–5 hours of unbilled work before any contract: read the email, research
the client, decide whether it's even a fit, classify the project, scope it, price
it without under- or over-quoting, and write a credible proposal. At ~3–4 serious
inquiries a day that a founder can realistically handle, intake *is* the ceiling.

## What AutoBrief does

AutoBrief is an autonomous **client-intake & proposal agent**. Drop a raw inquiry
email in, and it:

1. **Triages** — proceed, ask for clarification, or politely decline (out-of-scope).
2. **Parses** the email into a structured `ClientInquiry`, flagging what's missing.
3. **Researches** the client and market with grounded, cited web search.
4. **Scopes & prices** — the LLM only *classifies* (archetype, features, complexity,
   rush); a **deterministic rubric** does every dollar of the math.
5. **Writes** a product brief and a client-ready proposal (Pro-tier prose).
6. **Delivers** — after a human approves, drafts the reply email, a kickoff calendar
   invite, a Drive doc, and a proposal deck. **Nothing is ever sent automatically.**

It turns a 3–5 hour ritual into a few minutes of compute plus a quick review, and
it's directly sellable as SaaS to other agencies with the same bottleneck.

## Why it's a strong agent (technical)

- **Multi-agent ADK design** — a triage `LlmAgent` router over a `SequentialAgent`
  pipeline, with state handed off idiomatically via `output_key` / instruction
  templating. Model tiers are matched to the job (flash-lite → flash → pro) and are
  config-overridable so a live demo can downgrade under rate limits.
- **Deterministic where it matters** — pricing is pulled out of the model entirely.
  This is the single most important design choice: it makes the agent *trustworthy*
  to put in front of clients, because quotes are reproducible and auditable.
- **Custom MCP server** — a self-contained Studio MCP server exposes the five
  delivery actions as clean typed tools; swapping the stubs for the real
  Gmail/Calendar/Drive/Canva APIs is a localized change with an unchanged contract.
- **Real guardrails** — HITL approval on every irreversible action, no-auto-send by
  construction, price-consistency enforcement, PII redaction, prompt-injection
  framing.
- **Observability** — deployed on Cloud Run with Cloud Trace/Logging, so every
  agent step, tool call, and HITL pause is visible.
- **Honest evaluation** — 8 gold-labeled inquiries and deterministic scorers, run
  end-to-end on Vertex (below).

## Evaluation results

<!-- METRICS:BEGIN -->
Scored end-to-end on Vertex AI across all 8 gold-labeled inquiries:

| Metric | Result |
|---|---|
| Routing accuracy (proceed/clarify/decline) | **100%** (8/8) |
| Archetype accuracy | **100%** |
| Scope accuracy (mean feature-key Jaccard) | **1.0** |
| Price-in-band (±15% band overlap) | **100%** |
| Tool-trajectory valid (zero un-approved sends) | **100%** |
| Mean time per case | ~66 s |

These cover the full mix: clean projects, a rush job (priced, not refused), a vague
inquiry routed to clarify, and an out-of-scope request routed to decline.
<!-- METRICS:END -->

### Before / after

| Metric | Manual (founder) | AutoBrief |
|---|---|---|
| Time to first proposal | ~3–5 hours | ~1 minute of compute + a quick review |
| Inquiries handled / day | ~3–4 | dozens (compute-bound, ~430 in an 8h-equivalent) |
| Scope accuracy | (baseline) | 1.0 mean Jaccard vs. gold |
| Price-in-band | — | 100% (deterministic rubric) |
| Cost / proposal | ~$480 (founder time) | ~$0.05 (LLM) |

## Submission artifacts

- **Deployed URL** (Cloud Run, `--with_ui`): _added on deploy_
- **GitHub repo**: _added on push_
- **Demo video** (≤3 min): see `docs/demo_script.md`
- **This narrative + architecture diagram** (README.md) **+ eval results** (above).
