"""
tests/test_phase4_requirements.py

Comprehensive tests for Phase 4 Milestone A:
  - NBA Criteria and Requirements models and constraints
  - Idempotent seeding
  - Extensible deterministic evaluation framework (C3, C4, C5, C6)
  - Unknown rule keys and missing data handling (WARNING, never PASS)
  - Explicit applicability (NOT_APPLICABLE)
  - Evaluation history preservation (immutable inserts)
  - API endpoints and role-based access control (HOD/ADMIN only for evaluation)
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.business_rules.readiness_rules import (
    EvaluationResult,
    RequirementStatus,
    evaluate_requirement,
    load_all_rules,
)
from app.business_rules.criterion3_rules import evaluate_co_completeness
from app.business_rules.criterion4_rules import evaluate_pass_percentage
from app.business_rules.criterion5_rules import evaluate_faculty_qualification
from app.business_rules.criterion6_rules import evaluate_lab_facility
from app.db.seed_phase4 import seed_phase4
from app.models.academic import AcademicYear
from app.models.phase4 import (
    EvaluationMode,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
)
from app.models.user import User


# Load rules before running tests
load_all_rules()


class TestNBAModelsAndConstraints:
    """Test database schema, constraints, and relationships for NBA entities."""

    def test_seeded_criteria_present(self, db_session: Session):
        """Verify that Criteria 3, 4, 5, and 6 are seeded."""
        criteria = db_session.query(NBACriterion).all()
        codes = {c.code for c in criteria}
        assert "CRITERION_3" in codes
        assert "CRITERION_4" in codes
        assert "CRITERION_5" in codes
        assert "CRITERION_6" in codes

    def test_seeded_requirements_linked_to_criteria(self, db_session: Session):
        """Verify requirements are linked to their respective criteria."""
        c3 = db_session.query(NBACriterion).filter(NBACriterion.code == "CRITERION_3").first()
        assert c3 is not None
        assert len(c3.requirements) >= 2
        req_codes = {r.code for r in c3.requirements}
        assert "REQ_3_1" in req_codes
        assert "REQ_3_2" in req_codes

    def test_criterion_code_unique_constraint(self, db_session: Session):
        """Duplicate criterion code raises IntegrityError."""
        dup = NBACriterion(
            code="CRITERION_3",
            name="Duplicate Criterion 3",
            max_marks=100.0,
        )
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_requirement_code_unique_constraint(self, db_session: Session):
        """Duplicate requirement code raises IntegrityError."""
        c3 = db_session.query(NBACriterion).filter(NBACriterion.code == "CRITERION_3").first()
        dup = NBARequirement(
            criterion_id=c3.id,
            code="REQ_3_1",
            title="Duplicate Req",
            evaluation_rule_key="dummy.key",
        )
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_seed_phase4_idempotent(self, db_session: Session):
        """Running seed_phase4 multiple times produces no duplicates."""
        count_crit_before = db_session.query(NBACriterion).count()
        count_req_before = db_session.query(NBARequirement).count()

        seed_phase4(db_session)
        seed_phase4(db_session)

        assert db_session.query(NBACriterion).count() == count_crit_before
        assert db_session.query(NBARequirement).count() == count_req_before


class TestDeterministicEvaluationEngine:
    """Test deterministic business rule evaluations for C3, C4, C5, C6 and edge cases."""

    def test_criterion3_co_completeness_pass(self):
        result = evaluate_co_completeness({"total_subjects": 10, "subjects_with_cos": 10})
        assert result.status == RequirementStatus.PASS
        assert result.score_attained == 10.0
        assert result.max_score == 10.0
        assert result.deterministic_metrics["co_coverage_pct"] == 100.0

    def test_criterion3_co_completeness_warning(self):
        result = evaluate_co_completeness({"total_subjects": 10, "subjects_with_cos": 8})
        assert result.status == RequirementStatus.WARNING
        assert result.score_attained == 8.0

    def test_criterion3_co_completeness_fail(self):
        result = evaluate_co_completeness({"total_subjects": 10, "subjects_with_cos": 5})
        assert result.status == RequirementStatus.FAIL
        assert result.score_attained == 5.0

    def test_criterion3_co_completeness_not_applicable(self):
        result = evaluate_co_completeness({"total_subjects": 0, "subjects_with_cos": 0})
        assert result.status == RequirementStatus.NOT_APPLICABLE
        assert result.score_attained == 0.0

    def test_criterion3_missing_data_returns_warning(self):
        """Missing context keys must produce WARNING, never PASS."""
        result = evaluate_co_completeness({})
        assert result.status == RequirementStatus.WARNING
        assert len(result.limitations) > 0

    def test_criterion4_pass_percentage_pass(self):
        result = evaluate_pass_percentage({"registered_students": 100, "passed_students": 85})
        assert result.status == RequirementStatus.PASS
        assert result.score_attained > 0.0

    def test_criterion4_pass_percentage_warning(self):
        result = evaluate_pass_percentage({"registered_students": 100, "passed_students": 65})
        assert result.status == RequirementStatus.WARNING

    def test_criterion4_pass_percentage_fail(self):
        result = evaluate_pass_percentage({"registered_students": 100, "passed_students": 45})
        assert result.status == RequirementStatus.FAIL

    def test_criterion4_missing_data_returns_warning(self):
        result = evaluate_pass_percentage({})
        assert result.status == RequirementStatus.WARNING

    def test_criterion5_qualification_ratio(self):
        result = evaluate_faculty_qualification({
            "total_faculty": 20,
            "faculty_with_pg_or_phd": 18,
        })
        assert result.status == RequirementStatus.PASS
        assert result.deterministic_metrics["qualification_ratio_pct"] == 90.0

    def test_criterion5_missing_data_returns_warning(self):
        result = evaluate_faculty_qualification({})
        assert result.status == RequirementStatus.WARNING

    def test_criterion6_lab_availability(self):
        result = evaluate_lab_facility({
            "labs_required": 8,
            "labs_available": 8,
        })
        assert result.status == RequirementStatus.PASS

    def test_criterion6_missing_data_returns_warning(self):
        result = evaluate_lab_facility({})
        assert result.status == RequirementStatus.WARNING

    def test_unknown_rule_key_returns_warning(self):
        """Unknown rule keys must return WARNING, never PASS or unhandled error."""
        result = evaluate_requirement("nonexistent.fake.rule", {"any": 123})
        assert result.status == RequirementStatus.WARNING
        assert "No evaluation rule is registered" in result.limitations[0]


class TestRequirementsAPIs:
    """Test REST API endpoints for NBA criteria, requirements, and evaluations."""

    def test_unauthenticated_cannot_list_criteria(self, db_client: TestClient):
        res = db_client.get("/api/v1/nba/criteria")
        assert res.status_code == 401

    def test_authenticated_can_list_criteria(self, db_client: TestClient, faculty_headers: dict):
        res = db_client.get("/api/v1/nba/criteria", headers=faculty_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4
        codes = [c["code"] for c in data]
        assert "CRITERION_3" in codes

    def test_get_single_criterion(self, db_client: TestClient, db_session: Session, faculty_headers: dict):
        crit = db_session.query(NBACriterion).filter(NBACriterion.code == "CRITERION_3").first()
        res = db_client.get(f"/api/v1/nba/criteria/{crit.id}", headers=faculty_headers)
        assert res.status_code == 200
        assert res.json()["code"] == "CRITERION_3"

    def test_get_criterion_not_found(self, db_client: TestClient, faculty_headers: dict):
        fake_id = uuid.uuid4()
        res = db_client.get(f"/api/v1/nba/criteria/{fake_id}", headers=faculty_headers)
        assert res.status_code == 404

    def test_list_requirements_for_criterion(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        crit = db_session.query(NBACriterion).filter(NBACriterion.code == "CRITERION_3").first()
        res = db_client.get(f"/api/v1/nba/criteria/{crit.id}/requirements", headers=faculty_headers)
        assert res.status_code == 200
        reqs = res.json()
        assert len(reqs) >= 2
        assert any(r["code"] == "REQ_3_1" for r in reqs)

    def test_faculty_cannot_trigger_evaluation(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        req = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_3_1").first()
        year = db_session.query(AcademicYear).first()
        payload = {
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "context": {"total_subjects": 10, "subjects_with_cos": 10},
        }
        res = db_client.post(
            f"/api/v1/nba/requirements/{req.id}/evaluate",
            json=payload,
            headers=faculty_headers,
        )
        assert res.status_code == 403

    def test_hod_can_trigger_evaluation(
        self, db_client: TestClient, db_session: Session, hod_headers: dict
    ):
        req = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_3_1").first()
        year = db_session.query(AcademicYear).first()
        payload = {
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "context": {"total_subjects": 10, "subjects_with_cos": 10},
            "notes": "Automated evaluation run by HOD",
        }
        res = db_client.post(
            f"/api/v1/nba/requirements/{req.id}/evaluate",
            json=payload,
            headers=hod_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "PASS"
        assert data["score_attained"] == 10.0
        assert data["mode"] == EvaluationMode.DETERMINISTIC.value
        assert data["deterministic_metrics"]["co_coverage_pct"] == 100.0

    def test_evaluation_preserves_history_immutable(
        self, db_client: TestClient, db_session: Session, hod_headers: dict, faculty_headers: dict
    ):
        """Repeated evaluations create new historical records, preserving the trail."""
        req = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_3_1").first()
        year = db_session.query(AcademicYear).first()

        # Run 1: with partial data -> WARNING
        payload1 = {
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "context": {"total_subjects": 10, "subjects_with_cos": 8},
        }
        res1 = db_client.post(
            f"/api/v1/nba/requirements/{req.id}/evaluate",
            json=payload1,
            headers=hod_headers,
        )
        assert res1.status_code == 201
        assert res1.json()["status"] == "WARNING"

        # Run 2: full data -> PASS
        payload2 = {
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "context": {"total_subjects": 10, "subjects_with_cos": 10},
        }
        res2 = db_client.post(
            f"/api/v1/nba/requirements/{req.id}/evaluate",
            json=payload2,
            headers=hod_headers,
        )
        assert res2.status_code == 201
        assert res2.json()["status"] == "PASS"

        # Check history endpoint
        hist_res = db_client.get(
            f"/api/v1/nba/requirements/{req.id}/evaluations",
            headers=faculty_headers,
        )
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) >= 2
        # Most recent first
        assert history[0]["status"] == "PASS"
        assert history[1]["status"] == "WARNING"
