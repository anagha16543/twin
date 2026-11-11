"""
tests/test_phase5_notifications.py

Tests for In-App Notifications: persistence, recipient isolation, unread count queries,
mark-as-read, and duplicate prevention.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.phase5 import Notification, NotificationType
from app.models.user import Role, User, UserAccountStatus, UserRoleName
from app.services.notification_service import NotificationService


@pytest.fixture
def second_user(db_session: Session) -> User:
    """Create a distinct second faculty user for recipient isolation tests."""
    fac_role = db_session.query(Role).filter(Role.name == UserRoleName.FACULTY.value).first()
    u2 = User(
        email="faculty_two@example.com",
        hashed_password="hashed_pass_placeholder",
        status=UserAccountStatus.ACTIVE.value,
    )
    u2.roles.append(fac_role)
    db_session.add(u2)
    db_session.commit()
    db_session.refresh(u2)
    return u2


class TestNotificationService:
    def test_create_and_query_notifications(self, db_session: Session, admin_user: User):
        """Create notification and verify count and unread tracking."""
        service = NotificationService(db_session)
        notif = service.create_notification(
            user_id=admin_user.id,
            title="System Alert",
            message="Server maintenance completed.",
            notification_type=NotificationType.SYSTEM.value,
        )

        assert notif.id is not None
        assert notif.is_read is False

        items, total, unread = service.list_user_notifications(user_id=admin_user.id)
        assert total >= 1
        assert unread >= 1
        assert any(n.id == notif.id for n in items)

    def test_duplicate_notification_prevention(self, db_session: Session, admin_user: User):
        """Attempting to insert identical unread notification returns the existing record."""
        service = NotificationService(db_session)
        n1 = service.create_notification(
            user_id=admin_user.id,
            title="Action Overdue Reminder",
            message="Please submit syllabus.",
            notification_type=NotificationType.ACTION_OVERDUE.value,
            prevent_duplicates=True,
        )
        n2 = service.create_notification(
            user_id=admin_user.id,
            title="Action Overdue Reminder",
            message="Please submit syllabus.",
            notification_type=NotificationType.ACTION_OVERDUE.value,
            prevent_duplicates=True,
        )

        assert n1.id == n2.id

    def test_recipient_isolation(
        self,
        db_session: Session,
        admin_user: User,
        second_user: User,
    ):
        """Notifications for User A must never appear in User B's list."""
        service = NotificationService(db_session)
        service.create_notification(
            user_id=admin_user.id,
            title="Admin-only notice",
            message="Sensitive admin update.",
        )
        service.create_notification(
            user_id=second_user.id,
            title="Faculty notice",
            message="Your course outcome was mapped.",
        )

        items_u2, _, _ = service.list_user_notifications(user_id=second_user.id)
        assert all(n.user_id == second_user.id for n in items_u2)
        assert not any(n.title == "Admin-only notice" for n in items_u2)


class TestNotificationAPI:
    def test_mark_as_read_api(
        self,
        db_client: TestClient,
        db_session: Session,
        admin_user: User,
        admin_headers: dict,
    ):
        """PATCH /api/v1/notifications/{id}/read marks notification as read."""
        service = NotificationService(db_session)
        n = service.create_notification(
            user_id=admin_user.id,
            title="Test unread item",
            message="Click to acknowledge.",
        )

        resp = db_client.patch(f"/api/v1/notifications/{n.id}/read", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_read"] is True
        assert data["read_at"] is not None

    def test_cannot_mark_other_users_notification_read(
        self,
        db_client: TestClient,
        db_session: Session,
        admin_user: User,
        second_user: User,
    ):
        """User cannot modify another user's notification (returns 404)."""
        service = NotificationService(db_session)
        notif = service.create_notification(
            user_id=admin_user.id,
            title="Admin notification",
            message="Confidential.",
        )

        # Login as second user
        token = create_access_token(
            subject=str(second_user.id),
            roles=second_user.role_names,
        )
        headers = {"Authorization": f"Bearer {token}"}

        resp = db_client.patch(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert resp.status_code == 404
