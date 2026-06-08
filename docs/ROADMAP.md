# AutoBrief — Commercialization Roadmap

Honest read: today AutoBrief is a working **prototype** (hackathon MVP) — strong
architecture and a defensible core (deterministic pricing + HITL), but the hard
commercial parts are still ahead. This is the path from "impressive demo / founder's
internal tool" to "sellable SaaS." Effort is rough solo-dev estimate.

## Where it stands
- ✅ Multi-agent reasoning spine, router, deterministic pricing, HITL gates, eval (8 synthetic), Cloud Run deploy, Cloud Trace.
- ⚠️ Delivery is stubbed (writes to `outbox/`, not real Gmail/Calendar/Drive/Canva).
- ⚠️ Rubric numbers are hand-made, not calibrated to real deals.
- ⚠️ Eval is 8 self-authored cases (circular); proposal *quality* never human-judged.
- ⚠️ In-memory sessions, no auth/multi-tenancy/billing/persistence.

## Phase 0 — "Real for one user" (the founder's own studio) · ~1–2 weeks
The fastest value: make it genuinely usable for LightOn Plus Lab itself.
1. **Real Google integrations** behind the existing MCP contract: swap stubs for
   Gmail `drafts.create`, Calendar `events.insert`, Drive `files.create` (OAuth for
   one account). The tool signatures already exist — this is filling in 4 functions.
2. **Persist sessions/artifacts** (SQLite or Firestore) so runs survive restarts.
3. **Calibrate the rubric** on the founder's last ~10–20 real proposals (won + lost):
   adjust base days/prices and the complexity heuristic to match reality.
4. **Dogfood**: run every real inbound inquiry through it for 2–3 weeks; founder
   reviews/edits before sending. Log accept/edit/reject per proposal.

**Exit criteria:** founder actually uses it daily; proposals need only light edits.

## Phase 1 — "Trustworthy" (validation + safety) · ~2–3 weeks
1. **Real eval set**: 30–50 *real* (anonymized) past inquiries with outcomes;
   add a **human quality rubric** (would-send? edits needed?) and A/B vs.
   founder-written proposals. Replace the self-authored gold.
2. **Proposal-quality tuning**: brand-voice prompt, few-shot from the founder's best
   proposals; measure edit-distance to the sent version over time.
3. **Harden guardrails**: stronger prompt-injection tests, price-bound sanity checks,
   PII handling audited, abuse/rate-limit protection on the public endpoint.
4. **Cost & latency budget**: per-proposal cost dashboard; Pro→Flash fallback rules.

## Phase 2 — "Sellable" (multi-tenant SaaS) · ~4–8 weeks
1. **Auth + multi-tenancy**: per-studio accounts, isolated data, per-tenant rubric
   and brand voice config (the rubric becomes a customer-editable resource).
2. **Onboarding**: connect-your-Gmail/Calendar/Drive flow; import past proposals to
   auto-calibrate the rubric.
3. **Billing** (usage- or seat-based) + plan limits.
4. **Admin/observability**: per-tenant traces, error alerting, audit log of every
   HITL approval (compliance story for B2B).
5. **Data/compliance**: retention policy, DPA, data-deletion; SOC2-readiness if
   selling upmarket.

## Phase 3 — "Defensible" (moat) · ongoing
- **Closed-loop learning**: feed accept/edit/reject signals back to improve scoping
  and proposal quality per tenant.
- **Win-rate analytics**: which scopes/prices actually convert — becomes the studio's
  pricing intelligence, not just an automation.
- **Vertical templates**: rubric + archetype packs per niche (e.g. agencies, consultancies).

## Biggest risks / open questions
- **Quality bar**: will clients accept AI-drafted proposals? (Phase 1 answers this.)
- **Pricing accuracy**: a wrong quote is worse than no quote → rubric calibration is critical.
- **Liability**: who owns a mis-priced/mistakenly-sent proposal? (HITL mitigates; needs ToS.)
- **Moat**: the LLM plumbing is replicable; the moat is the calibrated rubric + win-rate data per customer.

## Suggested first move
Phase 0, item 1 (real Gmail/Drive/Calendar behind the MCP contract) + item 3
(rubric calibration). Together they turn the demo into something the founder relies
on — the cheapest path to proving the whole thesis.
