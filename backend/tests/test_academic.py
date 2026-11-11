"""
tests/test_academic.py

Tests for Academic Year, Subject, and Faculty Subject Assignment endpoints:
- GET /api/v1/academic-years
- POST /api/v1/academic-years
- GET /api/v1/subjects
- POST /api/v1/subjects
- POST /api/v1/subjects/{subject_id}/assignments
- GET /api/v1/faculty/{faculty_id}/subjects
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear
from app.models.faculty import FacultyProfile
from app.models.user import User


class TestAcademicYears:
    """Tests for academic year creation and retrieval."""

    def test_hod_can_create_academic_year(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        payload = {
            "name": "2027-28",
            "start_date": "2027-07-01",
            "end_date": "2028-06-30",
            "is_active": True,
        }
        response = db_client.post(
            "/api/v1/academic-years",
            headers=hod_headers,
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "2027-28"
        assert data["is_active"] is True

    def test_end_date_before_start_date_rejected(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        payload = {
            "name": "2029-30",
            "start_date": "2029-07-01",
            "end_date": "2028-06-30",  # Invalid
            "is_active": True,
        }
        response = db_client.post(
            "/api/v1/academic-years",
            headers=hod_headers,
            json=payload,
        )
        assert response.status_code == 400
        assert "after start date" in response.json()["detail"].lower()

    def test_duplicate_academic_year_name_rejected(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        payload = {
            "name": "2026-27",  # Seeded by default
            "start_date": "2026-07-01",
            "end_date": "2027-06-30",
            "is_active": True,
        }
        response = db_client.post(
            "/api/v1/academic-years",
            headers=hod_headers,
            json=payload,
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_faculty_cannot_create_academic_year(
        self, db_client: TestClient, faculty_headers: dict
    ) -> None:
        payload = {
            "name": "2030-31",
            "start_date": "2030-07-01",
            "end_date": "2031-06-30",
            "is_active": True,
        }
        response = db_client.post(
            "/api/v1/academic-years",
            headers=faculty_headers,
            json=payload,
        )
        assert response.status_code == 403

    def test_authenticated_users_can_list_academic_years(
        self, db_client: TestClient, faculty_headers: dict
    ) -> None:
        response = db_client.get("/api/v1/academic-years", headers=faculty_headers)
        assert response.status_code == 200
        names = [y["name"] for y in response.json()]
        assert "2026-27" in names


class TestSubjects:
    """Tests for Subject creation and retrieval."""

    def test_hod_can_create_subject(
        self, db_client: TestClient, hod_headers: dict, db_session: Session
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()

        payload = {
            "code": "CS601",
            "name": "Software Engineering",
            "semester": 6,
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "credits": 4.0,
        }
        response = db_client.post(
            "/api/v1/subjects",
            headers=hod_headers,
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "CS601"
        assert data["credits"] == 4.0

    def test_duplicate_subject_code_in_same_year_rejected(
        self, db_client: TestClient, hod_headers: dict, db_session: Session
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()

        payload = {
            "code": "CS602",
            "name": "Compiler Design",
            "semester": 6,
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "credits": 3.0,
        }
        res1 = db_client.post("/api/v1/subjects", headers=hod_headers, json=payload)
        assert res1.status_code == 201

        # Attempt to create subject with same code in same academic year
        res2 = db_client.post("/api/v1/subjects", headers=hod_headers, json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"].lower()

    def test_faculty_cannot_create_subject(
        self, db_client: TestClient, faculty_headers: dict, db_session: Session
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()
        payload = {
            "code": "CS603",
            "name": "Computer Networks",
            "semester": 6,
            "academic_year_id": str(year.id),
            "department": "Computer Science & Engineering",
            "credits": 3.0,
        }
        response = db_client.post("/api/v1/subjects", headers=faculty_headers, json=payload)
        assert response.status_code == 403

    def test_list_subjects_with_filters(
        self, db_client: TestClient, hod_headers: dict, faculty_headers: dict, db_session: Session
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()
        # Create subjects in different departments
        db_client.post(
            "/api/v1/subjects",
            headers=hod_headers,
            json={
                "code": "CS101",
                "name": "Intro to Programming",
                "semester": 1,
                "academic_year_id": str(year.id),
                "department": "CSE",
                "credits": 3.0,
            },
        )
        db_client.post(
            "/api/v1/subjects",
            headers=hod_headers,
            json={
                "code": "EC101",
                "name": "Basic Electronics",
                "semester": 1,
                "academic_year_id": str(year.id),
                "department": "ECE",
                "credits": 3.0,
            },
        )

        # Query all
        res_all = db_client.get("/api/v1/subjects", headers=faculty_headers)
        assert res_all.status_code == 200
        assert len(res_all.json()) >= 2

        # Query filtered by department=CSE
        res_cse = db_client.get("/api/v1/subjects?department=CSE", headers=faculty_headers)
        assert res_cse.status_code == 200
        for s in res_cse.json():
            assert s["department"] == "CSE"


class TestFacultySubjectAssignments:
    """Tests for Subject assignment to faculty and access permissions."""

    def _create_test_subject(self, client: TestClient, hod_headers: dict, session: Session) -> str:
        year = session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()
        res = client.post(
            "/api/v1/subjects",
            headers=hod_headers,
            json={
                "code": f"SUBJ_{uuid.uuid4().hex[:6]}",
                "name": "Test Subject",
                "semester": 5,
                "academic_year_id": str(year.id),
                "department": "CSE",
                "credits": 3.0,
            },
        )
        assert res.status_code == 201
        return res.json()["id"]

    def test_hod_assigns_subject_to_faculty(
        self,
        db_client: TestClient,
        hod_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        faculty_profile_id = str(active_faculty_user.faculty_profile.id)

        response = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_profile_id": faculty_profile_id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subject_id"] == subject_id
        assert data["faculty_profile_id"] == faculty_profile_id
        assert data["is_active"] is True

    def test_duplicate_active_assignment_rejected(
        self,
        db_client: TestClient,
        hod_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        faculty_profile_id = str(active_faculty_user.faculty_profile.id)

        # First assignment succeeds
        res1 = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_profile_id": faculty_profile_id},
        )
        assert res1.status_code == 201

        # Second assignment with same faculty and subject is rejected
        res2 = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_profile_id": faculty_profile_id},
        )
        assert res2.status_code == 409
        assert "already actively assigned" in res2.json()["detail"].lower()

    def test_faculty_cannot_create_assignment(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        faculty_profile_id = str(active_faculty_user.faculty_profile.id)

        response = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=faculty_headers,
            json={"faculty_profile_id": faculty_profile_id},
        )
        assert response.status_code == 403

    def test_faculty_can_view_own_assignments(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        fac_id = str(active_faculty_user.faculty_profile.id)

        # Assign subject
        db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_profile_id": fac_id},
        )

        # Faculty views their own subjects
        response = db_client.get(
            f"/api/v1/faculty/{fac_id}/subjects",
            headers=faculty_headers,
        )
        assert response.status_code == 200
        assignments = response.json()
        assert len(assignments) >= 1
        assert assignments[0]["subject_id"] == subject_id

    def test_faculty_cannot_view_other_faculty_assignments(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        hod_user: User,
    ) -> None:
        # HOD has a faculty profile
        other_faculty_id = str(hod_user.faculty_profile.id)

        # Normal faculty attempts to view HOD's assignments
        response = db_client.get(
            f"/api/v1/faculty/{other_faculty_id}/subjects",
            headers=faculty_headers,
        )
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    def test_hod_can_view_any_faculty_assignments(
        self,
        db_client: TestClient,
        hod_headers: dict,
        active_faculty_user: User,
    ) -> None:
        faculty_id = str(active_faculty_user.faculty_profile.id)
        response = db_client.get(
            f"/api/v1/faculty/{faculty_id}/subjects",
            headers=hod_headers,
        )
        assert response.status_code == 200

    def test_hod_assigns_subject_by_faculty_id_string(
        self,
        db_client: TestClient,
        hod_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        employee_id = active_faculty_user.faculty_profile.faculty_id  # e.g. "FAC001"

        response = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_id": employee_id},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subject_id"] == subject_id
        assert data["faculty_profile_id"] == str(active_faculty_user.faculty_profile.id)

    def test_faculty_can_view_own_assignments_by_employee_id_string(
        self,
        db_client: TestClient,
        hod_headers: dict,
        faculty_headers: dict,
        active_faculty_user: User,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        profile_id = str(active_faculty_user.faculty_profile.id)
        employee_id = active_faculty_user.faculty_profile.faculty_id

        # Assign subject
        db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={"faculty_profile_id": profile_id},
        )

        # Query using the employee ID string ("FAC001")
        response = db_client.get(
            f"/api/v1/faculty/{employee_id}/subjects",
            headers=faculty_headers,
        )
        assert response.status_code == 200
        assignments = response.json()
        assert len(assignments) >= 1
        assert assignments[0]["subject_id"] == subject_id

    def test_assign_subject_missing_both_identifiers_returns_400(
        self,
        db_client: TestClient,
        hod_headers: dict,
        db_session: Session,
    ) -> None:
        subject_id = self._create_test_subject(db_client, hod_headers, db_session)
        response = db_client.post(
            f"/api/v1/subjects/{subject_id}/assignments",
            headers=hod_headers,
            json={},
        )
        assert response.status_code == 400
        assert "either faculty_profile_id or faculty_id" in response.json()["detail"].lower()
