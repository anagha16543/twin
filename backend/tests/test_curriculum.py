"""
tests/test_curriculum.py

Comprehensive tests for Phase 3 Curriculum, Outcomes, Assessments, Attendance, and Students:
- Students registration, uniqueness, and listing
- Subject enrolments and duplicate prevention
- Program Outcomes (POs) & Program-Specific Outcomes (PSOs) creation and uniqueness
- Course Outcomes (COs) creation and per-subject code uniqueness
- CO-PO and CO-PSO mappings with 1-3 correlation level validation
- Assessment schemes creation and student marks entry with range checks (0 <= marks <= max_marks)
- Attendance records with validation (attended <= held) and automated percentage calculation
- Micro-projects creation and evaluations
- Feedback surveys with rating validation (1.0 to 5.0)
- Role-based and subject-assignment authorization (Assigned Faculty vs Unassigned Faculty vs HOD / Admin)
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear
from app.models.user import User


def _get_academic_year(db_session: Session) -> AcademicYear:
    return db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()


def _create_subject(db_client: TestClient, hod_headers: dict, year_id: str, code: str = "CS501") -> str:
    res = db_client.post(
        "/api/v1/subjects",
        headers=hod_headers,
        json={
            "code": code,
            "name": f"Subject {code}",
            "semester": 5,
            "academic_year_id": year_id,
            "department": "Computer Science & Engineering",
            "credits": 4.0,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _assign_faculty(db_client: TestClient, hod_headers: dict, subject_id: str, faculty_profile_id: str) -> None:
    res = db_client.post(
        f"/api/v1/subjects/{subject_id}/assignments",
        headers=hod_headers,
        json={"faculty_profile_id": faculty_profile_id},
    )
    assert res.status_code == 201


class TestStudentsAndEnrolments:
    """Tests for Student registration and Subject Enrolments."""

    def test_hod_can_create_student(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        payload = {
            "usn": "1MS21CS001",
            "full_name": "Bob Smith",
            "email": "bob.smith@student.example.com",
            "department": "Computer Science & Engineering",
            "current_semester": 5,
            "academic_year_id": str(year.id),
        }
        res = db_client.post("/api/v1/students", headers=hod_headers, json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["usn"] == "1MS21CS001"
        assert data["full_name"] == "Bob Smith"

    def test_duplicate_usn_rejected(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        payload = {
            "usn": "1MS21CS002",
            "full_name": "Charlie Brown",
            "department": "Computer Science & Engineering",
            "current_semester": 5,
            "academic_year_id": str(year.id),
        }
        res1 = db_client.post("/api/v1/students", headers=hod_headers, json=payload)
        assert res1.status_code == 201

        # Attempt to insert identical USN
        res2 = db_client.post("/api/v1/students", headers=hod_headers, json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"].lower()

    def test_faculty_cannot_create_student(
        self,
        db_client: TestClient,
        faculty_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        payload = {
            "usn": "1MS21CS003",
            "full_name": "David Miller",
            "department": "Computer Science & Engineering",
            "current_semester": 5,
            "academic_year_id": str(year.id),
        }
        res = db_client.post("/api/v1/students", headers=faculty_headers, json=payload)
        assert res.status_code == 403

    def test_subject_enrolment_and_duplicate_rejection(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS502")

        # Create student
        student_res = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS010",
                "full_name": "Eve Adams",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        assert student_res.status_code == 201
        student_id = student_res.json()["id"]

        # Enrol student in subject
        enrol_payload = {
            "student_id": student_id,
            "academic_year_id": str(year.id),
        }
        enrol_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/enrolments",
            headers=hod_headers,
            json=enrol_payload,
        )
        assert enrol_res.status_code == 201
        assert enrol_res.json()["is_active"] is True

        # Duplicate enrolment returns 409
        dup_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/enrolments",
            headers=hod_headers,
            json=enrol_payload,
        )
        assert dup_res.status_code == 409


class TestProgramOutcomesAndPSOs:
    """Tests for PO and PSO creation and department uniqueness."""

    def test_create_po_and_uniqueness(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        payload = {
            "code": "PO1",
            "description": "Engineering Knowledge: Apply mathematics and engineering principles to solve problems.",
            "department": "Computer Science & Engineering",
            "academic_year_id": str(year.id),
        }
        res1 = db_client.post("/api/v1/program-outcomes", headers=hod_headers, json=payload)
        assert res1.status_code == 201
        assert res1.json()["code"] == "PO1"

        # Duplicate PO code in same department rejected
        res2 = db_client.post("/api/v1/program-outcomes", headers=hod_headers, json=payload)
        assert res2.status_code == 409

    def test_create_pso_and_uniqueness(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        payload = {
            "code": "PSO1",
            "description": "Design and develop scalable AI and cloud architectures.",
            "department": "Computer Science & Engineering",
            "academic_year_id": str(year.id),
        }
        res1 = db_client.post("/api/v1/program-specific-outcomes", headers=hod_headers, json=payload)
        assert res1.status_code == 201
        assert res1.json()["code"] == "PSO1"

        # Duplicate PSO code in same department rejected
        res2 = db_client.post("/api/v1/program-specific-outcomes", headers=hod_headers, json=payload)
        assert res2.status_code == 409


class TestCourseOutcomesAndMappings:
    """Tests for CO creation and CO-PO / CO-PSO matrix mappings."""

    def test_create_co_and_duplicate_rejection(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS503")

        co_payload = {
            "code": "CO1",
            "description": "Understand fundamentals of cloud architectures and microservices.",
        }
        res1 = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=hod_headers,
            json=co_payload,
        )
        assert res1.status_code == 201
        assert res1.json()["code"] == "CO1"

        # Duplicate CO code for same subject rejected
        res2 = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=hod_headers,
            json=co_payload,
        )
        assert res2.status_code == 409

    def test_co_po_and_pso_mappings(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS504")

        # Create CO
        co_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=hod_headers,
            json={"code": "CO1", "description": "Master asynchronous database operations."},
        )
        co_id = co_res.json()["id"]

        # Create PO & PSO
        po_res = db_client.post(
            "/api/v1/program-outcomes",
            headers=hod_headers,
            json={
                "code": "PO2",
                "description": "Problem Analysis: Identify, formulate, and analyze engineering problems.",
                "department": "Computer Science & Engineering",
            },
        )
        po_id = po_res.json()["id"]

        pso_res = db_client.post(
            "/api/v1/program-specific-outcomes",
            headers=hod_headers,
            json={
                "code": "PSO2",
                "description": "Implement enterprise secure software systems.",
                "department": "Computer Science & Engineering",
            },
        )
        pso_id = pso_res.json()["id"]

        # Map CO to PO (valid correlation level 3 = High)
        map_po_res = db_client.post(
            f"/api/v1/course-outcomes/{co_id}/po-mappings",
            headers=hod_headers,
            json={"program_outcome_id": po_id, "correlation_level": 3},
        )
        assert map_po_res.status_code == 201
        assert map_po_res.json()["correlation_level"] == 3

        # Duplicate mapping rejected
        dup_po_res = db_client.post(
            f"/api/v1/course-outcomes/{co_id}/po-mappings",
            headers=hod_headers,
            json={"program_outcome_id": po_id, "correlation_level": 2},
        )
        assert dup_po_res.status_code == 409

        # Invalid correlation level (e.g. 5) rejected by schema validation
        inv_res = db_client.post(
            f"/api/v1/course-outcomes/{co_id}/po-mappings",
            headers=hod_headers,
            json={"program_outcome_id": po_id, "correlation_level": 5},
        )
        assert inv_res.status_code == 422

        # Map CO to PSO
        map_pso_res = db_client.post(
            f"/api/v1/course-outcomes/{co_id}/pso-mappings",
            headers=hod_headers,
            json={"program_specific_outcome_id": pso_id, "correlation_level": 2},
        )
        assert map_pso_res.status_code == 201
        assert map_pso_res.json()["correlation_level"] == 2


class TestAssessmentSchemesAndMarks:
    """Tests for CIE / SEE assessment schemes and student mark entries."""

    def test_assessment_scheme_and_marks(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS505")

        # Create scheme
        scheme_payload = {
            "name": "CIE-I",
            "assessment_type": "CIE-I",
            "max_marks": 50.0,
            "weightage": 20.0,
        }
        scheme_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/assessment-schemes",
            headers=hod_headers,
            json=scheme_payload,
        )
        assert scheme_res.status_code == 201
        scheme_id = scheme_res.json()["id"]

        # Duplicate scheme name for subject rejected
        dup_scheme_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/assessment-schemes",
            headers=hod_headers,
            json=scheme_payload,
        )
        assert dup_scheme_res.status_code == 409

        # Create student
        student_res = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS020",
                "full_name": "Frank White",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        student_id = student_res.json()["id"]

        # Record mark (42.5 out of 50)
        mark_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/marks",
            headers=hod_headers,
            json={
                "student_id": student_id,
                "assessment_scheme_id": scheme_id,
                "marks_obtained": 42.5,
                "is_absent": False,
            },
        )
        assert mark_res.status_code == 201
        assert mark_res.json()["marks_obtained"] == 42.5

        # Duplicate mark for same student and scheme rejected
        dup_mark_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/marks",
            headers=hod_headers,
            json={
                "student_id": student_id,
                "assessment_scheme_id": scheme_id,
                "marks_obtained": 45.0,
            },
        )
        assert dup_mark_res.status_code == 409

        # Marks exceeding max_marks (e.g. 55 out of 50) rejected with 400
        student_res2 = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS021",
                "full_name": "Grace Hopper",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        student2_id = student_res2.json()["id"]

        inv_mark_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/marks",
            headers=hod_headers,
            json={
                "student_id": student2_id,
                "assessment_scheme_id": scheme_id,
                "marks_obtained": 55.0,  # > 50 max_marks
            },
        )
        assert inv_mark_res.status_code == 400


class TestAttendanceRecords:
    """Tests for attendance tracking and validation."""

    def test_attendance_calculation_and_validation(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS506")

        # Create student
        student_res = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS030",
                "full_name": "Heidi Green",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        student_id = student_res.json()["id"]

        # Record valid attendance (36 out of 40 = 90.0%)
        att_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/attendance",
            headers=hod_headers,
            json={
                "student_id": student_id,
                "academic_year_id": str(year.id),
                "classes_held": 40,
                "classes_attended": 36,
            },
        )
        assert att_res.status_code == 201
        data = att_res.json()
        assert data["attendance_percentage"] == 90.0

        # Duplicate attendance record rejected
        dup_att = db_client.post(
            f"/api/v1/subjects/{subject_id}/attendance",
            headers=hod_headers,
            json={
                "student_id": student_id,
                "academic_year_id": str(year.id),
                "classes_held": 40,
                "classes_attended": 38,
            },
        )
        assert dup_att.status_code == 409

        # Attended > Held (e.g. 45 out of 40) rejected with 400
        student_res2 = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS031",
                "full_name": "Ivan Rogers",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        student2_id = student_res2.json()["id"]

        inv_att = db_client.post(
            f"/api/v1/subjects/{subject_id}/attendance",
            headers=hod_headers,
            json={
                "student_id": student2_id,
                "academic_year_id": str(year.id),
                "classes_held": 40,
                "classes_attended": 45,  # Invalid
            },
        )
        assert inv_att.status_code == 400


class TestMicroProjectsAndSurveys:
    """Tests for micro-project evaluations and stakeholder feedback surveys."""

    def test_micro_project_creation(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS507")

        student_res = db_client.post(
            "/api/v1/students",
            headers=hod_headers,
            json={
                "usn": "1MS21CS040",
                "full_name": "Jack Vance",
                "department": "Computer Science & Engineering",
                "current_semester": 5,
                "academic_year_id": str(year.id),
            },
        )
        student_id = student_res.json()["id"]

        project_res = db_client.post(
            f"/api/v1/subjects/{subject_id}/micro-projects",
            headers=hod_headers,
            json={
                "student_id": student_id,
                "academic_year_id": str(year.id),
                "title": "Automated NBA Readiness Metric Analyzer",
                "marks_obtained": 9.5,
                "max_marks": 10.0,
                "status": "COMPLETED",
            },
        )
        assert project_res.status_code == 201
        assert project_res.json()["title"] == "Automated NBA Readiness Metric Analyzer"

    def test_feedback_survey_and_rating_validation(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS508")

        # Submit valid survey (rating 4.5 out of 5.0)
        res = db_client.post(
            "/api/v1/feedback-surveys",
            headers=faculty_headers,
            json={
                "survey_type": "Course Exit Survey",
                "academic_year_id": str(year.id),
                "subject_id": subject_id,
                "stakeholder_type": "STUDENT",
                "rating": 4.5,
                "comments": "Excellent curriculum delivery and clear lab assignments.",
            },
        )
        assert res.status_code == 201
        assert res.json()["rating"] == 4.5

        # Invalid rating > 5.0 (e.g. 6.0) rejected by validation
        inv_res = db_client.post(
            "/api/v1/feedback-surveys",
            headers=faculty_headers,
            json={
                "survey_type": "Course Exit Survey",
                "academic_year_id": str(year.id),
                "stakeholder_type": "STUDENT",
                "rating": 6.0,  # Invalid
            },
        )
        assert inv_res.status_code == 422

        # Listing feedback surveys is restricted to HOD or Admin
        hod_list = db_client.get(
            f"/api/v1/feedback-surveys?subject_id={subject_id}",
            headers=hod_headers,
        )
        assert hod_list.status_code == 200
        assert len(hod_list.json()) >= 1

        faculty_list = db_client.get(
            f"/api/v1/feedback-surveys?subject_id={subject_id}",
            headers=faculty_headers,
        )
        assert faculty_list.status_code == 403


class TestSubjectAuthorization:
    """Tests confirming that only assigned faculty, HOD, or Admin can modify subject data."""

    def test_unassigned_faculty_forbidden_from_modifying_subject(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        second_faculty_headers: dict,
        active_faculty_user: User,
        second_faculty_user: User,
        db_session: Session,
    ) -> None:
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS509")

        # Assign Faculty 1 (active_faculty_user) to the subject
        _assign_faculty(db_client, hod_headers, subject_id, str(active_faculty_user.faculty_profile.id))

        # Faculty 1 (assigned) CAN create a Course Outcome
        res_assigned = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=faculty_headers,
            json={"code": "CO1", "description": "Formulate stateful systems."},
        )
        assert res_assigned.status_code == 201

        # Faculty 2 (unassigned) CANNOT create a Course Outcome for this subject
        res_unassigned = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=second_faculty_headers,
            json={"code": "CO2", "description": "Unauthorized outcome."},
        )
        assert res_unassigned.status_code == 403
        assert "not assigned" in res_unassigned.json()["detail"].lower()

    def test_admin_cannot_edit_academic_records(
        self,
        db_client: TestClient,
        hod_headers: dict,
        admin_headers: dict,
        db_session: Session,
    ) -> None:
        """Admin does not automatically receive unrestricted academic-data editing permissions."""
        year = _get_academic_year(db_session)
        subject_id = _create_subject(db_client, hod_headers, str(year.id), code="CS510")

        # Admin attempts to create a Course Outcome -> 403 Forbidden
        res_co = db_client.post(
            f"/api/v1/subjects/{subject_id}/course-outcomes",
            headers=admin_headers,
            json={"code": "CO1", "description": "Admin tampering test."},
        )
        assert res_co.status_code == 403
        assert "administrators do not have academic data editing permissions" in res_co.json()["detail"].lower()

        # Admin attempts to record attendance -> 403 Forbidden
        res_att = db_client.post(
            f"/api/v1/subjects/{subject_id}/attendance",
            headers=admin_headers,
            json={
                "student_id": str(uuid.uuid4()),
                "academic_year_id": str(year.id),
                "classes_held": 40,
                "classes_attended": 35,
            },
        )
        assert res_att.status_code == 403

        # However, Admin CAN inspect / read subject marks and attendance (monitoring/audit)
        res_read_marks = db_client.get(
            f"/api/v1/subjects/{subject_id}/marks",
            headers=admin_headers,
        )
        assert res_read_marks.status_code == 200

        res_read_att = db_client.get(
            f"/api/v1/subjects/{subject_id}/attendance",
            headers=admin_headers,
        )
        assert res_read_att.status_code == 200

    def test_unauthenticated_requests_rejected(
        self,
        db_client: TestClient,
        db_session: Session,
    ) -> None:
        """Verify unauthenticated requests are strictly rejected with 401."""
        year = _get_academic_year(db_session)
        fake_uuid = str(uuid.uuid4())

        # No auth header on protected routes
        assert db_client.post("/api/v1/students", json={}).status_code == 401
        assert db_client.post(f"/api/v1/subjects/{fake_uuid}/course-outcomes", json={}).status_code == 401
        assert db_client.post(f"/api/v1/subjects/{fake_uuid}/marks", json={}).status_code == 401
        assert db_client.post(f"/api/v1/subjects/{fake_uuid}/attendance", json={}).status_code == 401
        assert db_client.get("/api/v1/feedback-surveys").status_code == 401
