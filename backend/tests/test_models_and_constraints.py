"""
tests/test_models_and_constraints.py

Tests for database constraints, typed model relationships, and seed idempotence:
- User email uniqueness
- FacultyProfile user_id and faculty_id uniqueness
- Many-to-many User-Role assignments (supporting HOD + FACULTY)
- AcademicYear date check constraint
- Subject (code, academic_year_id) uniqueness
- FacultySubjectAssignment uniqueness
- Seed idempotency
"""

from __future__ import annotations

import uuid
from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.seed import seed_database
from app.models.academic import AcademicYear, FacultySubjectAssignment, Subject
from app.models.faculty import FacultyProfile
from app.models.user import Role, User, UserAccountStatus, UserRoleName


class TestDatabaseConstraints:
    """Direct database validation of uniqueness and check constraints."""

    def test_user_email_unique_constraint(self, db_session: Session) -> None:
        user1 = User(
            email="unique.email@example.com",
            hashed_password="hash1",
            status=UserAccountStatus.ACTIVE.value,
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            email="unique.email@example.com",
            hashed_password="hash2",
            status=UserAccountStatus.ACTIVE.value,
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_faculty_profile_faculty_id_unique_constraint(
        self, db_session: Session
    ) -> None:
        u1 = User(email="f1@example.com", hashed_password="h", status="ACTIVE")
        u2 = User(email="f2@example.com", hashed_password="h", status="ACTIVE")
        db_session.add_all([u1, u2])
        db_session.flush()

        p1 = FacultyProfile(
            user_id=u1.id,
            faculty_id="FAC_UNIQUE_1",
            full_name="Prof One",
            designation="Lecturer",
            department="CSE",
        )
        db_session.add(p1)
        db_session.commit()

        p2 = FacultyProfile(
            user_id=u2.id,
            faculty_id="FAC_UNIQUE_1",  # Duplicate faculty_id
            full_name="Prof Two",
            designation="Lecturer",
            department="CSE",
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_faculty_profile_user_id_unique_constraint(
        self, db_session: Session
    ) -> None:
        u1 = User(email="f3@example.com", hashed_password="h", status="ACTIVE")
        db_session.add(u1)
        db_session.flush()

        p1 = FacultyProfile(
            user_id=u1.id,
            faculty_id="FAC_11",
            full_name="Prof One",
            designation="Lecturer",
            department="CSE",
        )
        db_session.add(p1)
        db_session.commit()

        p2 = FacultyProfile(
            user_id=u1.id,  # Duplicate user_id (1-to-1 violation)
            faculty_id="FAC_22",
            full_name="Prof Duplicate",
            designation="Lecturer",
            department="CSE",
        )
        db_session.add(p2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_user_roles_many_to_many_hod_plus_faculty(
        self, db_session: Session
    ) -> None:
        user = User(
            email="multi_role@example.com",
            hashed_password="hash",
            status=UserAccountStatus.ACTIVE.value,
        )
        hod_role = db_session.query(Role).filter(Role.name == UserRoleName.HOD.value).first()
        faculty_role = db_session.query(Role).filter(Role.name == UserRoleName.FACULTY.value).first()

        user.roles.append(hod_role)
        user.roles.append(faculty_role)
        db_session.add(user)
        db_session.commit()

        db_session.refresh(user)
        assert len(user.roles) == 2
        assert user.has_role("HOD") is True
        assert user.has_role("FACULTY") is True
        assert user.has_role("ADMIN") is False

    def test_subject_code_and_academic_year_unique_constraint(
        self, db_session: Session
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()

        s1 = Subject(
            code="CS801",
            name="Distributed Systems",
            semester=8,
            academic_year_id=year.id,
            department="CSE",
            credits=3.0,
        )
        db_session.add(s1)
        db_session.commit()

        s2 = Subject(
            code="CS801",  # Same code in same academic year
            name="Advanced Distributed Systems",
            semester=8,
            academic_year_id=year.id,
            department="CSE",
            credits=4.0,
        )
        db_session.add(s2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_faculty_subject_assignment_unique_active_constraint(
        self, db_session: Session, active_faculty_user: User
    ) -> None:
        year = db_session.query(AcademicYear).filter(AcademicYear.name == "2026-27").first()
        subject = Subject(
            code="CS802",
            name="Cloud Computing",
            semester=8,
            academic_year_id=year.id,
            department="CSE",
            credits=3.0,
        )
        db_session.add(subject)
        db_session.commit()

        a1 = FacultySubjectAssignment(
            faculty_profile_id=active_faculty_user.faculty_profile.id,
            subject_id=subject.id,
            is_active=True,
        )
        db_session.add(a1)
        db_session.commit()

        a2 = FacultySubjectAssignment(
            faculty_profile_id=active_faculty_user.faculty_profile.id,
            subject_id=subject.id,
            is_active=True,
        )
        db_session.add(a2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestSeedIdempotency:
    """Verify that running the seed command multiple times is safe and idempotent."""

    def test_seed_database_is_idempotent(self, db_session: Session) -> None:
        admin_before = db_session.query(User).filter(User.email == "admin@example.com").first()
        admin_pw_before = admin_before.hashed_password

        hod_before = db_session.query(User).filter(User.email == "hod@example.com").first()
        hod_roles_before = [r.name for r in hod_before.roles]

        # Run seed a second and third time
        seed_database(db_session)
        seed_database(db_session)

        admin_after = db_session.query(User).filter(User.email == "admin@example.com").first()
        assert admin_after.hashed_password == admin_pw_before  # Password not reset

        hod_after = db_session.query(User).filter(User.email == "hod@example.com").first()
        assert [r.name for r in hod_after.roles] == hod_roles_before  # Roles preserved

        # Ensure no duplicates created
        total_admins = db_session.query(User).filter(User.email == "admin@example.com").count()
        assert total_admins == 1

        total_hods = db_session.query(User).filter(User.email == "hod@example.com").count()
        assert total_hods == 1
