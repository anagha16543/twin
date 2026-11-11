"""
End-to-end Criterion 3 pipeline:
course -> CO-PO matrix -> marks -> attainment config -> rubric -> run -> gaps -> re-assessment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db.seed_phase4 import seed_phase4
from app.models.academic import AcademicYear

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"
DEPT = "Computer Science and Engineering"


@pytest.fixture
def ctx(db_client, db_session, hod_headers):
    seed_phase4(db_session)
    ay = db_session.query(AcademicYear).first()
    return db_client, hod_headers, str(ay.id)


def _course(client, h, ay, code="22UAI608C"):
    r = client.post("/api/v1/criterion3/courses", headers=h, json={
        "department": DEPT, "academic_year_id": ay, "code": code, "name": "Machine Learning Algorithms", "semester": 6})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _upload(client, h, url, path):
    with open(path, "rb") as f:
        return client.post(url, headers=h, files={"file": (path.name, f, "text/csv")})


def test_full_pipeline(ctx):
    client, h, ay = ctx
    sid = _course(client, h, ay)
    r = _upload(client, h, f"/api/v1/criterion3/courses/{sid}/co-po", SAMPLES / "22UAI608C_co_po_matrix.csv")
    assert r.status_code == 200, r.text
    assert r.json()["course_outcomes"] == 4
    r = _upload(client, h, f"/api/v1/criterion3/courses/{sid}/marks", SAMPLES / "22UAI608C_marks.csv")
    assert r.status_code == 200, r.text
    assert r.json()["students"] == 60 and r.json()["see_components"] == 4

    # Without approved configuration 3.7 / 3.8 need clarification
    run = client.post("/api/v1/criterion3/run", headers=h, json={"department": DEPT, "academic_year_id": ay})
    assert run.status_code == 200, run.text
    assert run.json()["statuses"]["3.7"] == "NEEDS_RULE_CLARIFICATION"

    r = client.put("/api/v1/criterion3/config", headers=h, json={"department": DEPT, "academic_year_id": ay})
    assert r.status_code == 200 and r.json()["is_approved"] is True

    for code, comp in {"3.1": {"A": 2, "B": 3, "D": 2}, "3.7": {"A": 2, "B": 3}, "3.8": {"A": 9}}.items():
        r = client.put(f"/api/v1/criterion3/rubric-scores/{code}", headers=h, json={
            "department": DEPT, "academic_year_id": ay, "scores": {k: {"score": v} for k, v in comp.items()}})
        assert r.status_code == 200, r.text

    att = client.get("/api/v1/criterion3/attainment", headers=h, params={"department": DEPT, "academic_year_id": ay}).json()
    assert att["summary"]["cos_assessed"] == 4
    weak = [w["code"] for w in att["summary"]["weak_cos"]]
    assert "CO2" in weak, att["summary"]
    assert "PO1" in att["po"]["codes"] and "PSO1" in att["po"]["codes"]

    run = client.post("/api/v1/criterion3/run", headers=h, json={"department": DEPT, "academic_year_id": ay}).json()
    assert run["statuses"]["3.1"] in ("PASS", "WARNING")
    assert run["statuses"]["3.7"] != "NEEDS_RULE_CLARIFICATION"
    gaps = client.get("/api/v1/gaps", headers=h, params={"department": DEPT, "academic_year_id": ay}).json()
    assert any(g["title"].startswith("Weak CO: 22UAI608C CO2") and g["status"] == "IDENTIFIED" for g in gaps)

    # Remedial re-assessment fixes CO2 -> weak-CO gap auto-closes
    r = _upload(client, h, f"/api/v1/criterion3/courses/{sid}/marks", SAMPLES / "22UAI608C_marks_after_remedial.csv")
    assert r.status_code == 200
    run2 = client.post("/api/v1/criterion3/run", headers=h, json={"department": DEPT, "academic_year_id": ay}).json()
    assert run2["gaps_closed"] >= 1
    gaps = client.get("/api/v1/gaps", headers=h, params={"department": DEPT, "academic_year_id": ay}).json()
    assert any(g["title"].startswith("Weak CO: 22UAI608C CO2") and g["status"] == "COMPLETED" for g in gaps)

    # Dashboard (digital twin) reflects the run
    snap = client.get("/api/v1/digital-twin/criteria/CRITERION_3", headers=h,
                      params={"department": DEPT, "academic_year_id": ay}).json()
    assert snap["unevaluated_requirements"] == 0


def test_marks_upload_rejects_bad_cells(ctx, tmp_path):
    client, h, ay = ctx
    sid = _course(client, h, ay, "BAD101")
    bad = tmp_path / "bad.csv"
    bad.write_text("USN,Name,CIE-I Q1|CO1|10\n1,A,12\n2,B,x\n")
    r = _upload(client, h, f"/api/v1/criterion3/courses/{sid}/marks", bad)
    assert r.status_code == 422
    assert len(r.json()["detail"]["problems"]) == 2


def test_computed_component_cannot_be_entered(ctx):
    client, h, ay = ctx
    r = client.put("/api/v1/criterion3/rubric-scores/3.7", headers=h, json={
        "department": DEPT, "academic_year_id": ay, "scores": {"C": {"score": 20}}})
    assert r.status_code == 422


def test_faculty_cannot_run_or_configure(ctx, faculty_headers):
    client, _, ay = ctx
    assert client.post("/api/v1/criterion3/run", headers=faculty_headers,
                       json={"department": DEPT, "academic_year_id": ay}).status_code == 403
    assert client.put("/api/v1/criterion3/config", headers=faculty_headers,
                      json={"department": DEPT, "academic_year_id": ay}).status_code == 403
