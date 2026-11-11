"""
AI-NBA Readiness System — Backend
app/services/notification_service.py

Milestone F: In-App Notifications Service.
Manages persistent user-targeted notifications, recipient isolation, unread counters,
and event dispatch helpers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.phase5 import Notification, NotificationType
from app.models.user import User


class NotificationService:
    """
    Handles creation, querying, and updating of persistent in-app notifications.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str = NotificationType.SYSTEM.value,
        link_url: Optional[str] = None,
        prevent_duplicates: bool = True,
    ) -> Notification:
        """
        Create a persistent notification for a specific user.
        If prevent_duplicates is True, will not re-insert an unread notification
        with identical user_id, notification_type, and title.
        """
        if prevent_duplicates:
            existing = (
                self.db.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == notification_type,
                    Notification.title == title,
                    Notification.is_read.is_(False),
                )
                .first()
            )
            if existing:
                return existing

        now = datetime.now(timezone.utc)
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url,
            is_read=False,
            created_at=now,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int, int]:
        """
        List notifications for a specific user (enforces recipient isolation).
        Returns: (notifications, total_count, unread_count)
        """
        base_q = self.db.query(Notification).filter(Notification.user_id == user_id)
        unread_count = (
            self.db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )

        q = base_q
        if unread_only:
            q = q.filter(Notification.is_read.is_(False))

        total_count = q.count()
        items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        return items, total_count, unread_count

    def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        """
        Mark a notification as read. Enforces recipient isolation.
        """
        notif = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(notif)

        return notif

    def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all unread notifications for a user as read."""
        now = datetime.now(timezone.utc)
        updated = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .update({"is_read": True, "read_at": now}, synchronize_session="fetch")
        )
        self.db.commit()
        return updated

    # -----------------------------------------------------------------------
    # Domain event dispatch helpers
    # -----------------------------------------------------------------------

    def notify_action_assigned(self, action_id: uuid.UUID, action_title: str, assignee_id: uuid.UUID) -> Optional[Notification]:
        return self.create_notification(
            user_id=assignee_id,
            title="New Corrective Action Assigned",
            message=f"You have been assigned corrective action: '{action_title}'.",
            notification_type=NotificationType.ACTION_ASSIGNED.value,
            link_url=f"/gaps/actions/{action_id}",
        )

    def notify_action_overdue(self, assignee_id: uuid.UUID, action_title: str) -> Optional[Notification]:
        return self.create_notification(
            user_id=assignee_id,
            title="Corrective Action Overdue",
            message=f"Corrective action '{action_title}' has passed its due date.",
            notification_type=NotificationType.ACTION_OVERDUE.value,
        )

    def notify_evaluation_warning_or_fail(
        self,
        recipient_user_ids: List[uuid.UUID],
        req_code: str,
        status_val: str,
    ) -> List[Notification]:
        notifications = []
        ntype = (
            NotificationType.EVALUATION_FAIL.value
            if status_val == "FAIL"
            else NotificationType.EVALUATION_WARNING.value
        )
        for uid in recipient_user_ids:
            n = self.create_notification(
                user_id=uid,
                title=f"Evaluation {status_val}: {req_code}",
                message=f"Requirement {req_code} was evaluated with status {status_val}.",
                notification_type=ntype,
            )
            notifications.append(n)
        return notifications
