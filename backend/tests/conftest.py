"""
tests/conftest.py

Shared pytest fixtures for the AI-NBA Readiness System backend tests.

Design goals
------------
* Tests MUST NOT require a live PostgreSQL database.
* The test client uses FastAPI's built-in TestClient (synchronous WSGI
  wrapper over ASGI) backed by httpx.
* In-memory SQLite provides fully isolated database sessions for testing
  models, authentication, transactions, and role-based authorization.
"""

from __future__ import annotations

import os
from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Point to a safe test DATABASE_URL before the application module is imported
# so Settings never attempts to connect to a real database during test
# collection.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://testuser:testpass@localhost:5432/test_db",
)
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-running-automated-tests-safely-123456")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "AdminPassword123!")
os.environ.setdefault("INITIAL_HOD_PASSWORD", "HODPassword123!")
# Pin seed identities so a local backend/.env (e.g. written by run.py) cannot
# change the accounts the fixtures look up.
os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
os.environ["INITIAL_HOD_EMAIL"] = "hod@example.com"
os.environ["INITIAL_HOD_DEPARTMENT"] = "Computer Science & Engineering"
os.environ["INITIAL_HOD_NAME"] = "Head of Department"
os.environ["INITIAL_HOD_FACULTY_ID"] = "HOD001"

# ---------------------------------------------------------------------------
# Import app and models after env vars are set
# ---------------------------------------------------------------------------
import app.models  # noqa: F401, E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.db.seed import seed_database  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.faculty import FacultyProfile  # noqa: E402
from app.models.user import Role, User, UserAccountStatus, UserRoleName  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    Return a TestClient that wraps the FastAPI application.

    The client is session-scoped and used for general root/probe tests.
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Yield an isolated in-memory SQLite database session with seeded
    system roles, initial admin, and initial HOD accounts.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        class_=Session,
    )
    session = TestingSessionLocal()
    seed_database(session)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Return a TestClient configured with an isolated in-memory database session.
    """
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Return the seeded admin user."""
    return db_session.query(User).filter(User.email == "admin@example.com").first()


@pytest.fixture
def admin_headers(admin_user: User) -> Dict[str, str]:
    """Return Authorization headers for the admin user."""
    token = create_access_token(
        subject=str(admin_user.id),
        roles=admin_user.role_names,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hod_user(db_session: Session) -> User:
    """Return the seeded HOD user (has both HOD and FACULTY roles)."""
    return db_session.query(User).filter(User.email == "hod@example.com").first()


@pytest.fixture
def hod_headers(hod_user: User) -> Dict[str, str]:
    """Return Authorization headers for the HOD user."""
    token = create_access_token(
        subject=str(hod_user.id),
        roles=hod_user.role_names,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def active_faculty_user(db_session: Session) -> User:
    """Create and return an active faculty user with FACULTY role and profile."""
    faculty_role = db_session.query(Role).filter(Role.name == UserRoleName.FACULTY.value).first()
    user = User(
        email="faculty1@example.com",
        hashed_password=get_password_hash("FacultyPass123!"),
        status=UserAccountStatus.ACTIVE.value,
    )
    user.roles.append(faculty_role)
    db_session.add(user)
    db_session.flush()

    profile = FacultyProfile(
        user_id=user.id,
        faculty_id="FAC001",
        full_name="Dr. Alice Smith",
        designation="Assistant Professor",
        department="Computer Science & Engineering",
        contact_number="1234567890",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def faculty_headers(active_faculty_user: User) -> Dict[str, str]:
    """Return Authorization headers for the active faculty user."""
    token = create_access_token(
        subject=str(active_faculty_user.id),
        roles=active_faculty_user.role_names,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_faculty_user(db_session: Session) -> User:
    """Create and return a second active faculty user with FACULTY role and profile."""
    faculty_role = db_session.query(Role).filter(Role.name == UserRoleName.FACULTY.value).first()
    user = User(
        email="faculty2@example.com",
        hashed_password=get_password_hash("FacultyPass123!"),
        status=UserAccountStatus.ACTIVE.value,
    )
    user.roles.append(faculty_role)
    db_session.add(user)
    db_session.flush()

    profile = FacultyProfile(
        user_id=user.id,
        faculty_id="FAC002",
        full_name="Dr. Bob Jones",
        designation="Associate Professor",
        department="Computer Science & Engineering",
        contact_number="9876543210",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_faculty_headers(second_faculty_user: User) -> Dict[str, str]:
    """Return Authorization headers for the second active faculty user."""
    token = create_access_token(
        subject=str(second_faculty_user.id),
        roles=second_faculty_user.role_names,
    )
    return {"Authorization": f"Bearer {token}"}
