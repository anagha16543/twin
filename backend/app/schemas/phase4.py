"""
AI-NBA Readiness System — Backend
app/schemas/phase4.py

Pydantic v2 request/response schemas for Phase 4:
  - NBA Criteria and Requirements
  - Requirement Evaluations
  - Documents
  - Evidence associations
  - RAG retrieval
  - AI analysis

Internal file paths are never returned in API responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# NBA Criteria
# ---------------------------------------------------------------------------

class NBACriterionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    max_marks: float
    guideline_version: str
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# NBA Requirements
# ---------------------------------------------------------------------------

class NBARequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    criterion_id: uuid.UUID
    code: str
    title: str
    description: Optional[str]
    weightage: float
    is_mandatory: bool
    evaluation_rule_key: str
    display_order: int
    is_active: bool
    created_at: datetime


class NBARequirementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = None
    weightage: float = Field(ge=0.0)
    is_mandatory: bool = True
    evaluation_rule_key: str = Field(min_length=3, max_length=120)
    display_order: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Requirement Evaluations
# ---------------------------------------------------------------------------

class EvaluationTriggerRequest(BaseModel):
    """Body for triggering a deterministic evaluation."""
    academic_year_id: uuid.UUID
    department: str = Field(min_length=2, max_length=100)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured backend data required by the evaluation rule.",
    )
    notes: Optional[str] = None


class RequirementEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    academic_year_id: uuid.UUID
    department: str
    status: str
    score_attained: float
    max_score: float
    mode: str
    deterministic_metrics: Optional[dict]
    limitations: Optional[list]
    ai_interpretation: Optional[str]
    ai_findings: Optional[dict]
    ai_confidence: Optional[float]
    notes: Optional[str]
    evaluated_at: datetime


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentOut(BaseModel):
    """Safe document metadata — never exposes stored_filename."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    department: str
    academic_year_id: uuid.UUID
    version: int
    is_current: bool
    parent_document_id: Optional[uuid.UUID]
    is_deleted: bool
    processing_status: str
    validation_status: str
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response after a successful document upload."""
    document_id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    is_duplicate: bool
    processing_status: str
    message: str


class DocumentSoftDeleteOut(BaseModel):
    document_id: uuid.UUID
    is_deleted: bool
    message: str


# ---------------------------------------------------------------------------
# Requirement Evidence
# ---------------------------------------------------------------------------

class RequirementEvidenceLinkIn(BaseModel):
    document_id: uuid.UUID
    is_primary: bool = False
    relevance_note: Optional[str] = Field(default=None, max_length=500)


class RequirementEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    document_id: uuid.UUID
    is_primary: bool
    relevance_note: Optional[str]
    linked_at: datetime


# ---------------------------------------------------------------------------
# Document Chunks / RAG
# ---------------------------------------------------------------------------

class ChunkMatchOut(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section_heading: Optional[str]
    content: str
    similarity_score: Optional[float]


class RAGQueryIn(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    department: Optional[str] = None
    academic_year_id: Optional[uuid.UUID] = None
    criterion_code: Optional[str] = None


class RAGQueryOut(BaseModel):
    query: str
    results: list[ChunkMatchOut]
    total: int
    embedding_available: bool


# ---------------------------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------------------------

class AIAnalysisTriggerIn(BaseModel):
    requirement_id: uuid.UUID
    academic_year_id: uuid.UUID
    department: str = Field(min_length=2, max_length=100)
    analysis_task: str = Field(default="general_analysis", max_length=100)
    top_k_passages: int = Field(default=5, ge=1, le=10)


class AIAnalysisOut(BaseModel):
    request_id: str
    correlation_id: str
    criterion_code: str
    status: str
    summary: Optional[str]
    findings: list[dict]
    recommended_actions: list[str]
    confidence_score: Optional[float]
    limitations: list[str]
    execution_time_ms: Optional[int]
    error: Optional[str]
    ai_drives_compliance: bool = False  # ALWAYS False — backend only
