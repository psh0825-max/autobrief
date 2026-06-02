# Sample outputs

Real artifacts produced by AutoBrief on Vertex AI for three representative
inquiries (one per routing outcome). Generated with
`python _gen_demo_outputs.py`. Use them as judge-facing samples and as a
storyboard for the demo video.

| File | Inquiry | Routed |
|---|---|---|
| `01_crud_saas_clean.md` | internal CRM MVP | **proceed** → full proposal + reply draft |
| `06_vague_clarify.md` | vague "app idea" | **need_clarification** → questions draft |
| `08_out_of_scope_decline.md` | full licensed bank in 2 weeks for $500 | **decline** → polite reply |

**On price reproducibility:** the rubric arithmetic in `estimate_scope()` is fully
deterministic — given a classification it always returns the same band. The one
LLM *judgment* input is the complexity multiplier (1.0–1.6), so the exact band can
shift run-to-run when the model reads a project as more/less complex (e.g. the CRM
sample here lands at ~$18–22k at complexity ≈1.25, vs the gold band $14.5–17.5k at
complexity 1.0). The eval's **100% price-in-band** figure is measured against
gold-labeled complexity; in production the band is always internally consistent —
the proposal quotes the estimate's band verbatim, never a number the LLM invented.
