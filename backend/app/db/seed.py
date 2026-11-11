"""
AI-NBA Readiness System — Backend
app/db/seed.py

Idempotent seed command to initialize standard roles, the initial administrator,
and the initial HOD account based on environment variables.

Usage:
    python -m app.db.seed
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.academic import AcademicYear
from app.models.faculty import FacultyProfile
from app.models.user import Role, User, UserAccountStatus, UserRoleName

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")


def seed_database(db: Optional[Session] = None) -> None:
    """
    Seed standard roles, initial admin, and initial HOD account idempotently.

    Existing accounts and passwords will NEVER be modified or reset.
    """
    settings = get_settings()
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Ensure system roles exist
        roles_to_seed = [
            (UserRoleName.ADMIN.value, "System Administrator with full management access"),
            (UserRoleName.HOD.value, "Head of Department with approval and assignment permissions"),
            (UserRoleName.FACULTY.value, "Academic Faculty Member with subject and course-outcome duties"),
        ]

        roles_dict = {}
        for role_name, description in roles_to_seed:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name, description=description)
                db.add(role)
                db.flush()
                logger.info("Created system role: %s", role_name)
            roles_dict[role_name] = role

        # 2. Seed Initial Admin Account
        admin_email = settings.INITIAL_ADMIN_EMAIL.lower().strip()
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            logger.info("Admin account '%s' already exists. Skipping creation.", admin_email)
        else:
            if not settings.INITIAL_ADMIN_PASSWORD:
                raise ValueError(
                    "INITIAL_ADMIN_PASSWORD environment variable is required to create the initial admin account."
                )
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                status=UserAccountStatus.ACTIVE.value,
            )
            admin_user.roles.append(roles_dict[UserRoleName.ADMIN.value])
            db.add(admin_user)
            db.flush()
            logger.info("Created initial admin account: %s", admin_email)

        # 3. Seed Initial HOD Account (with HOD + FACULTY roles)
        hod_email = settings.INITIAL_HOD_EMAIL.lower().strip()
        existing_hod = db.query(User).filter(User.email == hod_email).first()
        if existing_hod:
            logger.info("HOD account '%s' already exists. Skipping creation.", hod_email)
        else:
            if not settings.INITIAL_HOD_PASSWORD:
                raise ValueError(
                    "INITIAL_HOD_PASSWORD environment variable is required to create the initial HOD account."
                )
            hod_user = User(
                email=hod_email,
                hashed_password=get_password_hash(settings.INITIAL_HOD_PASSWORD),
                status=UserAccountStatus.ACTIVE.value,
            )
            # Assign BOTH HOD and FACULTY roles
            hod_user.roles.append(roles_dict[UserRoleName.HOD.value])
            hod_user.roles.append(roles_dict[UserRoleName.FACULTY.value])
            db.add(hod_user)
            db.flush()

            # Create FacultyProfile for HOD
            hod_profile = FacultyProfile(
                user_id=hod_user.id,
                faculty_id=settings.INITIAL_HOD_FACULTY_ID,
                full_name=settings.INITIAL_HOD_NAME,
                designation="Head of Department",
                department=settings.INITIAL_HOD_DEPARTMENT,
            )
            db.add(hod_profile)
            db.flush()
            logger.info(
                "Created initial HOD account '%s' with HOD + FACULTY roles and profile.",
                hod_email,
            )

        # 4. Seed Initial Academic Year if none exists
        default_year_name = "2026-27"
        existing_year = db.query(AcademicYear).filter(AcademicYear.name == default_year_name).first()
        if not existing_year:
            initial_year = AcademicYear(
                name=default_year_name,
                start_date=date(2026, 7, 1),
                end_date=date(2027, 6, 30),
                is_active=True,
            )
            db.add(initial_year)
            db.flush()
            logger.info("Created initial academic year: %s", default_year_name)

        # 5. Seed Phase 4 NBA Criteria and Requirements idempotently
        from app.db.seed_phase4 import seed_phase4
        seed_phase4(db)
        logger.info("Seeded Phase 4 criteria and requirements.")

        db.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as exc:
        db.rollback()
        logger.error("Error during database seeding: %s", exc)
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_database()
