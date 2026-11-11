"""
AI-NBA Readiness System — Backend
app/api/deps.py

FastAPI dependency providers for database sessions, authentication,
and role-based access control (RBAC).
"""

from __future__ import annotations

import uuid
from typing import Callable, List, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserAccountStatus

security = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the incoming Bearer token and return the active User.

    Raises:
        HTTPException 401: If token is missing, invalid, expired, or user not found.
        HTTPException 403: If user account is not ACTIVE (e.g. PENDING, DISABLED, REJECTED).
    """
    if auth is None or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject format in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserAccountStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is not active (status: {user.status}).",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """
    Factory dependency to enforce role-based access control.

    A user passes authorization if they possess at least one of the `allowed_roles`.
    """
    def _role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = current_user.role_names
        for role in allowed_roles:
            if role in user_roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: insufficient privileges.",
        )

    return _role_checker


def resolve_faculty_profile(faculty_id: str | uuid.UUID, db: Session):
    """Resolve a FacultyProfile by UUID or string faculty_id."""
    from app.models.faculty import FacultyProfile

    faculty = None
    if isinstance(faculty_id, uuid.UUID):
        faculty = db.query(FacultyProfile).filter(FacultyProfile.id == faculty_id).first()
    elif isinstance(faculty_id, str):
        try:
            fac_uuid = uuid.UUID(faculty_id)
            faculty = db.query(FacultyProfile).filter(FacultyProfile.id == fac_uuid).first()
        except (ValueError, AttributeError):
            pass
        if not faculty:
            faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id == faculty_id.strip()).first()
    return faculty


def verify_faculty_owner_or_admin(faculty_id: str | uuid.UUID, user: User, db: Session):
    """
    Ensure the user is HOD, ADMIN, or the owner faculty member.
    Returns the resolved FacultyProfile or raises HTTPException.
    """
    from app.models.user import UserRoleName

    faculty = resolve_faculty_profile(faculty_id, db)
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found.",
        )

    is_admin_or_hod = user.has_role(UserRoleName.ADMIN.value) or user.has_role(UserRoleName.HOD.value)
    is_owner = user.faculty_profile is not None and user.faculty_profile.id == faculty.id

    if not (is_admin_or_hod or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view or modify this faculty member's records.",
        )

    return faculty


def verify_subject_faculty_or_admin(
    subject_id: uuid.UUID,
    user: User,
    db: Session,
    require_write_permission: bool = False,
):
    """
    Ensure the user has access to the subject:
    - For read operations (require_write_permission=False):
      ADMIN, HOD, or actively assigned faculty members.
    - For academic write operations (require_write_permission=True):
      HOD or an actively assigned faculty member.
      Admins do NOT automatically receive unrestricted academic-data editing permissions.
    """
    from app.models.academic import FacultySubjectAssignment, Subject
    from app.models.user import UserRoleName

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    # HOD has departmental academic oversight
    if user.has_role(UserRoleName.HOD.value):
        return subject

    # System Administrator read-only for monitoring/audit; writing classroom records is forbidden
    if user.has_role(UserRoleName.ADMIN.value):
        if require_write_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators do not have academic data editing permissions for subjects. Academic records must be managed by assigned faculty or the department HOD.",
            )
        return subject

    # Faculty must be actively assigned
    is_assigned = False
    if user.faculty_profile:
        assignment = (
            db.query(FacultySubjectAssignment)
            .filter(
                FacultySubjectAssignment.subject_id == subject_id,
                FacultySubjectAssignment.faculty_profile_id == user.faculty_profile.id,
                FacultySubjectAssignment.is_active.is_(True),
            )
            .first()
        )
        if assignment:
            is_assigned = True

    if not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this subject and cannot manage its academic records.",
        )

    return subject
