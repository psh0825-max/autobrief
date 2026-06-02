# AutoBrief — Build Status & Resume Guide

_Last saved: 2026-06-02 (end of Day 1). Submission deadline: **2026-06-05 17:00**._

AutoBrief = autonomous client-intake & proposal agent for LightOn Plus Lab
(Google for Startups AI Agents Challenge, Track 1). Repo: `C:\Users\rnd\autobrief`.
Plan: `C:\Users\rnd\.claude\plans\all-eligible-startups-will-zesty-lynx.md`.

## ✅ Done & verified
- Repo scaffold + git. Python 3.12, ADK **2.1.0**, `mcp`, `truststore` installed.
- **Environment fixes (Norton TLS interception):**
  - Python app: `truststore.inject_into_ssl()` in `autobrief/config.py`.
  - gcloud: bundled-python + `truststore` copied in + `sitecustomize.py` + user env
    `CLOUDSDK_PYTHON` and `CLOUDSDK_PYTHON_SITEPACKAGES=1`. (Details in the
    `env-norton-tls-interception` memory.)
- **gcloud + Vertex auth done:** logged in as `support@lightonpluslab.com`;
  ADC saved; project **`lightonplus-apps`** (billing on, **Vertex AI API enabled**).
- **Deterministic estimator** `autobrief/tools/estimate_scope.py` + `rubric.yaml` — verified.
- **4-agent pipeline** (IntakeParser → Researcher[google_search] → ScoperEstimator →
  ProposalWriter) — **runs end-to-end on Vertex and produced a real proposal**
  (price band matches the rubric verbatim; guardrail consistent). See `smoke_test.py`.
- **Custom MCP server** `autobrief/mcp_server/studio_server.py` (5 tools: gmail draft,
  calendar event, drive doc, deck, slot) — ADK connects over stdio & lists tools; tools
  produce real artifacts under `outbox/`.
- **HITL toolsets** `autobrief/tools/mcp_toolsets.py` (write=approval-gated, read=open)
  + **DeliveryAgent** `autobrief/sub_agents/delivery_agent.py` (built; not yet wired into root).
- **Guardrails** `autobrief/tools/guardrails.py` (PII redaction callback + price-consistency) — self-test passes.
- **Eval harness** `eval/` (8 inquiries + gold, scorers, run_eval) — deterministic parts verified;
  full scored run now possible on Vertex.

## ⏭️ Next (in priority order)
1. **Run full eval on Vertex** → metrics + before/after table:
   `python eval/run_eval.py` (with the env vars below).
2. **Router**: add a proceed/clarify/decline `LlmAgent` as `root_agent`, then wire
   DeliveryAgent + HITL into the flow after ProposalWriter.
3. **Observability**: enable Cloud Trace/Logging (`--trace_to_cloud` on deploy).
4. **Deploy to Cloud Run**: `adk deploy cloud_run --project lightonplus-apps --region us-central1 --with_ui --trace_to_cloud ./autobrief` (set min-instances=1).
5. **Docs/demo**: README, architecture diagram, NARRATIVE.md, ≤3-min demo video.
6. **Submit** before 2026-06-05 17:00.

## ▶️ How to run locally (resume)
PowerShell, from anywhere:
```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI='1'
$env:GOOGLE_CLOUD_PROJECT='lightonplus-apps'
$env:GOOGLE_CLOUD_LOCATION='us-central1'
$env:PYTHONIOENCODING='utf-8'
python C:\Users\rnd\autobrief\smoke_test.py        # full pipeline on one sample
# or the ADK web UI (loads autobrief/.env automatically):
#   adk web C:\Users\rnd\autobrief
```
gcloud (if needed) requires `CLOUDSDK_PYTHON` + `CLOUDSDK_PYTHON_SITEPACKAGES=1`
(already set as user env vars). ADC is already logged in.
