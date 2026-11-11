"""
Tests for the small endpoints added for the HTML/CSS/JS Criterion 3 frontend:
  * GET   /api/v1/nba/criteria/code/CRITERION_3/context
  * PATCH /api/v1/documents/{id}/validation
and the legacy 0-mark C3 requirement being excluded from readiness.
"""

from __future__ import annotations

import uuid

from app.db.seed_phase4 import seed_phase4
from app.models.academic import AcademicYear
from app.models.phase4 import Document, NBARequirement


def _ay(db):
    return db.query(AcademicYear).first()


def test_c3_context_endpoint(db_client, db_session, hod_headers):
    seed_phase4(db_session)
    ay = _ay(db_session)
    r = db_client.get(
        "/api/v1/nba/criteria/code/CRITERION_3/context",
        params={"department": "Computer Science and Engineering", "academic_year_id": str(ay.id)},
        headers=hod_headers,
    )
    assert r.status_code == 200
    body = r.json()
    for k in ("total_subjects", "subjects_with_cos", "total_cos", "cos_with_po_map"):
        assert k in body
    assert body["attainment_formula_configured"] is False


def test_legacy_copo_requirement_inactive(db_session):
    seed_phase4(db_session)
    legacy = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_3_COPO").one()
    assert legacy.is_active is False
    active = (
        db_session.query(NBARequirement)
        .filter(NBARequirement.code.like("REQ_3_%"), NBARequirement.is_active.is_(True))
        .count()
    )
    assert active == 8


def _doc(db, ay):
    d = Document(
        original_filename="evidence.pdf",
        stored_filename=f"{uuid.uuid4()}.pdf",
        file_size_bytes=10,
        mime_type="application/pdf",
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        department="Computer Science and Engineering",
        academic_year_id=ay.id,
    )
    db.add(d)
    db.commit()
    return d


def test_document_validation_hod(db_client, db_session, hod_headers):
    d = _doc(db_session, _ay(db_session))
    r = db_client.patch(
        f"/api/v1/documents/{d.id}/validation",
        json={"validation_status": "VALIDATED"},
        headers=hod_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["validation_status"] == "VALIDATED"


def test_document_validation_rejects_bad_status(db_client, db_session, hod_headers):
    d = _doc(db_session, _ay(db_session))
    r = db_client.patch(
        f"/api/v1/documents/{d.id}/validation",
        json={"validation_status": "APPROVED_BY_ME"},
        headers=hod_headers,
    )
    assert r.status_code == 422


def test_document_validation_forbidden_for_faculty(db_client, db_session, faculty_headers):
    d = _doc(db_session, _ay(db_session))
    r = db_client.patch(
        f"/api/v1/documents/{d.id}/validation",
        json={"validation_status": "VALIDATED"},
        headers=faculty_headers,
    )
    assert r.status_code == 403
