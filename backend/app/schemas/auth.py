"""
AI-NBA Readiness System — Backend
app/schemas/auth.py

Pydantic schemas for authentication and registration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """User login credentials."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class FacultyRegisterRequest(BaseModel):
    """
    Public faculty self-registration payload.
    Role assignment is prohibited here — all registrations default to PENDING status.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    faculty_id: str = Field(..., min_length=1, max_length=50, description="Employee/Faculty ID")
    full_name: str = Field(..., min_length=1, max_length=100)
    designation: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    contact_number: Optional[str] = Field(None, max_length=30)


class FacultyProfileResponse(BaseModel):
    """Faculty profile response data."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_id: str
    full_name: str
    designation: str
    department: str
    contact_number: Optional[str] = None


class UserResponse(BaseModel):
    """User response data excluding sensitive authentication credentials."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    status: str
    roles: List[str] = Field(default_factory=list)
    created_at: datetime
    last_login: Optional[datetime] = None
    faculty_profile: Optional[FacultyProfileResponse] = None

    @classmethod
    def from_orm_user(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            status=user.status,
            roles=[r.name if hasattr(r, "name") else str(r) for r in user.roles],
            created_at=user.created_at,
            last_login=user.last_login,
            faculty_profile=FacultyProfileResponse.model_validate(user.faculty_profile)
            if user.faculty_profile
            else None,
        )
