"""
AI-NBA Readiness System — Backend
app/schemas/phase5.py

Pydantic v2 schemas for Phase 5:
  - Digital Twin snapshots & Readiness Analytics
  - Gap Analysis and Corrective Actions
  - In-App Notifications
  - Backup & Restore operations
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Digital Twin & Readiness Analytics Schemas
# ---------------------------------------------------------------------------

class RequirementSummary(BaseModel):
    requirement_id: uuid.UUID
    requirement_code: str
    title: str
    max_score: float
    status: str
    score_attained: Optional[float] = None
    has_evidence: bool = False
    evidence_count: int = 0
    last_evaluated_at: Optional[datetime] = None
    limitations: List[str] = Field(default_factory=list)


class CriterionReadinessAnalytics(BaseModel):
    criterion_id: uuid.UUID
    criterion_code: str
    criterion_name: str
    max_score: float
    total_requirements: int = 0
    passed_requirements: int = 0
    warning_requirements: int = 0
    failed_requirements: int = 0
    not_applicable_requirements: int = 0
    unevaluated_requirements: int = 0
    readiness_percentage: Optional[float] = None
    evidence_availability: float = 0.0
    data_completeness: Dict[str, Any] = Field(default_factory=dict)
    open_gaps: int = 0
    last_evaluation_timestamp: Optional[datetime] = None
    limitations: List[str] = Field(default_factory=list)
    requirements: List[RequirementSummary] = Field(default_factory=list)


class OverallReadiness(BaseModel):
    total_requirements: int = 0
    passed_requirements: int = 0
    warning_requirements: int = 0
    failed_requirements: int = 0
    not_applicable_requirements: int = 0
    unevaluated_requirements: int = 0
    eligible_requirements: int = 0
    readiness_percentage: Optional[float] = None
    readiness_formula: str = (
        "readiness_percentage = (passed_requirements / (total_requirements - not_applicable_requirements)) * 100"
    )
    is_official_nba_score: bool = False
    readiness_explanation: str = (
        "Internal readiness indicator based on deterministic evaluations. "
        "Not an official NBA accreditation score. Official NBA accreditation requires formal evaluation and committee decision."
    )


class DataCompletenessSummary(BaseModel):
    faculty_profiles_count: int = 0
    faculty_qualifications_count: int = 0
    faculty_publications_count: int = 0
    subjects_count: int = 0
    active_subject_assignments_count: int = 0
    students_count: int = 0
    course_outcomes_count: int = 0
    co_po_mappings_count: int = 0
    assessment_marks_count: int = 0
    attendance_records_count: int = 0
    uploaded_documents_count: int = 0
    validated_documents_count: int = 0


class DigitalTwinSnapshotResponse(BaseModel):
    academic_year: str
    academic_year_id: uuid.UUID
    department: str
    generated_at: datetime
    overall: OverallReadiness
    criteria: List[CriterionReadinessAnalytics] = Field(default_factory=list)
    data_completeness: DataCompletenessSummary
    open_gaps: int = 0
    overdue_actions: int = 0
    limitations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Gap Schemas
# ---------------------------------------------------------------------------

class CorrectiveActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gap_id: uuid.UUID
    title: str
    description: str
    assigned_to_user_id: Optional[uuid.UUID] = None
    assigned_to_email: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    is_overdue: bool = False
    completion_notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class CorrectiveActionCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    assigned_to_user_id: Optional[uuid.UUID] = None
    priority: str = Field(default="MEDIUM", pattern="^(HIGH|MEDIUM|LOW)$")
    due_date: Optional[datetime] = None


class CorrectiveActionUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    assigned_to_user_id: Optional[uuid.UUID] = None
    priority: Optional[str] = Field(default=None, pattern="^(HIGH|MEDIUM|LOW)$")
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(default=None, pattern="^(IDENTIFIED|IN_PROGRESS|COMPLETED|CANCELLED)$")
    completion_notes: Optional[str] = None


class GapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    requirement_code: Optional[str] = None
    criterion_id: uuid.UUID
    criterion_code: Optional[str] = None
    academic_year_id: uuid.UUID
    academic_year_name: Optional[str] = None
    department: str
    title: str
    description: str
    severity: str
    status: str
    responsible_evidence_or_data: Optional[str] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    actions: List[CorrectiveActionOut] = Field(default_factory=list)


class GapCreateRequest(BaseModel):
    requirement_id: uuid.UUID
    criterion_id: uuid.UUID
    academic_year_id: uuid.UUID
    department: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    severity: str = Field(default="MEDIUM", pattern="^(HIGH|MEDIUM|LOW)$")
    responsible_evidence_or_data: Optional[str] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None


class GapUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    severity: Optional[str] = Field(default=None, pattern="^(HIGH|MEDIUM|LOW)$")
    status: Optional[str] = Field(default=None, pattern="^(IDENTIFIED|IN_PROGRESS|COMPLETED|CANCELLED)$")
    responsible_evidence_or_data: Optional[str] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None


class GapGenerateRequest(BaseModel):
    academic_year_id: uuid.UUID
    department: str = Field(..., min_length=2, max_length=100)
    criterion_id: Optional[uuid.UUID] = None


class GapGenerateResponse(BaseModel):
    academic_year_id: uuid.UUID
    department: str
    gaps_created: int
    gaps_existing: int
    total_open_gaps: int
    details: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Notification Schemas
# ---------------------------------------------------------------------------

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    link_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    total_count: int
    notifications: List[NotificationOut]


# ---------------------------------------------------------------------------
# Backup & Restore Schemas
# ---------------------------------------------------------------------------

class BackupRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    backup_identifier: str
    backup_type: str
    file_path: str
    file_size_bytes: int
    sha256_hash: str
    status: str
    created_by_user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime


class BackupCreateRequest(BaseModel):
    backup_type: str = Field(default="FULL", pattern="^(FULL|DATA_ONLY|DOCUMENTS_ONLY)$")
    notes: Optional[str] = None


class BackupValidationResponse(BaseModel):
    backup_identifier: str
    is_valid: bool
    archive_exists: bool
    checksum_valid: bool
    archive_size_bytes: int
    manifest: Optional[Dict[str, Any]] = None
    security_checks_passed: bool
    errors: List[str] = Field(default_factory=list)


class RestoreRequest(BaseModel):
    backup_identifier: str
    dry_run: bool = True
    confirm_destructive_acknowledged: bool = False
    notes: Optional[str] = None


class RestoreResponse(BaseModel):
    backup_identifier: str
    status: str
    dry_run: bool
    message: str
    inspected_files_count: int = 0
    errors: List[str] = Field(default_factory=list)
