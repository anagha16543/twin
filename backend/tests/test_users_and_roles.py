"""
tests/test_users_and_roles.py

Tests for HOD approval flow and Admin user management:
- GET /api/v1/users/pending
- POST /api/v1/users/{user_id}/approve
- POST /api/v1/users/{user_id}/reject
- GET /api/v1/users
- PATCH /api/v1/users/{user_id}/status
- POST /api/v1/users/{user_id}/roles/hod
- DELETE /api/v1/users/{user_id}/roles/hod
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.faculty import FacultyProfile
from app.models.user import Role, User, UserAccountStatus, UserRoleName


class TestHODApprovalFlow:
    """Tests for listing, approving, and rejecting pending faculty registrations."""

    def _register_pending_faculty(self, client: TestClient, email: str, fac_id: str) -> dict:
        payload = {
            "email": email,
            "password": "Password123!",
            "faculty_id": fac_id,
            "full_name": "Pending Faculty",
            "designation": "Assistant Professor",
            "department": "CSE",
        }
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201
        return res.json()

    def test_hod_can_list_pending_users(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        self._register_pending_faculty(db_client, "pending1@example.com", "PEN001")
        response = db_client.get("/api/v1/users/pending", headers=hod_headers)
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "pending1@example.com" in emails

    def test_admin_can_list_pending_users(
        self, db_client: TestClient, admin_headers: dict
    ) -> None:
        self._register_pending_faculty(db_client, "pending2@example.com", "PEN002")
        response = db_client.get("/api/v1/users/pending", headers=admin_headers)
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert "pending2@example.com" in emails

    def test_faculty_cannot_list_pending_users(
        self, db_client: TestClient, faculty_headers: dict
    ) -> None:
        response = db_client.get("/api/v1/users/pending", headers=faculty_headers)
        assert response.status_code == 403
        assert "insufficient privileges" in response.json()["detail"].lower()

    def test_unauthenticated_cannot_list_pending_users(self, db_client: TestClient) -> None:
        response = db_client.get("/api/v1/users/pending")
        assert response.status_code == 401

    def test_hod_approves_pending_user_transactionally(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        user_data = self._register_pending_faculty(
            db_client, "to_approve@example.com", "PEN003"
        )
        user_id = user_data["id"]

        # Approve user
        response = db_client.post(
            f"/api/v1/users/{user_id}/approve",
            headers=hod_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"
        assert "FACULTY" in data["roles"]

        # Verify the newly approved user can now log in
        login_res = db_client.post(
            "/api/v1/auth/login",
            json={"email": "to_approve@example.com", "password": "Password123!"},
        )
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()

    def test_hod_rejects_pending_user(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        user_data = self._register_pending_faculty(
            db_client, "to_reject@example.com", "PEN004"
        )
        user_id = user_data["id"]

        response = db_client.post(
            f"/api/v1/users/{user_id}/reject",
            headers=hod_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

        # Verify rejected user cannot log in
        login_res = db_client.post(
            "/api/v1/auth/login",
            json={"email": "to_reject@example.com", "password": "Password123!"},
        )
        assert login_res.status_code == 403

    def test_faculty_cannot_approve_or_reject(
        self, db_client: TestClient, faculty_headers: dict
    ) -> None:
        user_data = self._register_pending_faculty(
            db_client, "unauthorized_approval@example.com", "PEN005"
        )
        user_id = user_data["id"]

        res_approve = db_client.post(
            f"/api/v1/users/{user_id}/approve",
            headers=faculty_headers,
        )
        assert res_approve.status_code == 403

        res_reject = db_client.post(
            f"/api/v1/users/{user_id}/reject",
            headers=faculty_headers,
        )
        assert res_reject.status_code == 403

    def test_approving_non_pending_user_returns_400(
        self, db_client: TestClient, hod_headers: dict, admin_user: User
    ) -> None:
        response = db_client.post(
            f"/api/v1/users/{admin_user.id}/approve",
            headers=hod_headers,
        )
        assert response.status_code == 400
        assert "not in pending status" in response.json()["detail"].lower()

    def test_approving_nonexistent_user_returns_404(
        self, db_client: TestClient, hod_headers: dict
    ) -> None:
        fake_id = uuid.uuid4()
        response = db_client.post(
            f"/api/v1/users/{fake_id}/approve",
            headers=hod_headers,
        )
        assert response.status_code == 404


class TestAdminUserManagement:
    """Tests for Admin user listing, status updates, and HOD role management."""

    def test_admin_can_list_users_with_filter(
        self, db_client: TestClient, admin_headers: dict
    ) -> None:
        response = db_client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # Seed admin + hod
        assert len(data["items"]) == data["total"]

        # Filter by status ACTIVE
        res_active = db_client.get(
            "/api/v1/users?status=ACTIVE", headers=admin_headers
        )
        assert res_active.status_code == 200
        for item in res_active.json()["items"]:
            assert item["status"] == "ACTIVE"

    def test_faculty_cannot_list_users(
        self, db_client: TestClient, faculty_headers: dict
    ) -> None:
        response = db_client.get("/api/v1/users", headers=faculty_headers)
        assert response.status_code == 403

    def test_admin_can_disable_and_reactivate_user(
        self,
        db_client: TestClient,
        admin_headers: dict,
        active_faculty_user: User,
    ) -> None:
        user_id = str(active_faculty_user.id)

        # Disable user
        res_disable = db_client.patch(
            f"/api/v1/users/{user_id}/status",
            headers=admin_headers,
            json={"status": "DISABLED"},
        )
        assert res_disable.status_code == 200
        assert res_disable.json()["status"] == "DISABLED"

        # Verify disabled user cannot log in
        login_res = db_client.post(
            "/api/v1/auth/login",
            json={"email": active_faculty_user.email, "password": "FacultyPass123!"},
        )
        assert login_res.status_code == 403

        # Reactivate user
        res_enable = db_client.patch(
            f"/api/v1/users/{user_id}/status",
            headers=admin_headers,
            json={"status": "ACTIVE"},
        )
        assert res_enable.status_code == 200
        assert res_enable.json()["status"] == "ACTIVE"

    def test_admin_can_assign_and_remove_hod_role(
        self,
        db_client: TestClient,
        admin_headers: dict,
        active_faculty_user: User,
    ) -> None:
        user_id = str(active_faculty_user.id)
        assert "FACULTY" in active_faculty_user.role_names
        assert "HOD" not in active_faculty_user.role_names

        # Assign HOD role
        assign_res = db_client.post(
            f"/api/v1/users/{user_id}/roles/hod",
            headers=admin_headers,
        )
        assert assign_res.status_code == 200
        roles = assign_res.json()["roles"]
        assert "HOD" in roles
        assert "FACULTY" in roles  # Both roles retained!

        # Remove HOD role
        remove_res = db_client.delete(
            f"/api/v1/users/{user_id}/roles/hod",
            headers=admin_headers,
        )
        assert remove_res.status_code == 200
        updated_roles = remove_res.json()["roles"]
        assert "HOD" not in updated_roles
        assert "FACULTY" in updated_roles  # Faculty role preserved!

    def test_faculty_cannot_escalate_roles(
        self,
        db_client: TestClient,
        faculty_headers: dict,
        active_faculty_user: User,
    ) -> None:
        user_id = str(active_faculty_user.id)
        res = db_client.post(
            f"/api/v1/users/{user_id}/roles/hod",
            headers=faculty_headers,
        )
        assert res.status_code == 403
