#!/usr/bin/env python3
"""
Tag every SkillFrame skill with a Manufacturing T category
(Adaptive / Process / Digital / Technical / Role-Specific) per
SkillFrame_T_Classification_Rubric_v3.

Input:  data/skills_master.csv  (id, name, area, sub, skill_type, desc)
Output: data/skill_t_categories.csv
        data/skill_t_categories.json

Five categories (v3 adds TECHNICAL, the equipment/hardware bucket carved out of
Role-Specific):
  adaptive       - general human / cognitive / change-readiness capability.
  process        - recognized improvement / quality / safety-system methodology.
  digital        - exists because of digital tech (software, data, AI/ML).
  technical      - hands-on physical EQUIPMENT competency: operate, set up, diagnose,
                   maintain, repair, assemble machines & hardware (controls, automation,
                   robotics, CNC, hydraulics, welding, MHE, instrumentation).
  role_specific  - functional/domain expertise (HR, Finance, Sales, Procurement, etc.).

MECHATRONICS RULE (the v3 decision): controls / automation / robotics / CNC / PLC /
IoT-hardware and any operate-maintain-repair-assemble work on physical equipment -> TECHNICAL.
DATA/AI CARVE-OUT: skills whose CORE competency is data science / ML / software itself --
computer-vision model development, predictive/industrial AI, sensor-data analytics, app/system
development -- stay DIGITAL even when pointed at equipment. Test: "could a data/software person
do it without touching the machine?" yes -> Digital, no (hands on the hardware) -> Technical.

Method (mirrors the rubric):
  1. EXPLICIT decisions  -> rubric anchor examples + edge-case table -> confidence "high".
  2. PRIORITY-ORDER rule -> Adaptive -> Digital -> Process -> Technical -> Role-Specific,
     applied with area + skill_type + name/desc keyword signals -> confidence "medium"/"low".
     Digital outranks Technical so the data/AI carve-out wins on overlap.
  3. AREA PROXY tag       -> a coarse Area->T rollup, the heuristic the live analyzer most
     likely uses today. Emitted alongside so the rubric tag can be diffed against it.
  4. DISAGREEMENT flag    -> rubric tag != area-proxy tag (the skills worth a human look).

Non-explicit tags are a FIRST PASS and are meant for consultant review, exactly as the
rubric's tagging process prescribes (≤30s/skill first pass, validate distribution at end).
"""
import csv, json, re, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(HERE, "data", "skills_master.csv")

ADAPTIVE, DIGITAL, PROCESS, TECHNICAL, ROLE = \
    "adaptive", "digital", "process", "technical", "role_specific"

# ---------------------------------------------------------------------------
# 1. EXPLICIT rubric decisions (anchors + edge-case table). High confidence.
#    Only those that exist in the master are applied; the rest still inform keywords.
# ---------------------------------------------------------------------------
EXPLICIT = {
    # Adaptive anchors / edge cases
    "CORE-PROF-003": ADAPTIVE, "CORE-PROF-002": ADAPTIVE, "CORE-COMM-003": ADAPTIVE,
    "PEF-AT-001": ADAPTIVE, "PEF-CT-001": ADAPTIVE, "LEAD-CHG-002": ADAPTIVE,
    "LEAD-COMM-001": ADAPTIVE, "MGMT-PQM-004": ADAPTIVE, "AIPRO-AIG-003": ADAPTIVE,
    "LEAD-CHG-001": ADAPTIVE,
    # Digital anchors / edge cases
    "CORE-AI-001": DIGITAL, "CORE-AI-004": DIGITAL, "CORE-DIG-001": DIGITAL,
    "AIPRO-AIA-001": DIGITAL, "DAIO-SEC-003": DIGITAL, "DAIO-IOT-003": DIGITAL,
    "IT-SRV-002": DIGITAL, "IT-SEC-001": DIGITAL,
    # Process anchors / edge cases
    "CI-LN-002": PROCESS, "CI-KAI-009": PROCESS, "CI-MGT-018": PROCESS,
    "QLT-CAPA-002": PROCESS, "QLT-DATA-003": PROCESS, "EHS-HAZ-003": PROCESS,
    "MGMT-WRC-003": PROCESS, "IEM-LEAN-002": PROCESS,
    # Technical (equipment) anchors -- the hands-on-the-hardware spine. Several were
    # Role-Specific anchors under the 4-category rubric; v3 reclassifies them to Technical.
    "TECH-EQ-001": TECHNICAL, "TECH-DIAG-002": TECHNICAL, "TECH-HYD-001": TECHNICAL,
    "MFG-CNC-001": TECHNICAL, "MFG-WELD-001": TECHNICAL, "MFG-OPS-003": TECHNICAL,
    "MFG-TECH-003": TECHNICAL, "MNT-CM-004": TECHNICAL, "SERV-REP-002": TECHNICAL,
    "WHL-MHE-001": TECHNICAL, "IEM-PROD-003": TECHNICAL,
    # DATA/AI carve-out: equipment-adjacent but the competency is data science -> Digital.
    "MNT-REL-009": DIGITAL,
    # Role-Specific anchors / edge cases
    "HR-BEN-001": ROLE, "FIN-GA-002": ROLE, "SALES-ACCT-002": ROLE, "MKT-BRAND-001": ROLE,
    "QLT-NCM-001": ROLE, "SALES-CRM-001": ROLE, "MKT-DATA-002": ROLE, "MNT-PM-003": ROLE,
    "MGMT-WFM-003": ROLE, "EHS-ENV-003": ROLE,
}

# ---------------------------------------------------------------------------
# Area priors (coarse Area -> dominant T). Used for the AREA-PROXY tag and as a
# tie-breaker prior inside the priority-order rule.
# ---------------------------------------------------------------------------
AREA_PROXY = {
    "Universal Core": ADAPTIVE, "Prof Effectiveness": ADAPTIVE, "Leadership": ADAPTIVE,
    "Org Development": ADAPTIVE, "Training & Development": ADAPTIVE,
    "IT & Cybersecurity": DIGITAL, "Data & AI Operations": DIGITAL,
    "AI-Augmented Practice": DIGITAL, "AI & DigitalTic": DIGITAL, "MIS": DIGITAL,
    "Continuous Improvement": PROCESS, "Quality": PROCESS, "Safety & EHS": PROCESS,
    "Environmental & Sustain": PROCESS,
    "Technical Equip & Sys": TECHNICAL,
}
def area_proxy(area):
    return AREA_PROXY.get(area, ROLE)

DIGITAL_AREAS = {"IT & Cybersecurity", "Data & AI Operations", "AI-Augmented Practice",
                 "AI & DigitalTic", "MIS"}

# The canonical equipment area: every skill here is hands-on hardware -> Technical
# (unless an adaptive/digital signal claims it first; none here are data-science skills).
TECH_EQUIP_AREAS = {"Technical Equip & Sys"}

# Subcategories that are Digital regardless of area (universal computer/AI literacy --
# DOL 2.7 Basic Computer Skills). NOTE: digital-sounding subs that live inside a functional
# domain (e.g. "Digital Marketing", "Supply Chain Analytics", "HR Data & Reporting") are
# deliberately NOT here -- the rubric's Campaign-Analytics precedent keeps those Role-Specific.
DIGITAL_SUBS = {"Digital & Computer Literacy", "AI & Emerging Technology"}

# ---------------------------------------------------------------------------
# Keyword signals
# ---------------------------------------------------------------------------
KW = {
 "adaptive": ["communicat", "listen", "collaborat", "teamwork", "adaptab", "flexib",
   "resilien", "accountab", "professional", "ethic", "integrity", "initiative",
   "lifelong", "interpersonal", "emotional intelligence", "conceptual thinking",
   "analytical thinking", "critical thinking", "decision making", "problem identif",
   "coaching", "mentor", "influenc", "change adoption", "change communication",
   "conflict", "facilitation", "active listening", "empathy", "feedback utiliz",
   "creative thinking", "creativity", "self-", "work ethic", "judgment", "prioritiz",
   "time management", "customer interaction", "service orientation", "negotiation"],
 # "strong" digital terms => Digital anywhere; "weak" => Digital only inside a digital area.
 # NOTE (v3): robotics / automation-system / CNC HARDWARE is no longer "strong digital" --
 # the mechatronics rule routes physical control/automation hardware to TECHNICAL. Only the
 # data/software side stays Digital. The DATA/AI CARVE-OUT phrases below force Digital even
 # when the skill is equipment-adjacent (e.g. "reliability data analysis", "iot sensor data").
 "digital_strong": ["artificial intelligence", " ai ", "ai-", "ai literacy",
   "machine learning", " ml ", "data scien", "software development", "cloud",
   "cybersecur", " sql", "programming", "coding", "scripting", "computer vision",
   "digital literacy", "devops", "llm", "prompt engineering", "algorithm",
   "system administration", "access control", "encryption", "bias detection",
   "computer skills", "data pipeline", "data governance", "etl", "api integration",
   "network administration",
   # --- DATA/AI carve-out (equipment-adjacent but core competency is data/ML) -> Digital ---
   "industrial ai", "predictive analytics", "reliability data", "iot sensor", "sensor data",
   "model development", "digital twin", "ml model", "machine vision"],
 "digital_weak": ["data analy", "analytics", "software", "network", "database",
   "digital", "dashboard", "model", "data quality", "data visualization",
   "infrastructure", "automation"],
 "process": ["lean", "six sigma", "kaizen", "5s", "kanban", "continuous improvement",
   "root cause", "a3", "5-why", "5 why", "fishbone", "capa", "corrective action",
   "preventive action", "nonconform", "non-conform", "value stream", "standard work",
   "bottleneck", "throughput", "spc", "statistical process", "dmaic", "poka", "gemba",
   "hazard control", "hierarchy of controls", "incident investigation", "audit",
   "process improvement", "process awareness", "quality management", "quality system",
   "5s practice", "5s implementation", "lean manufacturing", "lean fundamental",
   # DOL 3.4 Scheduling/Coordinating, 3.6 Checking/Examining/Recording, 3.9 Sustainability
   "scheduling", "coordinating", "checking", "examining", "recording",
   "sustainab", "waste reduction", "energy management", "process documentation",
   "workflow optimization", "standardization", "standard operating procedure"],
 # TECHNICAL (equipment): hands-on physical hardware -- operate / set up / diagnose /
 # maintain / repair / assemble machines. Curated to hit equipment trades and AVOID
 # domain false-positives ("internal control", "document control", "access control",
 # "change control", "export control", "loss prevention", "control plan").
 "technical": [
   # machining / fabrication / welding trades
   "cnc", "machining", "lathe", "milling", " mill ", "grinding", "welding", " weld ",
   "weld ", "weld-", "mig/", "tig/", "smaw", "gmaw", "gtaw", "brazing", "soldering",
   "fabricat", "metal cutting", "metal forming", "press brake", "stamping", "workholding",
   "fixturing", "fixture & tooling", "tooling use", "cutting tool", "machinab",
   # equipment operation / setup / changeover
   "machine operation", "equipment operation", "equipment setup", "equipment set-up",
   "equipment startup", "equipment shutdown", "equipment changeover", "changeover",
   "tool use and care", "tool use & care", "measurement tool",
   # mechanical / electrical / fluid-power systems (hands-on)
   "mechanical assembly", "assembly procedure", "mechanical troubleshoot",
   "mechanical diagnost", "disassembl", "electrical diagnost", "electrical component",
   "electrical schematic", "electrical & wiring", "electrical and wiring", "wiring assembly",
   "hydraulic", "pneumatic", "lubricat", "torque", "fastener", "calibrat",
   # controls / automation / robotics HARDWARE (mechatronics -> Technical, not Digital)
   "plc", "programmable logic", "robot", "servo", "actuator", "motion control",
   "control system", "controls system", "instrumentation", "bearing", "motor ",
   "automation hardware", "control panel",
   # maintenance / diagnostics / firmware-on-the-machine
   "equipment troubleshoot", "equipment troublesho", "equipment care", "equipment cleaning",
   "equipment inspection", "equipment criticality", "preventive maintenance",
   "predictive maintenance", "corrective maintenance", "breakdown response",
   "component replacement", "diagnostic tool", "diagnostic software", "firmware",
   "telematics", "building systems", "emergency equipment",
   # painting / coating equipment trades
   "paint booth", "spray application", "powder coating", "coating thickness",
   "surface preparation",
   # material-handling equipment
   "forklift", "pallet jack", "material handling equipment", "powered industrial truck",
   "pre-use inspection", "equipment pre-use",
   # technical-trade documentation (read-to-build, shop floor)
   "blueprint", "schematic", "drawing reading", "specification reading",
   "work instruction reading", "fabrication drawing", "technical manual", "service bulletin"],
 # SAFETY methodology -> Process. Curated PHRASES only (never bare "safety", which would
 # catch "safety stock"). Safety leadership/communication is caught by Adaptive first;
 # equipment-operation/inspection safety skills are kept Technical (see SAFETY_TECH_KEEP).
 "safety_process": [
   "lockout", "tagout", "loto", " ppe ", "ppe usage", "ppe use", "personal protective",
   "hazard communica", "hazard identif", "hazard recognition", "hazard control",
   "confined space", "hot work", "ergonomic", "chemical handling",
   "hazardous materials handling", "hazardous materials shipping", "hazmat",
   "spill prevention", "spill response", "load secur", "lifting practice", "safe lifting",
   "traffic safety", "yard safety", "unloading safety", "contractor safety",
   "safety awareness", "safety protocol", "safety check", "safety practice",
   "safety procedure", "safety policy", "safety audit", "risk assessment (safety)",
   "site assessment", "equipment tagging"],
}
# Digital keywords that are tool-use-in-a-domain (NOT digital) when outside a digital area.
DOMAIN_TOOL_TERMS = ["crm", "campaign", "erp ", "hris", "cmms", "marketing", "sales pipeline"]

# Safety skills kept TECHNICAL (the skill is operating/inspecting equipment, "safe" is the
# adjective) -- they skip the safety->Process promotion and fall through to the Technical step.
SAFETY_TECH_KEEP = ["equipment operation", "pre-use inspection", "equipment pre-use",
                    "equipment inspection"]
# skill_type "Safety" rows that are NOT safety methodology (security/shrink) -> stay Role.
NON_SAFETY_GUARD = ["loss prevention"]

# IT skills that are strategy/governance -> Role-Specific even inside IT.
IT_ROLE_TERMS = ["strategy", "governance", "vendor", "business alignment", "procurement",
                 "roadmap", "architecture review", "budgeting"]

def kwhit(text, key):
    return any(k in text for k in KW[key])

def classify(row):
    """Return (tag, confidence, rationale)."""
    sid = row["id"]
    if sid in EXPLICIT:
        return EXPLICIT[sid], "high", "explicit rubric anchor/edge-case decision"

    if row["sub"] in DIGITAL_SUBS:
        return DIGITAL, "high", f"universal digital/computer-literacy subcategory ({row['sub']})"

    name = row["name"].lower()
    desc = row["desc"].lower()
    area = row["area"]
    stype = row["skill_type"]
    text = f" {name} . {desc} "

    a_hit = kwhit(text, "adaptive")
    d_strong = kwhit(text, "digital_strong")
    d_weak = kwhit(text, "digital_weak")
    p_hit = kwhit(text, "process")
    t_hit = kwhit(text, "technical")
    tech_area = area in TECH_EQUIP_AREAS
    adaptive_area = area in AREA_PROXY and AREA_PROXY[area] == ADAPTIVE
    # Digital signal: strong terms anywhere, OR (in a digital area) strong/weak terms.
    d_hit = d_strong or (area in DIGITAL_AREAS and (d_strong or d_weak))

    # --- Priority order: Adaptive -> Digital -> Process -> Technical -> Role-Specific ---

    # 1) ADAPTIVE: general human/cognitive/change-readiness capability.
    #    Behavioral skills count as Adaptive only when the area is an adaptive-prior area
    #    OR an adaptive keyword is present -- a behavioral skill inside a functional domain
    #    (e.g. "Service Recovery" in Customer Success) stays Role-Specific per the rubric.
    if (stype == "Behavioral" and (adaptive_area or a_hit) and not d_hit and not p_hit) or \
       (a_hit and adaptive_area):
        return ADAPTIVE, ("high" if adaptive_area and a_hit else "medium" if a_hit or adaptive_area else "low"), \
               f"general/behavioral capability (type={stype}, area={area})"

    # 2) DIGITAL: exists because of digital tech. Gate domain-tool false positives.
    domain_tool = any(t in text for t in DOMAIN_TOOL_TERMS) and area not in DIGITAL_AREAS
    if (area in DIGITAL_AREAS or d_hit) and not domain_tool:
        # IT strategy/governance -> Role-Specific
        if area == "IT & Cybersecurity" and any(t in text for t in IT_ROLE_TERMS):
            return ROLE, "medium", "IT strategy/governance -> domain (Role-Specific)"
        conf = "high" if area in DIGITAL_AREAS and d_hit else "medium" if area in DIGITAL_AREAS or d_hit else "low"
        return DIGITAL, conf, f"digital tech build/operate signal (area={area}, kw={d_hit})"

    # 3) PROCESS: recognized improvement / quality / safety-system methodology.
    #    Safety methodology promotes here (skill_type "Safety" or a safety keyword), EXCEPT
    #    equipment-operation/inspection safety skills (kept Technical) and non-safety "Safety"
    #    rows like loss prevention. Adaptive already claimed safety leadership/communication.
    safety_methodology = (stype == "Safety" or kwhit(text, "safety_process")) \
        and not any(k in text for k in SAFETY_TECH_KEEP) \
        and not any(k in text for k in NON_SAFETY_GUARD)
    if p_hit or area == "Continuous Improvement" or safety_methodology:
        why = ("safety methodology -> Process" if safety_methodology and not p_hit
               else f"improvement/methodology signal (area={area}, kw={p_hit})")
        conf = ("high" if p_hit and area in ("Continuous Improvement","Quality","Safety & EHS")
                else "high" if stype == "Safety" else "medium")
        return PROCESS, conf, why

    # Adaptive carve-out inside Role-Specific areas (e.g. coaching/communication in Sales/HR)
    if a_hit and stype == "Behavioral":
        return ADAPTIVE, "low", f"behavioral carve-out in role area (area={area})"

    # 4) TECHNICAL: hands-on physical equipment / hardware competency. Ranked after Digital
    #    (so the data/AI carve-out -- computer vision, reliability data -- stays Digital) and
    #    after Process (so methodology like SPC, *PM scheduling*, lean stays Process). Gated to
    #    hands-on skill types; the canonical equipment area always qualifies.
    if tech_area or (t_hit and stype in ("Technical", "Operational", "Safety", "")):
        conf = "high" if tech_area or (t_hit and stype == "Technical") else "medium"
        return TECHNICAL, conf, f"equipment/hardware hands-on signal (area={area}, kw={t_hit})"

    # 5) ROLE-SPECIFIC: fallback (domain expertise).
    return ROLE, ("medium" if stype in ("Technical", "Operational", "Safety") else "low"), \
           f"domain expertise fallback (type={stype}, area={area})"


def main():
    rows = list(csv.DictReader(open(SRC)))
    out = []
    for r in rows:
        tag, conf, why = classify(r)
        proxy = area_proxy(r["area"])
        out.append({
            "id": r["id"], "name": r["name"], "area": r["area"], "sub": r["sub"],
            "skill_type": r["skill_type"],
            "t_category": tag, "confidence": conf, "rationale": why,
            "area_proxy_t": proxy,
            "review_flag": "REVIEW" if (tag != proxy or conf == "low") else "",
        })

    # write CSV + JSON
    cols = ["id","name","area","sub","skill_type","t_category","confidence",
            "rationale","area_proxy_t","review_flag"]
    with open(os.path.join(HERE,"data","skill_t_categories.csv"),"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    with open(os.path.join(HERE,"data","skill_t_categories.json"),"w") as f:
        json.dump(out, f, indent=1)

    # ---- distribution report to stdout ----
    n = len(out)
    dist = Counter(o["t_category"] for o in out)
    conf = Counter(o["confidence"] for o in out)
    flags = sum(1 for o in out if o["review_flag"])
    disagree = sum(1 for o in out if o["t_category"] != o["area_proxy_t"])
    print(f"tagged {n} skills")
    print("RUBRIC EXPECTED (v3, 5-cat)  Role-Specific ~45-50% | Technical ~10-14% | "
          "Process ~12-16% | Adaptive ~15-18% | Digital ~10-13%")
    label = {ROLE:"Role-Specific",TECHNICAL:"Technical",PROCESS:"Process",
             ADAPTIVE:"Adaptive",DIGITAL:"Digital"}
    for t in (ROLE, TECHNICAL, PROCESS, ADAPTIVE, DIGITAL):
        print(f"  {label[t]:14s} {dist[t]:4d}  ({100*dist[t]/n:4.1f}%)")
    print("confidence:", dict(conf))
    print(f"rubric vs area-proxy disagreements: {disagree}")
    print(f"flagged for review (disagree or low-confidence): {flags}")

if __name__ == "__main__":
    main()
