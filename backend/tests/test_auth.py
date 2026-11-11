"""
tests/test_auth.py

Tests for authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me
"""

from __future__ import annotations

from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserAccountStatus, Role, UserRoleName


class TestFacultyRegistration:
    """Tests for POST /api/v1/auth/register"""

    def test_successful_faculty_registration(self, db_client: TestClient) -> None:
        payload = {
            "email": "faculty.new@example.com",
            "password": "StrongPassword123!",
            "faculty_id": "EMP101",
            "full_name": "Dr. John Watson",
            "designation": "Assistant Professor",
            "department": "Computer Science & Engineering",
            "contact_number": "+1234567890",
        }
        response = db_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "faculty.new@example.com"
        assert data["status"] == "PENDING"
        assert "hashed_password" not in data
        assert "password" not in data
        assert data["faculty_profile"]["faculty_id"] == "EMP101"
        assert data["faculty_profile"]["full_name"] == "Dr. John Watson"

    def test_registration_defaults_to_pending(self, db_client: TestClient) -> None:
        payload = {
            "email": "pending.test@example.com",
            "password": "StrongPassword123!",
            "faculty_id": "EMP102",
            "full_name": "Dr. Sarah Connor",
            "designation": "Associate Professor",
            "department": "Information Technology",
        }
        response = db_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        assert response.json()["status"] == "PENDING"

    def test_cannot_self_assign_roles_during_registration(self, db_client: TestClient) -> None:
        payload = {
            "email": "hacker@example.com",
            "password": "StrongPassword123!",
            "faculty_id": "EMP103",
            "full_name": "Malicious User",
            "designation": "Lecturer",
            "department": "Cybersecurity",
            "roles": ["ADMIN", "HOD"],
            "status": "ACTIVE",
        }
        response = db_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert "ADMIN" not in data["roles"]
        assert "HOD" not in data["roles"]

    def test_duplicate_email_rejected(self, db_client: TestClient) -> None:
        payload = {
            "email": "duplicate@example.com",
            "password": "StrongPassword123!",
            "faculty_id": "EMP104",
            "full_name": "User One",
            "designation": "Lecturer",
            "department": "CSE",
        }
        res1 = db_client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        payload["faculty_id"] = "EMP105"
        res2 = db_client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        assert "email" in res2.json()["detail"].lower()

    def test_duplicate_faculty_id_rejected(self, db_client: TestClient) -> None:
        payload = {
            "email": "user1@example.com",
            "password": "StrongPassword123!",
            "faculty_id": "EMP_SHARED",
            "full_name": "User One",
            "designation": "Lecturer",
            "department": "CSE",
        }
        res1 = db_client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        payload["email"] = "user2@example.com"
        res2 = db_client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        assert "faculty id" in res2.json()["detail"].lower()


class TestUserLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_successful_login_active_account(self, db_client: TestClient) -> None:
        payload = {
            "email": "admin@example.com",
            "password": "AdminPassword123!",
        }
        response = db_client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_successful_login_updates_last_login(self, db_client: TestClient, db_session: Session) -> None:
        admin = db_session.query(User).filter(User.email == "admin@example.com").first()
        assert admin.last_login is None

        payload = {
            "email": "admin@example.com",
            "password": "AdminPassword123!",
        }
        response = db_client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200

        db_session.refresh(admin)
        assert admin.last_login is not None

    def test_invalid_password_returns_401_without_leaking(self, db_client: TestClient) -> None:
        payload = {
            "email": "admin@example.com",
            "password": "WrongPassword!",
        }
        response = db_client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."

    def test_nonexistent_email_returns_401_without_leaking(self, db_client: TestClient) -> None:
        payload = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
        }
        response = db_client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."

    def test_pending_account_cannot_login(self, db_client: TestClient) -> None:
        # Register a pending user
        db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "pending.login@example.com",
                "password": "Password123!",
                "faculty_id": "EMP_PEN_1",
                "full_name": "Pending User",
                "designation": "Lecturer",
                "department": "CSE",
            },
        )
        response = db_client.post(
            "/api/v1/auth/login",
            json={"email": "pending.login@example.com", "password": "Password123!"},
        )
        assert response.status_code == 403
        assert "pending" in response.json()["detail"].lower()

    def test_disabled_account_cannot_login(self, db_client: TestClient, db_session: Session) -> None:
        user = User(
            email="disabled@example.com",
            hashed_password=get_password_hash("Password123!"),
            status=UserAccountStatus.DISABLED.value,
        )
        db_session.add(user)
        db_session.commit()

        response = db_client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@example.com", "password": "Password123!"},
        )
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    def test_rejected_account_cannot_login(self, db_client: TestClient, db_session: Session) -> None:
        user = User(
            email="rejected@example.com",
            hashed_password=get_password_hash("Password123!"),
            status=UserAccountStatus.REJECTED.value,
        )
        db_session.add(user)
        db_session.commit()

        response = db_client.post(
            "/api/v1/auth/login",
            json={"email": "rejected@example.com", "password": "Password123!"},
        )
        assert response.status_code == 403
        assert "rejected" in response.json()["detail"].lower()


class TestCurrentUserEndpoint:
    """Tests for GET /api/v1/auth/me"""

    def test_me_returns_profile_for_active_user(
        self, db_client: TestClient, admin_headers: dict
    ) -> None:
        response = db_client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        assert "ADMIN" in data["roles"]
        assert "hashed_password" not in data

    def test_me_unauthenticated_returns_401(self, db_client: TestClient) -> None:
        response = db_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_expired_token_returns_401(
        self, db_client: TestClient, admin_user: User
    ) -> None:
        expired_token = create_access_token(
            subject=str(admin_user.id),
            roles=admin_user.role_names,
            expires_delta=timedelta(seconds=-10),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = db_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_me_invalid_token_returns_401(self, db_client: TestClient) -> None:
        headers = {"Authorization": "Bearer invalid.token.string"}
        response = db_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_me_disabled_user_token_returns_403(
        self, db_client: TestClient, db_session: Session
    ) -> None:
        user = User(
            email="to_disable@example.com",
            hashed_password=get_password_hash("Pass123!"),
            status=UserAccountStatus.ACTIVE.value,
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(subject=str(user.id), roles=[])
        headers = {"Authorization": f"Bearer {token}"}

        # First request succeeds
        res1 = db_client.get("/api/v1/auth/me", headers=headers)
        assert res1.status_code == 200

        # Now disable user in database
        user.status = UserAccountStatus.DISABLED.value
        db_session.commit()

        # Subsequent request with same token fails with 403
        res2 = db_client.get("/api/v1/auth/me", headers=headers)
        assert res2.status_code == 403
        assert "not active" in res2.json()["detail"].lower()
