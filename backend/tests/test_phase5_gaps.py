"""
tests/test_phase5_gaps.py

Tests for Gap Analysis, Corrective Action lifecycle, duplicate prevention, and RBAC rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.seed_phase4 import seed_phase4
from app.models.academic import AcademicYear
from app.models.phase4 import NBARequirement, RequirementEvaluation, RequirementStatus
from app.models.phase5 import ActionStatus, CorrectiveAction, Gap, GapSeverity, GapStatus
from app.services.gap_service import GapService


@pytest.fixture
def gap_test_env(db_session: Session) -> dict:
    """Setup academic year, NBA requirements, and initial records for gap testing."""
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

    reqs = db_session.query(NBARequirement).all()
    return {"academic_year": ay, "requirements": reqs}


class TestGapGenerationAndLifecycle:
    def test_gap_generation_from_failed_evaluation(
        self,
        db_session: Session,
        gap_test_env: dict,
        admin_user,
    ):
        """Failed evaluation automatically creates HIGH severity gap."""
        ay = gap_test_env["academic_year"]
        req = gap_test_env["requirements"][0]
        dept = "Computer Science and Engineering"

        # Record a FAIL evaluation
        ev = RequirementEvaluation(
            requirement_id=req.id,
            academic_year_id=ay.id,
            department=dept,
            status=RequirementStatus.FAIL.value,
            score_attained=0.0,
            max_score=req.weightage,
            mode="DETERMINISTIC",
            limitations=["Student faculty ratio deficit"],
            evaluated_by_user_id=admin_user.id,
        )
        db_session.add(ev)
        db_session.commit()

        service = GapService(db_session)
        res = service.generate_gaps_for_academic_year(
            academic_year_id=ay.id,
            department=dept,
            current_user=admin_user,
        )

        assert res.gaps_created >= 1
        gap = db_session.query(Gap).filter(Gap.requirement_id == req.id).first()
        assert gap is not None
        assert gap.severity == GapSeverity.HIGH.value
        assert gap.status == GapStatus.IDENTIFIED.value
        assert gap.identified_from_evaluation_id == ev.id

    def test_duplicate_open_gap_prevention(
        self,
        db_session: Session,
        gap_test_env: dict,
        admin_user,
    ):
        """Calling gap generation repeatedly does not create duplicate open gaps."""
        ay = gap_test_env["academic_year"]
        dept = "Computer Science and Engineering"
        service = GapService(db_session)

        # First run
        res1 = service.generate_gaps_for_academic_year(
            academic_year_id=ay.id,
            department=dept,
            current_user=admin_user,
        )
        first_created = res1.gaps_created

        # Second run immediately
        res2 = service.generate_gaps_for_academic_year(
            academic_year_id=ay.id,
            department=dept,
            current_user=admin_user,
        )
        assert res2.gaps_created == 0
        assert res2.gaps_existing == first_created

    def test_auto_resolution_when_reevaluated_pass(
        self,
        db_session: Session,
        gap_test_env: dict,
        admin_user,
    ):
        """When a requirement is reevaluated as PASS, existing open gap is resolved."""
        ay = gap_test_env["academic_year"]
        req = gap_test_env["requirements"][0]
        dept = "Computer Science and Engineering"
        service = GapService(db_session)

        # 1. Create open gap from FAIL
        ev_fail = RequirementEvaluation(
            requirement_id=req.id,
            academic_year_id=ay.id,
            department=dept,
            status=RequirementStatus.FAIL.value,
            score_attained=0.0,
            max_score=req.weightage,
            mode="DETERMINISTIC",
            evaluated_by_user_id=admin_user.id,
        )
        db_session.add(ev_fail)
        db_session.commit()
        service.generate_gaps_for_academic_year(ay.id, dept, admin_user)

        gap = db_session.query(Gap).filter(Gap.requirement_id == req.id).first()
        assert gap.status == GapStatus.IDENTIFIED.value

        # 2. Add PASS evaluation
        ev_pass = RequirementEvaluation(
            requirement_id=req.id,
            academic_year_id=ay.id,
            department=dept,
            status=RequirementStatus.PASS.value,
            score_attained=req.weightage,
            max_score=req.weightage,
            mode="DETERMINISTIC",
            evaluated_by_user_id=admin_user.id,
        )
        db_session.add(ev_pass)
        db_session.commit()


        # 3. Regenerate gaps
        service.generate_gaps_for_academic_year(ay.id, dept, admin_user)
        db_session.refresh(gap)

        assert gap.status == GapStatus.COMPLETED.value
        assert gap.resolved_at is not None


class TestCorrectiveActionRBAC:
    def test_faculty_can_update_own_action(
        self,
        db_client: TestClient,
        db_session: Session,
        gap_test_env: dict,
        admin_user,
        active_faculty_user,
    ):
        """Assigned faculty can update progress and completion notes on their own action."""
        ay = gap_test_env["academic_year"]
        req = gap_test_env["requirements"][0]

        gap = Gap(
            requirement_id=req.id,
            criterion_id=req.criterion_id,
            academic_year_id=ay.id,
            department="Computer Science and Engineering",
            title="Syllabus revision required",
            description="Missing CO-PO matrix",
            severity=GapSeverity.MEDIUM.value,
            status=GapStatus.IDENTIFIED.value,
            created_by_user_id=admin_user.id,
        )
        db_session.add(gap)
        db_session.commit()

        action = CorrectiveAction(
            gap_id=gap.id,
            title="Draft updated syllabus",
            description="Include CO4 and CO5 mappings",
            assigned_to_user_id=active_faculty_user.id,
            status=ActionStatus.IN_PROGRESS.value,
            priority="HIGH",
            created_by_user_id=admin_user.id,
        )
        db_session.add(action)
        db_session.commit()

        from app.core.security import create_access_token
        faculty_token = create_access_token(
            subject=str(active_faculty_user.id),
            roles=active_faculty_user.role_names,
        )
        headers = {"Authorization": f"Bearer {faculty_token}"}

        resp = db_client.patch(
            f"/api/v1/gaps/actions/{action.id}",
            json={
                "status": "COMPLETED",
                "completion_notes": "Syllabus updated and validated with HOD.",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["completion_notes"] == "Syllabus updated and validated with HOD."

    def test_faculty_cannot_reassign_owner(
        self,
        db_client: TestClient,
        db_session: Session,
        gap_test_env: dict,
        admin_user,
        active_faculty_user,
    ):
        """Faculty cannot reassign corrective action to another user (403 Forbidden)."""
        ay = gap_test_env["academic_year"]
        req = gap_test_env["requirements"][0]

        gap = Gap(
            requirement_id=req.id,
            criterion_id=req.criterion_id,
            academic_year_id=ay.id,
            department="Computer Science and Engineering",
            title="Lab maintenance",
            description="Verify equipment calibration",
            severity=GapSeverity.LOW.value,
            status=GapStatus.IDENTIFIED.value,
            created_by_user_id=admin_user.id,
        )
        db_session.add(gap)
        db_session.commit()

        action = CorrectiveAction(
            gap_id=gap.id,
            title="Calibrate digital oscilloscopes",
            description="Lab 204 calibration",
            assigned_to_user_id=active_faculty_user.id,
            status=ActionStatus.IN_PROGRESS.value,
            created_by_user_id=admin_user.id,
        )
        db_session.add(action)
        db_session.commit()

        from app.core.security import create_access_token
        faculty_token = create_access_token(
            subject=str(active_faculty_user.id),
            roles=active_faculty_user.role_names,
        )
        headers = {"Authorization": f"Bearer {faculty_token}"}

        resp = db_client.patch(
            f"/api/v1/gaps/actions/{action.id}",
            json={"assigned_to_user_id": str(admin_user.id)},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "Only HOD or Admin can reassign" in resp.json()["detail"]
