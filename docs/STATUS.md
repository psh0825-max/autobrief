# AutoBrief — Build Status & Resume Guide

_Last saved: 2026-06-02 (Day 2). Submission deadline: **2026-06-05 17:00**._

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

## ✅ Done & verified (Day 2)
- **Router (custom `BaseAgent` orchestrator)** `autobrief/router.py` + `RouterClassifier`
  (`sub_agents/router_classifier.py`, output_schema → `state['routing']`),
  `ClarifierAgent`, `DeclineAgent`. Root is now `AutoBriefRouter` (proceed→pipeline,
  need_clarification→clarifier, decline→decline). **Note:** LLM `transfer_to_agent`
  is unusable in ADK 2.1.0 when an LlmAgent has a `SequentialAgent` peer (crashes:
  `'SequentialAgent' object has no attribute 'mode'` in agent_transfer.py) — hence the
  custom orchestrator + `disallow_transfer_to_*` on the peer LlmAgents.
- **DeliveryAgent wired** into the pipeline tail, but ONLY when `AUTOBRIEF_ENABLE_MCP=1`
  (interactive/deploy); eval path keeps it off so HITL doesn't stall headless runs.
- **Full eval on Vertex: 8/8 PERFECT** — routing 100%, archetype 100%, scope Jaccard
  1.0, price-in-band 100%, trajectory 100%, ~66 s/case. Metrics baked into README +
  NARRATIVE. (Fixes that got there: conservative feature-key selection in
  ScoperEstimator to stop archetype double-counting; classifier no longer declines
  rush jobs or small-budget/small-scope landing pages.)
- **Eval hardened**: `_run_one_with_retry` backs off on 429/RESOURCE_EXHAUSTED.
- **Docs**: README.md (arch diagram + metrics), docs/NARRATIVE.md, docs/demo_script.md.

- **DEPLOYED to Cloud Run** ✅ — **https://autobrief-g36me2m3ca-uc.a.run.app**
  (`--with_ui --trace_to_cloud`, min-instances=1, public). Verified end-to-end on
  Vertex: proceed → full proposal (price guardrail holds, $ band verbatim);
  decline → polite reply. **Deploy gotchas solved:** (a) `--trace_to_cloud` needs
  `opentelemetry-exporter-gcp-trace` in the agent's `requirements.txt` (added) or
  the container fails to start; (b) the runtime SA
  (`693521645262-compute@…`) needed `roles/aiplatform.user` + `roles/cloudtrace.agent`
  (granted). First deploy is WITHOUT MCP (matches plan default: deploy shows
  inference+drafts; MCP write actions run locally behind HITL).
  - API: `POST /run` body is **camelCase** (`appName/userId/sessionId/newMessage`).
    UI: `/dev-ui/?app=autobrief`.

## ⏭️ Next (in priority order)
1. **GitHub**: push repo (create remote `autobrief`, push `main`).
2. **(Optional) MCP+HITL demo**: redeploy with `AUTOBRIEF_ENABLE_MCP=1` (or show locally) to demo Gmail-draft/Calendar/Drive/deck approval gates → outbox artifacts.
3. **Demo video** (≤3 min) per docs/demo_script.md.
4. **Submit** before 2026-06-05 17:00 (URL + GitHub + video + NARRATIVE/README).

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
