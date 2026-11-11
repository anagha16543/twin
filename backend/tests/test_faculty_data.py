"""
tests/test_faculty_data.py

Comprehensive tests for Phase 3 Faculty Data Layer:
- Qualifications CRUD and soft-deletion
- Experience records CRUD and soft-deletion
- Certificates creation (v1), version replacement (v2+), lineage history, and soft-deletion
- Publications, Patents, Trainings, Projects, Consultancies, and Contributions CRUD & soft-deletion
- Role-based authorization & ownership enforcement (Faculty isolation vs HOD / Admin access)
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.faculty import FacultyProfile
from app.models.faculty_data import FacultyCertificate, FacultyQualification
from app.models.user import User


class TestFacultyQualifications:
    """Tests for faculty qualification records and soft deletion."""

    def test_faculty_can_add_and_list_qualification(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "degree": "Ph.D. in Computer Science",
            "field_of_study": "Machine Learning & Distributed Systems",
            "institution": "National Institute of Technology",
            "university": "NIT University",
            "year_of_passing": 2020,
            "grade_or_percentage": "9.4 CGPA",
            "document_reference": "https://storage.example.com/phd_cert.pdf",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/qualifications",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["degree"] == payload["degree"]
        assert data["year_of_passing"] == 2020
        assert data["is_deleted"] is False

        # List qualifications
        list_res = db_client.get(
            "/api/v1/faculty/FAC001/qualifications",
            headers=faculty_headers,
        )
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 1
        assert items[0]["id"] == data["id"]

    def test_soft_delete_qualification(
        self,
        db_client: TestClient,
        db_session: Session,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        # Create qualification
        payload = {
            "degree": "B.Tech in Information Technology",
            "field_of_study": "Information Technology",
            "institution": "State Technical University",
            "university": "State University",
            "year_of_passing": 2014,
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/qualifications",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        qual_id = res.json()["id"]

        # Soft delete
        del_res = db_client.delete(
            f"/api/v1/faculty/qualifications/{qual_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

        # Listing should now exclude the soft-deleted record
        list_res = db_client.get(
            "/api/v1/faculty/FAC001/qualifications",
            headers=faculty_headers,
        )
        assert list_res.status_code == 200
        ids = [q["id"] for q in list_res.json()]
        assert qual_id not in ids

        # Verify DB state directly: is_deleted is True, deleted_at is recorded
        db_record = db_session.query(FacultyQualification).filter(FacultyQualification.id == uuid.UUID(qual_id)).first()
        assert db_record is not None
        assert db_record.is_deleted is True
        assert db_record.deleted_at is not None

        # Re-attempting delete returns 404
        del_res2 = db_client.delete(
            f"/api/v1/faculty/qualifications/{qual_id}",
            headers=faculty_headers,
        )
        assert del_res2.status_code == 404


class TestFacultyExperience:
    """Tests for faculty work experience records and soft deletion."""

    def test_faculty_can_add_experience(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "designation": "Assistant Professor",
            "organization": "ABC Institute of Technology",
            "experience_type": "Teaching",
            "start_date": "2020-08-01",
            "is_current": True,
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/experiences",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["organization"] == payload["organization"]
        assert data["designation"] == payload["designation"]
        assert data["is_current"] is True

        list_res = db_client.get(
            "/api/v1/faculty/FAC001/experiences",
            headers=faculty_headers,
        )
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

    def test_soft_delete_experience(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "designation": "Software Research Engineer",
            "organization": "Prior Tech Labs",
            "experience_type": "Industry",
            "start_date": "2018-06-01",
            "end_date": "2020-07-15",
            "is_current": False,
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/experiences",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        exp_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/experiences/{exp_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

        list_res = db_client.get(
            "/api/v1/faculty/FAC001/experiences",
            headers=faculty_headers,
        )
        ids = [e["id"] for e in list_res.json()]
        assert exp_id not in ids


class TestFacultyCertificatesAndVersioning:
    """Tests for certificate creation, version replacement, lineage history, and soft deletion."""

    def test_certificate_versioning_and_lineage_replacement(
        self,
        db_client: TestClient,
        db_session: Session,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        # 1. Create initial certificate (v1)
        create_payload = {
            "title": "AWS Certified Solutions Architect",
            "issuing_organization": "Amazon Web Services",
            "issue_date": "2022-01-15",
            "expiry_date": "2025-01-15",
            "credential_id": "AWS-12345678",
            "document_reference": "https://storage.example.com/aws_v1.pdf",
        }
        v1_res = db_client.post(
            "/api/v1/faculty/FAC001/certificates",
            headers=faculty_headers,
            json=create_payload,
        )
        assert v1_res.status_code == 201
        v1_data = v1_res.json()
        v1_id = v1_data["id"]
        assert v1_data["version"] == 1
        assert v1_data["is_current"] is True
        assert v1_data["parent_certificate_id"] is None

        # 2. Replace with new certificate version (v2)
        replace_payload = {
            "title": "AWS Certified Solutions Architect - Professional",
            "issue_date": "2025-01-10",
            "expiry_date": "2028-01-10",
            "credential_id": "AWS-87654321",
            "document_reference": "https://storage.example.com/aws_v2.pdf",
        }
        v2_res = db_client.post(
            f"/api/v1/faculty/certificates/{v1_id}/replace",
            headers=faculty_headers,
            json=replace_payload,
        )
        assert v2_res.status_code == 201
        v2_data = v2_res.json()
        v2_id = v2_data["id"]
        assert v2_data["version"] == 2
        assert v2_data["is_current"] is True
        assert v2_data["parent_certificate_id"] == v1_id

        # Verify old v1 certificate is now is_current = False in DB
        v1_db = db_session.query(FacultyCertificate).filter(FacultyCertificate.id == uuid.UUID(v1_id)).first()
        assert v1_db.is_current is False

        # 3. Active certificates list should only return current certificates (v2, not v1)
        list_res = db_client.get(
            "/api/v1/faculty/FAC001/certificates",
            headers=faculty_headers,
        )
        assert list_res.status_code == 200
        current_certs = list_res.json()
        assert len(current_certs) == 1
        assert current_certs[0]["id"] == v2_id
        assert current_certs[0]["version"] == 2

        # 4. Certificate version history endpoint returns full lineage (v1 and v2)
        history_res = db_client.get(
            f"/api/v1/faculty/certificates/{v2_id}/history",
            headers=faculty_headers,
        )
        assert history_res.status_code == 200
        history_items = history_res.json()
        assert len(history_items) == 2
        versions = [h["version"] for h in history_items]
        assert versions == [1, 2]

        # 5. Soft delete v2 certificate
        del_res = db_client.delete(
            f"/api/v1/faculty/certificates/{v2_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

        # Verify active list is now empty
        list_res2 = db_client.get(
            "/api/v1/faculty/FAC001/certificates",
            headers=faculty_headers,
        )
        assert list_res2.status_code == 200
        assert len(list_res2.json()) == 0


class TestFacultyAchievementsCRUD:
    """Tests for Publications, Patents, Trainings, Projects, Consultancies, and Contributions."""

    def test_publication_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "title": "Deep Learning for NBA Performance Analysis",
            "publication_type": "Journal",
            "journal_or_conference_name": "IEEE Transactions on AI",
            "indexing": "SCOPUS, SCI",
            "doi_or_url": "10.1109/TAI.2023.001",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/publications",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        pub_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/publications/{pub_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

    def test_patent_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "title": "Smart IoT System for Automated Classroom Analytics",
            "application_number": "202341012345",
            "filing_date": "2023-04-12",
            "status": "Published",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/patents",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        patent_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/patents/{patent_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

    def test_training_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "title": "AICTE ATAL FDP on Cloud-Native Systems",
            "program_type": "FDP",
            "organization": "IIT Bombay",
            "start_date": "2023-06-10",
            "end_date": "2023-06-15",
            "duration_days": 5,
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/trainings",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        training_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/trainings/{training_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

    def test_project_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "title": "Autonomous Edge Computing Infrastructure for Smart Cities",
            "funding_agency": "DST - SERB",
            "grant_amount": 2500000.0,
            "status": "Ongoing",
            "start_date": "2023-01-01",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/projects",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        project_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/projects/{project_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

    def test_consultancy_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "project_title": "Enterprise Microservices Architecture Migration",
            "client_organization": "TechCorp Global Services",
            "financial_outlay": 450000.0,
            "start_date": "2023-02-01",
            "status": "Completed",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/consultancies",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        consultancy_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/consultancies/{consultancy_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204

    def test_contribution_crud(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
    ) -> None:
        payload = {
            "title": "NBA Criterion 5 Coordinator",
            "category": "Departmental Administration",
            "description": "Criterion 5 Faculty Information Coordinator",
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/contributions",
            headers=faculty_headers,
            json=payload,
        )
        assert res.status_code == 201
        contrib_id = res.json()["id"]

        del_res = db_client.delete(
            f"/api/v1/faculty/contributions/{contrib_id}",
            headers=faculty_headers,
        )
        assert del_res.status_code == 204


class TestFacultyOwnershipAndAuthorization:
    """Tests isolating faculty data from cross-faculty manipulation while permitting HOD and Admin."""

    def test_faculty_cannot_create_or_view_other_faculty_records(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        second_faculty_headers: dict,
    ) -> None:
        # Faculty 2 attempts to add a qualification to Faculty 1's profile
        payload = {
            "degree": "Unauthorized Entry",
            "field_of_study": "Cyber Attack",
            "institution": "Dark Web Academy",
            "university": "Dark Web",
            "year_of_passing": 2022,
        }
        res = db_client.post(
            "/api/v1/faculty/FAC001/qualifications",
            headers=second_faculty_headers,
            json=payload,
        )
        assert res.status_code == 403
        assert "not authorized" in res.json()["detail"].lower()

        # Faculty 2 attempts to list Faculty 1's qualifications
        list_res = db_client.get(
            "/api/v1/faculty/FAC001/qualifications",
            headers=second_faculty_headers,
        )
        assert list_res.status_code == 403

    def test_hod_and_admin_can_view_faculty_records(
        self,
        db_client: TestClient,
        active_faculty_user: User,
        faculty_headers: dict,
        hod_headers: dict,
        admin_headers: dict,
    ) -> None:
        # Faculty 1 creates qualification
        payload = {
            "degree": "M.Tech in Software Engineering",
            "field_of_study": "Software Systems",
            "institution": "National University",
            "university": "National Tech University",
            "year_of_passing": 2017,
        }
        db_client.post(
            "/api/v1/faculty/FAC001/qualifications",
            headers=faculty_headers,
            json=payload,
        )

        # HOD can view Faculty 1's qualifications
        hod_res = db_client.get(
            "/api/v1/faculty/FAC001/qualifications",
            headers=hod_headers,
        )
        assert hod_res.status_code == 200
        assert len(hod_res.json()) >= 1

        # Admin can view Faculty 1's qualifications
        admin_res = db_client.get(
            "/api/v1/faculty/FAC001/qualifications",
            headers=admin_headers,
        )
        assert admin_res.status_code == 200
        assert len(admin_res.json()) >= 1
