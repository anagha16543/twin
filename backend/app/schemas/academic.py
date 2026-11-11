"""
AI-NBA Readiness System — Backend
app/schemas/academic.py

Pydantic schemas for AcademicYear, Subject, and FacultySubjectAssignment.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import FacultyProfileResponse


class AcademicYearCreate(BaseModel):
    """Schema for creating a new academic year."""
    name: str = Field(..., min_length=4, max_length=20, examples=["2026-27"])
    start_date: date
    end_date: date
    is_active: bool = True


class AcademicYearResponse(BaseModel):
    """Schema for academic year details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime


class SubjectCreate(BaseModel):
    """Schema for creating a subject."""
    code: str = Field(..., min_length=1, max_length=30, examples=["CS601"])
    name: str = Field(..., min_length=1, max_length=150, examples=["Software Engineering"])
    semester: int = Field(..., ge=1, le=10)
    academic_year_id: uuid.UUID
    department: str = Field(..., min_length=1, max_length=100)
    credits: float = Field(3.0, gt=0)


class SubjectResponse(BaseModel):
    """Schema for subject details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    semester: int
    academic_year_id: uuid.UUID
    department: str
    credits: float
    created_at: datetime


class SubjectAssignmentCreate(BaseModel):
    """Schema for assigning a subject to a faculty member."""
    faculty_profile_id: Optional[uuid.UUID] = None
    faculty_id: Optional[str] = None


class SubjectAssignmentResponse(BaseModel):
    """Schema for subject assignment details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    subject_id: uuid.UUID
    assigned_at: datetime
    is_active: bool
    subject: Optional[SubjectResponse] = None
    faculty_profile: Optional[FacultyProfileResponse] = None
