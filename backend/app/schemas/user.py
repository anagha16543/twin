"""
AI-NBA Readiness System — Backend
app/schemas/user.py

Pydantic schemas for user management, HOD approval, and role assignments.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import UserAccountStatus, UserRoleName
from app.schemas.auth import UserResponse


class UserStatusUpdateRequest(BaseModel):
    """Payload to update an account's status."""
    status: UserAccountStatus


class RoleModifyRequest(BaseModel):
    """Payload to assign or remove a role."""
    role_name: UserRoleName


class UserListResponse(BaseModel):
    """Paginated or listed collection of users."""
    total: int
    items: List[UserResponse]
