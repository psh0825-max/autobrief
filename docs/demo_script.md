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

## Word-for-word narration (≈2:45, read while you click)

Open `docs/demo_deck.html` in a browser for the slide track, and the live UI in a
second tab. Read these lines:

- **0:00 (title slide):** "This is AutoBrief — an autonomous client-intake and proposal agent, built on Google ADK and Gemini on Vertex AI, for a one-person AI MVP studio."
- **0:12 (problem):** "For a solo founder, the bottleneck isn't building — it's winning the work. Every inquiry is three to five hours of reading, researching, scoping, pricing, and writing a proposal before any contract."
- **0:28 (paste inquiry, live UI):** "So I drop a raw client email straight into the deployed agent. That's the only input."
- **0:40 (streaming):** "It triages the inquiry, parses it into a structured brief, researches the client with cited web search, and then — this is the key part — a deterministic rule-book prices it. The model only classifies; every dollar comes from the rubric, so there are no hallucinated quotes."
- **1:10 (proposal appears):** "Out comes a full proposal — scope, timeline, and a price band quoted verbatim from the estimate."
- **1:25 (HITL approvals):** "Nothing client-facing is sent automatically. Each delivery action — the Drive doc, the deck, the calendar invite, the Gmail draft — pauses for one human approval. I click approve."
- **2:05 (Cloud Trace):** "And it's fully observable — here's the Cloud Trace view showing every agent step, tool call, and the human-approval pause."
- **2:20 (clarify + decline, quick):** "It also knows when to ask — a vague inquiry gets a clarifying reply — and when to say no: a fully licensed bank in two weeks for five hundred dollars gets a polite decline."
- **2:35 (metrics slide):** "Across an eight-case evaluation it scores one hundred percent on routing, scope, and price-in-band. Three-to-five hours becomes one minute — and it's sellable to every agency with the same bottleneck. That's AutoBrief."

## Pre-recording checklist
- Cloud Run service warm (`min-instances=1`), URL smoke-tested twice.
- Three inquiries ready to paste: `eval/inquiries/01_crud_saas_clean.txt`,
  `06_vague_clarify.txt`, `08_out_of_scope_decline.txt`.
- `AUTOBRIEF_ENABLE_MCP=1` so delivery + HITL gates are live.
- `outbox/` cleared so created artifacts are visibly fresh.
- before/after slide updated with the latest `eval/results/last_run.json` numbers.
