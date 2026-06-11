# SkillFrame T-Category Tagging (first pass)

Tags every one of the **725** library skills with a Manufacturing **T category** —
`adaptive` / `process` / `digital` / `technical` / `role_specific` — per
`SkillFrame_T_Classification_Rubric_v3`.

## The five categories

| Category | What it is | Examples |
| --- | --- | --- |
| **adaptive** | General human / cognitive / change-readiness capability | Active Listening, Critical Thinking, Change Adoption |
| **process** | Recognized improvement / quality / safety-system methodology | CAPA, Root Cause Analysis, 5S, SPC, Hierarchy of Controls |
| **digital** | Exists because of digital tech — software, data, AI/ML | AI Literacy, SQL, Cybersecurity, ML Model Development |
| **technical** | Hands-on physical **equipment** competency — operate, set up, diagnose, maintain, repair, assemble machines & hardware | CNC Machine Operation, Hydraulic Component Replacement, MIG Welding, Forklift Operation, Breakdown Repair |
| **role_specific** | Functional / domain expertise | Journal Entry Prep, Campaign Analytics, Spare Parts Mgmt, OSHA Recordkeeping |

**v3 added `technical`** — the equipment/hardware bucket carved out of what v1/v2 lumped
into Role-Specific. A manufacturer's shop-floor skill mix (machining, welding, hydraulics,
maintenance, MHE) is now visible as its own bar instead of being buried in "Role-Specific."

## The mechatronics rule (the v3 decision)

The hard question v3 settles: where do controls / automation / robotics / CNC / PLC / IoT
skills go? They live on physical equipment but some are really data/software work.

- **Default — physical control & automation hardware → `technical`.** Operating, setting up,
  diagnosing, maintaining, repairing, or assembling equipment — including PLCs, robotics,
  CNC, hydraulics, instrumentation, control panels — is Technical. It matches who does the
  work (controls/maintenance techs are shop-floor technical, not the IT/data team) and keeps
  one clean, fast rule.
- **DATA/AI carve-out → stays `digital`.** Skills whose **core competency is data science /
  ML / software itself** — computer-vision model development, predictive/industrial AI,
  sensor-data analytics, app/system development — stay Digital **even when pointed at
  equipment**, because the skill is the data competency and the machine is just the data
  source. This mirrors the rubric's existing Campaign-Analytics precedent (the skill is the
  analytics, the domain is incidental).
- **The test:** *"Could a data/software person do this without touching the machine?"*
  Yes → Digital. No (you need hands on the hardware) → Technical.

The carve-out in action, on two near-identical-sounding skills:

| Skill | Tag | Why |
| --- | --- | --- |
| `Reliability Data Analysis` (MNT-REL-009) | **digital** | Weibull/failure-stats analysis — a data analyst could do it off the data, no machine |
| `Predictive Maintenance Techniques` (MNT-REL-008) | **technical** | Vibration analysis / thermography — hands on the running equipment |
| `Computer Vision for Manufacturing` (DAIO-IOT-003) | **digital** | The skill is building/training the ML model, not fixing the camera |
| `CNC Machine Operation` (MFG-CNC-001) | **technical** | Operating the machine on the floor |

In practice the carve-out is a handful of skills; most already live in the Data & AI
Operations area and were Digital anyway. Digital **outranks** Technical in the priority
order so the carve-out always wins on overlap.

## Why this exists

The category breakdown is rendered in **Layer 2 of the JD Assessment**, but **no canonical
data source carries a per-skill T tag**:

- No workbook version (v1 → v2.1 → MDC-restructured) has a `t_category` column.
- The deployed catalog (`skills_db.js` / `skills_db_catalog_patch.json`) stores only
  `id / name / area / subcategory` per skill — no T field.

So the live breakdown is **derived at runtime**, most likely as a coarse **functional-area
rollup**. This artifact replaces that proxy with an explicit, auditable per-skill tag.

## Files

| File | What it is |
| --- | --- |
| `data/skills_master.csv` | Input: the 725 skills (id, name, area, sub, skill_type, desc). |
| `scripts/tag_t_categories.py` | The generator. Encodes the rubric. Re-runnable: `python3 scripts/tag_t_categories.py`. |
| `data/skill_t_categories.csv` | Output: one row per skill with `t_category`, `confidence`, `rationale`, `area_proxy_t`, `review_flag`. |
| `data/skill_t_categories.json` | Same, as JSON. |

## Method (mirrors the rubric)

1. **Explicit decisions (`confidence: high`)** — the rubric's anchor examples + edge-case
   table are hard-coded, including the new Technical anchors and the data/AI carve-out
   anchors. These are the authoritative rows.
2. **Priority-order rule** — for everything else:
   **Adaptive → Digital → Process → Technical → Role-Specific**, using area + skill_type +
   name/desc keyword signals. Order matters:
   - **Digital before Technical** so the data/AI carve-out (computer vision, reliability
     data) wins over the equipment signal.
   - **Process before Technical** so methodology (SPC, *PM scheduling*, lean, LOTO) stays
     Process rather than getting pulled into equipment.
   - a behavioral skill inside a functional domain stays **Role-Specific**, not Adaptive;
   - domain tool-use (CRM, campaign analytics, HRIS) stays **Role-Specific**, not Digital;
   - IT strategy/governance is **Role-Specific** even inside IT.
3. **`area_proxy_t`** — a coarse Area→T rollup, emitted alongside so the rubric tag can be
   diffed against it.
4. **`review_flag = REVIEW`** — set where the rubric tag disagrees with the area proxy, or
   confidence is low. These are the consultant's worklist.

## Distribution (this pass vs. rubric's rough target)

| Category | This pass | Rubric target |
| --- | --- | --- |
| Role-Specific | 49.7% | ~45-50% |
| Technical | 11.0% | ~10-14% |
| Process | 11.9% | ~12-16% |
| Adaptive | 15.7% | ~15-18% |
| Digital | 11.7% | ~10-13% |

Adaptive, Digital, Technical, and Role-Specific land in target. **Process runs a few points
light** — the rubric splits Quality / Safety / Operations skills between *Process*
(methodology) and *Role-Specific* (domain), and that split is a human judgment call. The
heuristic defaults the ambiguous ones to Role-Specific and flags them. Start review there.
Note that **safety skills outside the "Safety & EHS" area** (e.g. LOTO / PPE in Manufacturing,
Service, Warehouse) currently fall to Role-Specific — promote them to Process on review if
you treat safety as a methodology bucket.

## How to use

- **Confidence `high`** — accept as-is; these are rubric-decided.
- **`REVIEW` rows** — consultant first pass, ≤30s each. Concentrate on the Quality / Safety /
  Operations rows to recover the Process count, and on the Manufacturing/Service equipment
  rows to confirm the new Technical/Role-Specific boundary.
- The rubric records a **secondary** category for v2+ use; this pass assigns the **primary**
  only. Secondary tagging is a later layer.

This is a **first pass**, exactly as the rubric's tagging process prescribes. Re-running the
script after editing the keyword/explicit tables regenerates both outputs deterministically.
