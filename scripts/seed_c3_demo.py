"""
seed_c3_demo.py — load the Criterion 3 sample data through the public API.

Uses exactly the same endpoints as the portal, so every attainment value,
rubric score and status is computed by the backend.

  1. creates the 3 AIML courses in sample_data/courses.csv
  2. uploads each CO-PO matrix and marks sheet
  3. approves the attainment methodology (default levels)
  4. enters course-exit and program-level survey results
  5. enters reviewer rubric scores for the evidence-based components
  6. uploads + links + verifies evidence PDFs (3.4 left without evidence on purpose)
  7. runs Criterion 3

Usage (backend running):
    python scripts/seed_c3_demo.py --email hod@viit.ac.in --password Hod@12345
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_data"
DEPT_DEFAULT = "Artificial Intelligence and Machine Learning"

COURSE_EXIT = {  # % of students who agree the CO was achieved (course exit survey)
    "22UAI608C": {"CO1": 82, "CO2": 61, "CO3": 78, "CO4": 74},
    "22UAI602C": {"CO1": 80, "CO2": 77, "CO3": 70, "CO4": 72},
    "22UAI603C": {"CO1": 79, "CO2": 73, "CO3": 76},
}
PO_SURVEYS = [
    {"name": "Program Exit Survey 2026", "values": {"PO1": 2.6, "PO2": 2.4, "PO3": 2.3, "PO4": 2.1, "PO5": 2.7, "PO6": 2.0,
                                                   "PO7": 2.2, "PO8": 2.5, "PO9": 2.3, "PO10": 1.9, "PO11": 2.4, "PSO1": 2.6, "PSO2": 2.3}},
    {"name": "Employer Survey 2026", "values": {"PO1": 2.4, "PO2": 2.2, "PO3": 2.2, "PO4": 2.0, "PO5": 2.6, "PO8": 2.6,
                                               "PO9": 2.1, "PO11": 2.3, "PSO1": 2.4, "PSO2": 2.2}},
]
REVIEWER = {
    "3.1": {"A": 2, "B": 2.5, "D": 1.5},
    "3.2": {"A": 3, "B": 4, "C": 2},
    "3.3": {"A": 5, "B": 4.5},
    "3.4": {"A": 3.5, "B": 4.5},
    "3.5": {"A": 9, "B": 8.5},
    "3.6": {"A": 8},
    "3.7": {"A": 2, "B": 2.5},
    "3.8": {"A": 8.5},
}
EVIDENCE = [
    ("REQ_3_1", "C3.1_CIE_Question_Papers_and_CO_Mapping.pdf", True),
    ("REQ_3_2", "C3.2_SEE_Paper_Setting_and_Scrutiny_Process.pdf", True),
    ("REQ_3_3", "C3.3_Lab_Rubrics_and_Evaluation_Sheets.pdf", True),
    ("REQ_3_5", "C3.5_Project_Evaluation_Rubrics.pdf", True),
    ("REQ_3_6", "C3.6_SDG_Project_Portfolio.pdf", True),
    ("REQ_3_7", "C3.7_CO_Attainment_Methodology.pdf", True),
    ("REQ_3_8", "C3.8_PO_PSO_Attainment_Report.pdf", False),   # left pending HOD review
]


def make_pdf(title: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(56, 790, title.replace("_", " ").replace(".pdf", ""))
    c.setFont("Helvetica", 11)
    c.drawString(56, 765, "Department of AIML - NBA Criterion 3 course-file evidence (sample).")
    c.drawString(56, 748, "Academic Year 2026-27 - UG Engineering Tier-I.")
    c.showPage()
    c.save()
    return buf.getvalue()


def ok(r: httpx.Response, what: str) -> dict:
    if r.status_code >= 400:
        print(f"  ! {what}: HTTP {r.status_code} {r.text[:300]}")
        return {}
    return r.json() if r.content else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000/api/v1")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--department", default=DEPT_DEFAULT)
    a = ap.parse_args()

    api = httpx.Client(base_url=a.api, timeout=120)
    tok = api.post("/auth/login", json={"email": a.email, "password": a.password})
    if tok.status_code != 200:
        print("Login failed:", tok.text)
        return 1
    api.headers["Authorization"] = f"Bearer {tok.json()['access_token']}"
    years = api.get("/academic-years").json()
    ay = next((y for y in years if y["is_active"]), years[0])
    dept, ay_id = a.department, ay["id"]
    q = {"department": dept, "academic_year_id": ay_id}
    print(f"Academic year {ay['name']} | {dept}")

    existing = {c["code"]: c for c in api.get("/criterion3/courses", params=q).json()}
    with open(SAMPLES / "courses.csv", newline="") as f:
        courses = list(csv.DictReader(f))
    for c in courses:
        code = c["code"]
        if code in existing:
            sid = existing[code]["id"]
        else:
            sid = ok(api.post("/criterion3/courses", json={**q, "code": code, "name": c["name"],
                                                            "semester": int(c["semester"]), "credits": float(c["credits"])}),
                     f"create {code}").get("id")
        if not sid:
            continue
        with open(SAMPLES / f"{code}_co_po_matrix.csv", "rb") as f:
            r = ok(api.post(f"/criterion3/courses/{sid}/co-po", files={"file": (f.name, f, "text/csv")}), f"{code} CO-PO")
        with open(SAMPLES / f"{code}_marks.csv", "rb") as f:
            m = ok(api.post(f"/criterion3/courses/{sid}/marks", files={"file": (f.name, f, "text/csv")}), f"{code} marks")
        ok(api.put(f"/criterion3/courses/{sid}/indirect", json={"values": COURSE_EXIT[code]}), f"{code} exit survey")
        print(f"  {code}: {r.get('course_outcomes')} COs, {r.get('mappings')} CO-PO links, {m.get('students')} students")

    ok(api.put("/criterion3/config", json={**q, "approve": True}), "approve config")
    ok(api.put("/criterion3/po-indirect", json={**q, "surveys": PO_SURVEYS}), "PO surveys")
    for code, comps in REVIEWER.items():
        ok(api.put(f"/criterion3/rubric-scores/{code}", json={**q, "scores": {k: {"score": v} for k, v in comps.items()}}),
           f"rubric {code}")

    crit = next(c for c in api.get("/nba/criteria").json() if c["code"] == "CRITERION_3")
    reqs = {r["code"]: r for r in api.get(f"/nba/criteria/{crit['id']}/requirements").json()}
    linked = {e["document_id"] for r in reqs.values() for e in api.get(f"/documents/requirements/{r['id']}/evidence").json()}
    if not linked:
        for code, fname, verify in EVIDENCE:
            up = ok(api.post("/documents/upload", params=q, files={"file": (fname, make_pdf(fname), "application/pdf")}),
                    f"upload {fname}")
            if not up:
                continue
            ok(api.post(f"/documents/requirements/{reqs[code]['id']}/evidence",
                        json={"document_id": up["document_id"], "is_primary": True}), f"link {fname}")
            if verify:
                ok(api.patch(f"/documents/{up['document_id']}/validation", json={"validation_status": "VALIDATED"}),
                   f"verify {fname}")

    run = ok(api.post("/criterion3/run", json=q), "run Criterion 3")
    if run:
        print(f"Criterion 3: {run['total_score']}/{run['max_score']} | readiness {run['readiness_percentage']}% | "
              f"gaps +{run['gaps_created']} / closed {run['gaps_closed']}")
        for k, v in run["statuses"].items():
            print(f"  {k}: {v}")
        w = run["attainment_summary"]["weak_cos"]
        print("  Weak COs:", ", ".join(f"{x['course']} {x['code']} ({x['final']})" for x in w) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
