"""
AI-NBA Readiness System — Backend
app/api/v1/users.py

User management endpoints: pending user approval/rejection (HOD/Admin)
and administrative account management (Admin only).
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import Role, User, UserAccountStatus, UserRoleName
from app.schemas.auth import UserResponse
from app.schemas.user import RoleModifyRequest, UserListResponse, UserStatusUpdateRequest

router = APIRouter(prefix="/users", tags=["User Management"])


# =============================================================================
# HOD / Admin Approval Endpoints (STEP 4)
# =============================================================================

@router.get(
    "/pending",
    response_model=List[UserResponse],
    summary="List pending user registrations",
    description="Retrieve all user registrations currently awaiting HOD or Administrator approval.",
)
def list_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> List[UserResponse]:
    """List all users with PENDING status (HOD or Admin only)."""
    pending_users = (
        db.query(User)
        .filter(User.status == UserAccountStatus.PENDING.value)
        .order_by(User.created_at.asc())
        .all()
    )
    return [UserResponse.from_orm_user(u) for u in pending_users]


@router.post(
    "/{user_id}/approve",
    response_model=UserResponse,
    summary="Approve pending user registration",
    description="Approve a pending registration, set status to ACTIVE, and grant FACULTY role transactionally.",
)
def approve_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> UserResponse:
    """Approve a pending user registration transactionally."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if target_user.status != UserAccountStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not in PENDING status (current: {target_user.status}).",
        )

    try:
        # Find or create FACULTY role
        faculty_role = db.query(Role).filter(Role.name == UserRoleName.FACULTY.value).first()
        if not faculty_role:
            faculty_role = Role(
                name=UserRoleName.FACULTY.value,
                description="Academic faculty member",
            )
            db.add(faculty_role)
            db.flush()

        if faculty_role not in target_user.roles:
            target_user.roles.append(faculty_role)

        target_user.status = UserAccountStatus.ACTIVE.value
        db.commit()
        db.refresh(target_user)
    except Exception:
        db.rollback()
        raise

    return UserResponse.from_orm_user(target_user)


@router.post(
    "/{user_id}/reject",
    response_model=UserResponse,
    summary="Reject pending user registration",
    description="Reject a pending registration and transition status to REJECTED.",
)
def reject_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> UserResponse:
    """Reject a pending registration."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if target_user.status != UserAccountStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not in PENDING status (current: {target_user.status}).",
        )

    target_user.status = UserAccountStatus.REJECTED.value
    db.commit()
    db.refresh(target_user)
    return UserResponse.from_orm_user(target_user)


# =============================================================================
# Admin User Management Endpoints (STEP 5)
# =============================================================================

@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users (Admin only)",
    description="Query users with optional filtering by status or role.",
)
def list_users(
    status_filter: Optional[UserAccountStatus] = Query(None, alias="status"),
    role_filter: Optional[UserRoleName] = Query(None, alias="role"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
) -> UserListResponse:
    """List users with optional filtering (Admin only)."""
    query = db.query(User)

    if status_filter:
        query = query.filter(User.status == status_filter.value)

    if role_filter:
        query = query.filter(User.roles.any(Role.name == role_filter.value))

    users = query.order_by(User.created_at.desc()).all()
    items = [UserResponse.from_orm_user(u) for u in users]
    return UserListResponse(total=len(items), items=items)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Update account status (Admin only)",
    description="Enable, disable, or reject a user account.",
)
def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
) -> UserResponse:
    """Update user account status (Admin only)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    target_user.status = payload.status.value
    db.commit()
    db.refresh(target_user)
    return UserResponse.from_orm_user(target_user)


@router.post(
    "/{user_id}/roles/hod",
    response_model=UserResponse,
    summary="Assign HOD role (Admin only)",
    description="Grant HOD privileges to a user while preserving their FACULTY role.",
)
def assign_hod_role(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
) -> UserResponse:
    """Grant HOD role to a user (Admin only)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    hod_role = db.query(Role).filter(Role.name == UserRoleName.HOD.value).first()
    if not hod_role:
        hod_role = Role(
            name=UserRoleName.HOD.value,
            description="Head of Department",
        )
        db.add(hod_role)
        db.flush()

    if hod_role not in target_user.roles:
        target_user.roles.append(hod_role)
        db.commit()
        db.refresh(target_user)

    return UserResponse.from_orm_user(target_user)


@router.delete(
    "/{user_id}/roles/hod",
    response_model=UserResponse,
    summary="Remove HOD role (Admin only)",
    description="Remove HOD privileges from a user while preserving their FACULTY role.",
)
def remove_hod_role(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
) -> UserResponse:
    """Remove HOD role from a user (Admin only)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    hod_role = db.query(Role).filter(Role.name == UserRoleName.HOD.value).first()
    if hod_role and hod_role in target_user.roles:
        target_user.roles.remove(hod_role)
        db.commit()
        db.refresh(target_user)

    return UserResponse.from_orm_user(target_user)
