"""
AI-NBA Readiness System — Backend
app/api/v1/notifications.py

Endpoints for persistent in-app notifications with recipient isolation.
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.phase5 import NotificationListResponse, NotificationOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List Current User Notifications",
)
def list_notifications(
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List persistent in-app notifications for the authenticated user.
    Strictly isolated: users cannot view other users' notifications.
    """
    service = NotificationService(db)
    items, total, unread = service.list_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        offset=offset,
        limit=limit,
    )
    return NotificationListResponse(
        unread_count=unread,
        total_count=total,
        notifications=[NotificationOut.model_validate(n) for n in items],
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark Notification as Read",
)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a notification as read. Fails with 404 if notification belongs to another user.
    """
    service = NotificationService(db)
    notif = service.mark_as_read(notification_id=notification_id, user_id=current_user.id)
    return NotificationOut.model_validate(notif)


@router.post(
    "/read-all",
    summary="Mark All Notifications as Read",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all unread notifications for the current user as read.
    """
    service = NotificationService(db)
    count = service.mark_all_as_read(user_id=current_user.id)
    return {"marked_read_count": count}
