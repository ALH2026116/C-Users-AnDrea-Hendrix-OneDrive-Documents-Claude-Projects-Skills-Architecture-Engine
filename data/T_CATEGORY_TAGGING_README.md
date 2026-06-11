# SkillFrame T-Category Tagging (first pass)

Tags every one of the **725** library skills with a Manufacturing **T category** —
`adaptive` / `digital` / `process` / `role_specific` — per
`SkillFrame_T_Classification_Rubric_v2`.

## Why this exists

The four-category "Manufacturing T Coverage" / "Skill Domains" breakdown is rendered in
**Layer 2 of the JD Assessment**, but **no canonical data source carries a per-skill T tag**:

- No workbook version (v1 → v2.1 → MDC-restructured) has a `t_category` column — "Adaptive"
  appears **zero** times as a tag in any of them.
- The deployed catalog (`skills_db.js` / `skills_db_catalog_patch.json`) stores only
  `id / name / area / subcategory` per skill — no T field.

So the live four-bar breakdown is **derived at runtime**, most likely as a coarse
**functional-area rollup** (the analyzer already uses skill-code/area heuristics for its
shop-floor/back-office indicator). This artifact replaces that proxy with an explicit,
auditable per-skill tag mapped to the rubric.

## Files

| File | What it is |
| --- | --- |
| `data/skills_master.csv` | Input: the 725 skills (id, name, area, sub, skill_type, desc), assembled from the deployed catalog + workbook descriptions. |
| `scripts/tag_t_categories.py` | The generator. Encodes the rubric. Re-runnable: `python3 scripts/tag_t_categories.py`. |
| `data/skill_t_categories.csv` | Output: one row per skill with `t_category`, `confidence`, `rationale`, `area_proxy_t`, `review_flag`. This is the column to paste into the workbook copy / feed into `skills_db.js`. |
| `data/skill_t_categories.json` | Same, as JSON. |

## Method (mirrors the rubric)

1. **Explicit decisions (`confidence: high`)** — the rubric's anchor examples + edge-case
   table are hard-coded, plus the two universal digital-literacy subcategories the rubric
   maps to Digital (DOL 2.7). These are the authoritative rows.
2. **Priority-order rule** — for everything else, the rubric's order is applied:
   **Adaptive → Digital → Process → Role-Specific**, using area + skill_type + name/desc
   keyword signals. Faithful guards from the rubric are encoded, e.g.:
   - a behavioral skill inside a functional domain (e.g. "Service Recovery" in Customer
     Success) stays **Role-Specific**, not Adaptive;
   - domain tool-use (CRM, campaign analytics, HRIS) stays **Role-Specific**, not Digital
     (the rubric's Campaign-Analytics precedent);
   - IT strategy/governance is **Role-Specific** even inside IT.
3. **`area_proxy_t`** — a coarse Area→T rollup (the heuristic the live analyzer most likely
   uses today), emitted alongside so the rubric tag can be diffed against it.
4. **`review_flag = REVIEW`** — set where the rubric tag disagrees with the area proxy, or
   confidence is low. **200 of 725** skills are flagged — these are the consultant's worklist.

## Distribution (this pass vs. rubric's rough target)

| Category | This pass | Rubric target |
| --- | --- | --- |
| Role-Specific | 60.7% | ~50-55% |
| Process | 12.0% | ~15-20% |
| Adaptive | 15.7% | ~15-20% |
| Digital | 11.6% | ~10-15% |

Adaptive and Digital land in target. **Role-Specific runs ~6 pts hot and Process ~4 pts
light** — they are mirror images of the same boundary: the rubric explicitly says
Quality, Safety/EHS, and Operations skills split between *Process* (methodology — CAPA, root
cause, hierarchy of controls, audits) and *Role-Specific* (domain — defect ID, HAZMAT, OSHA
specifics), and that split is a **human judgment call**. The heuristic defaults the
ambiguous ones to Role-Specific and flags them, rather than guessing Process. Start the
review there.

## How to use

- **Confidence `high` (130 skills)** — accept as-is; these are rubric-decided.
- **`REVIEW` rows (200 skills)** — consultant first pass, ≤30s each per the rubric.
  Concentrate on the Quality / Safety & EHS / Operations rows to recover the Process count.
- The rubric records a **secondary** category for v2 use; this pass assigns the **primary**
  only (what v1 scoring uses). Secondary tagging is a later layer.

This is a **first pass**, exactly as the rubric's tagging process prescribes — not a final
tagging. Re-running the script after editing the keyword/explicit tables regenerates both
outputs deterministically.
