"""
AI-NBA Readiness System — Backend
app/schemas/faculty_data.py

Pydantic schemas for faculty achievements:
- Qualifications
- Experience
- Certificates (with version history support)
- Publications
- Patents
- Trainings (FDPs, Workshops, STTPs)
- Projects (Research Grants)
- Consultancies
- Contributions (Departmental & Professional)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Qualifications
# ---------------------------------------------------------------------------

class FacultyQualificationCreate(BaseModel):
    degree: str = Field(..., min_length=1, max_length=100)
    field_of_study: str = Field(..., min_length=1, max_length=150)
    institution: str = Field(..., min_length=1, max_length=200)
    university: str = Field(..., min_length=1, max_length=200)
    year_of_passing: int = Field(..., ge=1950, le=2100)
    grade_or_percentage: Optional[str] = Field(None, max_length=50)
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyQualificationUpdate(BaseModel):
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    university: Optional[str] = None
    year_of_passing: Optional[int] = None
    grade_or_percentage: Optional[str] = None
    document_reference: Optional[str] = None


class FacultyQualificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    degree: str
    field_of_study: str
    institution: str
    university: str
    year_of_passing: int
    grade_or_percentage: Optional[str] = None
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

class FacultyExperienceCreate(BaseModel):
    designation: str = Field(..., min_length=1, max_length=100)
    organization: str = Field(..., min_length=1, max_length=200)
    experience_type: str = Field("Teaching", max_length=50)
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    roles_and_responsibilities: Optional[str] = None
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyExperienceUpdate(BaseModel):
    designation: Optional[str] = None
    organization: Optional[str] = None
    experience_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    roles_and_responsibilities: Optional[str] = None
    document_reference: Optional[str] = None


class FacultyExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    designation: str
    organization: str
    experience_type: str
    start_date: date
    end_date: Optional[date] = None
    is_current: bool
    roles_and_responsibilities: Optional[str] = None
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Certificates (with Versioning)
# ---------------------------------------------------------------------------

class FacultyCertificateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    issuing_organization: str = Field(..., min_length=1, max_length=200)
    issue_date: date
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = Field(None, max_length=100)
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyCertificateReplace(BaseModel):
    """Payload to upload/replace a certificate, creating a new version."""
    title: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    document_reference: Optional[str] = None


class FacultyCertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    title: str
    issuing_organization: str
    issue_date: date
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    document_reference: Optional[str] = None
    version: int
    is_current: bool
    parent_certificate_id: Optional[uuid.UUID] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

class FacultyPublicationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    publication_type: str = Field(..., max_length=50)
    journal_or_conference_name: str = Field(..., min_length=1, max_length=255)
    academic_year_id: Optional[uuid.UUID] = None
    issn_or_isbn: Optional[str] = Field(None, max_length=50)
    publication_date: Optional[date] = None
    volume_issue_pages: Optional[str] = Field(None, max_length=100)
    doi_or_url: Optional[str] = Field(None, max_length=255)
    indexing: Optional[str] = Field(None, max_length=100)
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyPublicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    academic_year_id: Optional[uuid.UUID] = None
    title: str
    publication_type: str
    journal_or_conference_name: str
    issn_or_isbn: Optional[str] = None
    publication_date: Optional[date] = None
    volume_issue_pages: Optional[str] = None
    doi_or_url: Optional[str] = None
    indexing: Optional[str] = None
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Patents
# ---------------------------------------------------------------------------

class FacultyPatentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    application_number: str = Field(..., min_length=1, max_length=100)
    patent_number: Optional[str] = Field(None, max_length=100)
    filing_date: date
    grant_date: Optional[date] = None
    status: str = Field("Filed", max_length=50)
    inventors: Optional[str] = Field(None, max_length=255)
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyPatentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    title: str
    application_number: str
    patent_number: Optional[str] = None
    filing_date: date
    grant_date: Optional[date] = None
    status: str
    inventors: Optional[str] = None
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Trainings (FDPs, Workshops, STTPs)
# ---------------------------------------------------------------------------

class FacultyTrainingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    program_type: str = Field(..., max_length=50)
    organization: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=150)
    start_date: date
    end_date: date
    duration_days: Optional[int] = None
    role: str = Field("Participant", max_length=50)
    academic_year_id: Optional[uuid.UUID] = None
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyTrainingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    academic_year_id: Optional[uuid.UUID] = None
    title: str
    program_type: str
    organization: str
    location: Optional[str] = None
    start_date: date
    end_date: date
    duration_days: Optional[int] = None
    role: str
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Research Projects
# ---------------------------------------------------------------------------

class FacultyProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    funding_agency: str = Field(..., min_length=1, max_length=200)
    grant_amount: float = Field(..., ge=0)
    sanction_date: Optional[date] = None
    start_date: date
    end_date: Optional[date] = None
    status: str = Field("Ongoing", max_length=50)
    role: str = Field("Principal Investigator", max_length=100)
    academic_year_id: Optional[uuid.UUID] = None
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    academic_year_id: Optional[uuid.UUID] = None
    title: str
    funding_agency: str
    grant_amount: float
    sanction_date: Optional[date] = None
    start_date: date
    end_date: Optional[date] = None
    status: str
    role: str
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Consultancies
# ---------------------------------------------------------------------------

class FacultyConsultancyCreate(BaseModel):
    project_title: str = Field(..., min_length=1, max_length=255)
    client_organization: str = Field(..., min_length=1, max_length=200)
    financial_outlay: float = Field(..., ge=0)
    start_date: date
    end_date: Optional[date] = None
    status: str = Field("Ongoing", max_length=50)
    academic_year_id: Optional[uuid.UUID] = None
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyConsultancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    academic_year_id: Optional[uuid.UUID] = None
    project_title: str
    client_organization: str
    financial_outlay: float
    start_date: date
    end_date: Optional[date] = None
    status: str
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Contributions
# ---------------------------------------------------------------------------

class FacultyContributionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., max_length=100)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    academic_year_id: Optional[uuid.UUID] = None
    document_reference: Optional[str] = Field(None, max_length=255)


class FacultyContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    faculty_profile_id: uuid.UUID
    academic_year_id: Optional[uuid.UUID] = None
    title: str
    category: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    document_reference: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
