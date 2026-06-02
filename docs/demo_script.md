# AutoBrief — Demo video shot list (≤3 min)

Narrate the business case throughout: a solo studio drowning in intake.

| # | Time | Shot | Narration beat |
|---|---|---|---|
| 1 | 0:00–0:15 | Title slide → founder's overflowing inbox | "A one-person studio. Every inquiry is 3–5 hours before any contract." |
| 2 | 0:15–0:35 | Paste a real inquiry into the Cloud Run `--with_ui` chat | "Drop the raw email in. That's the only input." |
| 3 | 0:35–1:25 | Watch the stream: Router → IntakeParser → Researcher (show citations) → ScoperEstimator (show the `compute_estimate` tool call + line items) → ProposalWriter brief/proposal | "It triages, parses, researches with sources, then a **deterministic rubric** prices it — no hallucinated numbers — and writes the proposal." |
| 4 | 1:25–2:05 | HITL approval prompts appear; click **Approve** → Gmail draft, tentative Calendar event, Drive doc, deck all created under `outbox/` | "Nothing is sent automatically. Every client-facing action waits for one human approval." |
| 5 | 2:05–2:30 | Cloud Trace view: agent steps, tool calls, the HITL pause | "Fully observable end to end." |
| 6 | 2:30–3:00 | Run two more inquiries fast: the vague one → **clarify** reply; the bank-in-2-weeks one → **polite decline**. Then the before/after metrics slide. | "It also knows when to ask, and when to say no. 3–5 hours → minutes. This is sellable to every agency with the same bottleneck." |

## Pre-recording checklist
- Cloud Run service warm (`min-instances=1`), URL smoke-tested twice.
- Three inquiries ready to paste: `eval/inquiries/01_crud_saas_clean.txt`,
  `06_vague_clarify.txt`, `08_out_of_scope_decline.txt`.
- `AUTOBRIEF_ENABLE_MCP=1` so delivery + HITL gates are live.
- `outbox/` cleared so created artifacts are visibly fresh.
- before/after slide updated with the latest `eval/results/last_run.json` numbers.
