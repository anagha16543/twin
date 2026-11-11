"""
AI-NBA Readiness System — Backend
app/api/v1/auth.py

Authentication endpoints: registration, login, and current-user profile.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.faculty import FacultyProfile
from app.models.user import User, UserAccountStatus
from app.schemas.auth import (
    FacultyRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Faculty self-registration",
    description=(
        "Register a new faculty account. Accounts are created in PENDING status "
        "and must be approved by an HOD or Administrator before login is permitted."
    ),
)
def register_faculty(
    payload: FacultyRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new faculty account in PENDING status."""
    normalized_email = payload.email.lower().strip()

    # Check for duplicate email
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    # Check for duplicate faculty_id
    existing_profile = (
        db.query(FacultyProfile)
        .filter(FacultyProfile.faculty_id == payload.faculty_id.strip())
        .first()
    )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A faculty profile with this faculty ID already exists.",
        )

    try:
        new_user = User(
            email=normalized_email,
            hashed_password=get_password_hash(payload.password),
            status=UserAccountStatus.PENDING.value,
        )
        db.add(new_user)
        db.flush()  # Generate new_user.id for profile foreign key

        profile = FacultyProfile(
            user_id=new_user.id,
            faculty_id=payload.faculty_id.strip(),
            full_name=payload.full_name.strip(),
            designation=payload.designation.strip(),
            department=payload.department.strip(),
            contact_number=payload.contact_number.strip() if payload.contact_number else None,
        )
        db.add(profile)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return UserResponse.from_orm_user(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email and password to receive a JWT access token.",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate credentials and generate a JWT access token."""
    normalized_email = payload.email.lower().strip()

    user = db.query(User).filter(User.email == normalized_email).first()

    # Avoid leaking whether email exists
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account status
    if user.status == UserAccountStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is pending approval by an HOD or Administrator.",
        )
    elif user.status == UserAccountStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account registration request was rejected.",
        )
    elif user.status == UserAccountStatus.DISABLED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled. Please contact your administrator.",
        )
    elif user.status != UserAccountStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is inactive (status: {user.status}).",
        )

    # Record last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(
        subject=str(user.id),
        roles=user.role_names,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current authenticated user",
    description="Retrieve account profile and assigned roles for the authenticated user.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's details."""
    return UserResponse.from_orm_user(current_user)
