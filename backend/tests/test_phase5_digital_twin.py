"""
tests/test_phase5_digital_twin.py

Tests for Digital Twin snapshot and readiness analytics calculations.
Verifies deterministic rules, placeholder detection, soft-deleted record exclusion,
and API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.seed_phase4 import seed_phase4
from app.models.academic import AcademicYear, Subject
from app.models.phase4 import (
    Document,
    DocumentValidationStatus,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementStatus,
)
from app.services.digital_twin_service import DigitalTwinService


@pytest.fixture
def populated_nba_db(db_session: Session) -> AcademicYear:
    """Seed Phase 4 NBA criteria & requirements, and create an academic year."""
    seed_phase4(db_session)

    ay = AcademicYear(
        name="2026-2027",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2027, 6, 30, tzinfo=timezone.utc).date(),
        is_active=True,
    )

    db_session.add(ay)
    db_session.commit()
    db_session.refresh(ay)
    return ay


class TestDigitalTwinCalculations:
    def test_empty_department_snapshot(self, db_session: Session, populated_nba_db: AcademicYear):
        """Empty department with no evaluations should yield unevaluated requirements and null readiness."""
        service = DigitalTwinService(db_session)
        snapshot = service.get_digital_twin_snapshot(
            academic_year_id=populated_nba_db.id,
            department="Empty Engineering",
        )

        assert snapshot.overall.total_requirements > 0
        assert snapshot.overall.passed_requirements == 0
        assert snapshot.overall.warning_requirements == 0
        assert snapshot.overall.failed_requirements == 0
        assert snapshot.overall.unevaluated_requirements == snapshot.overall.total_requirements
        # When no eligible requirements are evaluated, readiness_percentage is None (null)
        assert snapshot.overall.readiness_percentage is None
        assert any("cannot be calculated" in lim for lim in snapshot.limitations)
        assert snapshot.overall.is_official_nba_score is False

    def test_deterministic_readiness_calculation(
        self,
        db_session: Session,
        populated_nba_db: AcademicYear,
        admin_user,
    ):
        """Mixed evaluation statuses should compute exact deterministic readiness."""
        service = DigitalTwinService(db_session)
        reqs = db_session.query(NBARequirement).all()
        dept = "Computer Science and Engineering"

        # Evaluate first requirement as PASS
        r1 = reqs[0]
        eval1 = RequirementEvaluation(
            requirement_id=r1.id,
            academic_year_id=populated_nba_db.id,
            department=dept,
            status=RequirementStatus.PASS.value,
            score_attained=r1.weightage,
            max_score=r1.weightage,
            mode="DETERMINISTIC",
            evaluated_by_user_id=admin_user.id,
        )
        # Evaluate second requirement as FAIL
        r2 = reqs[1]
        eval2 = RequirementEvaluation(
            requirement_id=r2.id,
            academic_year_id=populated_nba_db.id,
            department=dept,
            status=RequirementStatus.FAIL.value,
            score_attained=0.0,
            max_score=r2.weightage,
            mode="DETERMINISTIC",
            evaluated_by_user_id=admin_user.id,
        )
        # Evaluate third requirement as NOT_APPLICABLE
        r3 = reqs[2]
        eval3 = RequirementEvaluation(
            requirement_id=r3.id,
            academic_year_id=populated_nba_db.id,
            department=dept,
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=r3.weightage,
            mode="DETERMINISTIC",
            evaluated_by_user_id=admin_user.id,
        )
        db_session.add_all([eval1, eval2, eval3])
        db_session.commit()

        snapshot = service.get_digital_twin_snapshot(
            academic_year_id=populated_nba_db.id,
            department=dept,
        )

        assert snapshot.overall.passed_requirements == 1
        assert snapshot.overall.failed_requirements == 1
        assert snapshot.overall.not_applicable_requirements == 1

        # Denominator excludes NOT_APPLICABLE
        eligible = snapshot.overall.total_requirements - 1
        expected_pct = round((1 / eligible) * 100.0, 2)
        assert snapshot.overall.readiness_percentage == expected_pct

    def test_soft_deleted_documents_excluded(
        self,
        db_session: Session,
        populated_nba_db: AcademicYear,
        admin_user,
    ):
        """Soft-deleted documents must not be counted in active data completeness."""
        service = DigitalTwinService(db_session)
        dept = "Mechanical Engineering"

        doc_active = Document(
            original_filename="active.pdf",
            stored_filename="stored_active_123.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="activehash1",
            department=dept,
            academic_year_id=populated_nba_db.id,
            uploaded_by_user_id=admin_user.id,
            is_deleted=False,
            validation_status=DocumentValidationStatus.VALIDATED.value,
        )
        doc_deleted = Document(
            original_filename="deleted.pdf",
            stored_filename="stored_deleted_456.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            sha256_hash="deletedhash2",
            department=dept,
            academic_year_id=populated_nba_db.id,
            uploaded_by_user_id=admin_user.id,
            is_deleted=True,
            validation_status=DocumentValidationStatus.VALIDATED.value,
        )
        db_session.add_all([doc_active, doc_deleted])
        db_session.commit()


        comp = service.get_data_completeness(populated_nba_db.id, dept)
        assert comp.uploaded_documents_count == 1
        assert comp.validated_documents_count == 1


class TestDigitalTwinAPI:
    def test_get_snapshot_endpoint(
        self,
        db_client: TestClient,
        db_session: Session,
        populated_nba_db: AcademicYear,
        hod_headers: dict,
    ):
        """GET /api/v1/digital-twin/snapshot should return structured snapshot."""
        resp = db_client.get(
            f"/api/v1/digital-twin/snapshot?academic_year_id={populated_nba_db.id}&department=Computer Science and Engineering",
            headers=hod_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["academic_year"] == "2026-2027"
        assert "overall" in data
        assert "criteria" in data
        assert "data_completeness" in data
        assert len(data["criteria"]) >= 4

    def test_get_criterion_analytics_endpoint(
        self,
        db_client: TestClient,
        db_session: Session,
        populated_nba_db: AcademicYear,
        hod_headers: dict,
    ):
        """GET /api/v1/digital-twin/criteria/CRITERION_3 returns Criterion 3 analytics."""
        resp = db_client.get(
            f"/api/v1/digital-twin/criteria/CRITERION_3?academic_year_id={populated_nba_db.id}&department=Computer Science and Engineering",
            headers=hod_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["criterion_code"] == "CRITERION_3"
        assert len(data["requirements"]) > 0

    def test_get_criterion_not_found(
        self,
        db_client: TestClient,
        db_session: Session,
        populated_nba_db: AcademicYear,
        hod_headers: dict,
    ):
        """GET with invalid criterion code returns 404."""
        resp = db_client.get(
            f"/api/v1/digital-twin/criteria/NON_EXISTENT?academic_year_id={populated_nba_db.id}",
            headers=hod_headers,
        )
        assert resp.status_code == 404
