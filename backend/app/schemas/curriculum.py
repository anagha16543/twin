"""
AI-NBA Readiness System — Backend
app/schemas/curriculum.py

Pydantic schemas for:
- Students & Enrolments
- Program Outcomes (POs) & Program-Specific Outcomes (PSOs)
- Course Outcomes (COs)
- CO-PO & CO-PSO Mappings
- Assessment Schemes & Student Marks
- Attendance Records
- Micro-Projects
- Feedback & Surveys
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Students & Enrolments
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    usn: str = Field(..., min_length=3, max_length=20, examples=["1MS21CS001"])
    full_name: str = Field(..., min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    department: str = Field(..., min_length=1, max_length=100)
    current_semester: int = Field(..., ge=1, le=10)
    academic_year_id: uuid.UUID


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usn: str
    full_name: str
    email: Optional[str] = None
    department: str
    current_semester: int
    academic_year_id: uuid.UUID
    created_at: datetime


class SubjectEnrolmentCreate(BaseModel):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID


class SubjectEnrolmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    enrolled_at: datetime
    is_active: bool
    student: Optional[StudentResponse] = None


# ---------------------------------------------------------------------------
# Program Outcomes (POs) & Program-Specific Outcomes (PSOs)
# ---------------------------------------------------------------------------

class ProgramOutcomeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, examples=["PO1"])
    description: str = Field(..., min_length=5)
    department: str = Field(..., min_length=1, max_length=100)
    academic_year_id: Optional[uuid.UUID] = None


class ProgramOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str
    department: str
    academic_year_id: Optional[uuid.UUID] = None
    created_at: datetime


class ProgramSpecificOutcomeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, examples=["PSO1"])
    description: str = Field(..., min_length=5)
    department: str = Field(..., min_length=1, max_length=100)
    academic_year_id: Optional[uuid.UUID] = None


class ProgramSpecificOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str
    department: str
    academic_year_id: Optional[uuid.UUID] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Course Outcomes (COs) & Mappings
# ---------------------------------------------------------------------------

class CourseOutcomeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, examples=["CO1"])
    description: str = Field(..., min_length=5)


class CourseOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str
    subject_id: uuid.UUID
    created_at: datetime


class COPOMappingCreate(BaseModel):
    program_outcome_id: uuid.UUID
    correlation_level: int = Field(..., ge=1, le=3, description="1=Low, 2=Medium, 3=High")


class COPOMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_outcome_id: uuid.UUID
    program_outcome_id: uuid.UUID
    correlation_level: int
    program_outcome: Optional[ProgramOutcomeResponse] = None


class COPSOMappingCreate(BaseModel):
    program_specific_outcome_id: uuid.UUID
    correlation_level: int = Field(..., ge=1, le=3, description="1=Low, 2=Medium, 3=High")


class COPSOMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_outcome_id: uuid.UUID
    program_specific_outcome_id: uuid.UUID
    correlation_level: int
    program_specific_outcome: Optional[ProgramSpecificOutcomeResponse] = None


# ---------------------------------------------------------------------------
# Assessment Schemes & Marks
# ---------------------------------------------------------------------------

class AssessmentSchemeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, examples=["CIE-I"])
    assessment_type: str = Field(..., max_length=50, examples=["CIE-I", "CIE-II", "SEE"])
    max_marks: float = Field(..., gt=0, examples=[50.0])
    weightage: Optional[float] = Field(None, ge=0)


class AssessmentSchemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    name: str
    assessment_type: str
    max_marks: float
    weightage: Optional[float] = None
    created_at: datetime


class StudentAssessmentMarkCreate(BaseModel):
    student_id: uuid.UUID
    assessment_scheme_id: uuid.UUID
    marks_obtained: float = Field(..., ge=0)
    is_absent: bool = False


class StudentAssessmentMarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    assessment_scheme_id: uuid.UUID
    marks_obtained: float
    max_marks: float
    is_absent: bool
    created_at: datetime
    student: Optional[StudentResponse] = None
    assessment_scheme: Optional[AssessmentSchemeResponse] = None


# ---------------------------------------------------------------------------
# Attendance Records
# ---------------------------------------------------------------------------

class AttendanceRecordCreate(BaseModel):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    classes_held: int = Field(..., ge=0)
    classes_attended: int = Field(..., ge=0)


class AttendanceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    classes_held: int
    classes_attended: int
    attendance_percentage: float
    created_at: datetime
    student: Optional[StudentResponse] = None


# ---------------------------------------------------------------------------
# Micro-Projects
# ---------------------------------------------------------------------------

class MicroProjectCreate(BaseModel):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    guide_faculty_id: Optional[uuid.UUID] = None
    marks_obtained: Optional[float] = Field(None, ge=0)
    max_marks: Optional[float] = Field(10.0, gt=0)
    status: str = Field("Proposed", max_length=50)
    document_reference: Optional[str] = Field(None, max_length=255)


class MicroProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    guide_faculty_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    marks_obtained: Optional[float] = None
    max_marks: Optional[float] = None
    status: str
    document_reference: Optional[str] = None
    created_at: datetime
    student: Optional[StudentResponse] = None


# ---------------------------------------------------------------------------
# Feedback & Surveys
# ---------------------------------------------------------------------------

class FeedbackSurveyCreate(BaseModel):
    survey_type: str = Field(..., min_length=1, max_length=100)
    academic_year_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    student_id: Optional[uuid.UUID] = None
    stakeholder_type: str = Field("STUDENT", max_length=50)
    rating: float = Field(..., ge=1.0, le=5.0)
    comments: Optional[str] = None


class FeedbackSurveyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    survey_type: str
    academic_year_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    student_id: Optional[uuid.UUID] = None
    stakeholder_type: str
    rating: float
    comments: Optional[str] = None
    created_at: datetime
