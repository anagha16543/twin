"""
AI-NBA Readiness System — Backend
app/models/phase4.py

Phase 4 models:
  - NBACriterion          : Top-level accreditation criteria (C3, C4, C5, C6)
  - NBARequirement        : Individual sub-requirements within a criterion
  - RequirementEvaluation : Deterministic evaluation result for a requirement
  - Document              : File metadata for uploaded evidence documents
  - RequirementEvidence   : Many-to-many linking requirements to documents
  - DocumentChunk         : Extracted text chunks with optional vector embedding

Design notes
------------
* `document_chunks.embedding` uses pgvector Vector on PostgreSQL and falls
  back to JSON on SQLite so the test suite (sqlite:///:memory:) can create
  the schema without error.
* All statuses are stored as plain VARCHAR strings using Python Enum values to
  remain compatible with both PostgreSQL and SQLite.
* Evidence upload NEVER automatically satisfies a requirement. Only the
  deterministic evaluation engine may set PASS/FAIL/WARNING/NOT_APPLICABLE.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import JSON as _JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.engine import Dialect

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.academic import AcademicYear
    from app.models.user import User


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RequirementStatus(str, enum.Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_RULE_CLARIFICATION = "NEEDS_RULE_CLARIFICATION"


class EvaluationMode(str, enum.Enum):
    DETERMINISTIC = "DETERMINISTIC"
    AI_ASSISTED = "AI_ASSISTED"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DocumentProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    PROCESSED_PARTIAL = "PROCESSED_PARTIAL"
    FAILED = "FAILED"


class DocumentValidationStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# pgvector compatibility shim
# ---------------------------------------------------------------------------

def _make_vector_column(dimensions: int):
    """
    Return a mapped_column that uses pgvector Vector on PostgreSQL
    and JSON on SQLite so the in-memory test suite continues to work.
    """
    try:
        from pgvector.sqlalchemy import Vector  # type: ignore[import]

        class _DialectAwareVector(Vector):
            def load_dialect_impl(self, dialect: Dialect):
                if dialect.name == "sqlite":
                    return dialect.type_descriptor(_JSONType())
                return super().load_dialect_impl(dialect)

            def process_bind_param(self, value, dialect):
                if dialect.name == "sqlite":
                    return value
                return super().process_bind_param(value, dialect)

            def process_result_value(self, value, dialect):
                if dialect.name == "sqlite":
                    return value
                return super().process_result_value(value, dialect)

        return mapped_column(_DialectAwareVector(dimensions), nullable=True)
    except Exception:
        return mapped_column(_JSONType, nullable=True)


# ---------------------------------------------------------------------------
# Milestone A — NBA Requirements Engine
# ---------------------------------------------------------------------------

class NBACriterion(Base):
    """
    Top-level NBA accreditation criterion.

    max_marks and weightage values are PLACEHOLDERS — official scoring
    details must be confirmed from the institution's NBA SAR documents.
    """
    __tablename__ = "nba_criteria"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    guideline_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NBA-UG-TIER-1"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    requirements: Mapped[List["NBARequirement"]] = relationship(
        "NBARequirement", back_populates="criterion", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<NBACriterion(code='{self.code}')>"


class NBARequirement(Base):
    """
    Individual sub-requirement within a criterion.

    evaluation_rule_key links to a Python function in business_rules/.
    Unknown keys return WARNING rather than crashing or returning PASS.
    """
    __tablename__ = "nba_requirements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("nba_criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weightage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evaluation_rule_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    criterion: Mapped["NBACriterion"] = relationship(
        "NBACriterion", back_populates="requirements"
    )
    evaluations: Mapped[List["RequirementEvaluation"]] = relationship(
        "RequirementEvaluation", back_populates="requirement", cascade="all, delete-orphan"
    )
    evidence_links: Mapped[List["RequirementEvidence"]] = relationship(
        "RequirementEvidence", back_populates="requirement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<NBARequirement(code='{self.code}')>"


class RequirementEvaluation(Base):
    """
    Immutable evaluation snapshot for one requirement / year / department.

    New evaluations are always INSERTed (never UPDATE).
    status is set only by deterministic backend rules.
    ai_interpretation informs explanations but never determines status.
    """
    __tablename__ = "requirement_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("nba_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Deterministic outcome — set only by evaluation engine
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    score_attained: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default=EvaluationMode.DETERMINISTIC.value
    )

    # Payload snapshots
    deterministic_metrics: Mapped[Optional[dict]] = mapped_column(_JSONType, nullable=True)
    limitations: Mapped[Optional[list]] = mapped_column(_JSONType, nullable=True)

    # AI-generated interpretation (advisory only — never drives status)
    ai_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_findings: Mapped[Optional[dict]] = mapped_column(_JSONType, nullable=True)
    ai_request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Audit
    evaluated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    requirement: Mapped["NBARequirement"] = relationship(
        "NBARequirement", back_populates="evaluations"
    )
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear")
    evaluated_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[evaluated_by_user_id]
    )

    def __repr__(self) -> str:
        return (
            f"<RequirementEvaluation(req='{self.requirement_id}', status='{self.status}')>"
        )


# ---------------------------------------------------------------------------
# Milestone B — Document / Evidence Management
# ---------------------------------------------------------------------------

class Document(Base):
    """
    Evidence document metadata. Binary stored on disk; metadata in DB.

    SECURITY: stored_filename is an internal path reference and must NEVER
    be returned directly in API responses. Use signed download URLs or
    streaming endpoints only.

    Evidence presence alone does NOT satisfy an NBA requirement.
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Version lineage
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Soft deletion
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Lifecycle
    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=DocumentProcessingStatus.UPLOADED.value, index=True
    )
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=DocumentValidationStatus.PENDING_REVIEW.value
    )
    validated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[uploaded_by_user_id]
    )
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear")
    evidence_links: Mapped[List["RequirementEvidence"]] = relationship(
        "RequirementEvidence", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', filename='{self.original_filename}', v={self.version})>"


class RequirementEvidence(Base):
    """Links a Document to an NBARequirement as supporting evidence."""
    __tablename__ = "requirement_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("nba_requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    relevance_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linked_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    requirement: Mapped["NBARequirement"] = relationship(
        "NBARequirement", back_populates="evidence_links"
    )
    document: Mapped["Document"] = relationship("Document", back_populates="evidence_links")

    __table_args__ = (
        UniqueConstraint("requirement_id", "document_id", name="uq_req_document"),
    )

    def __repr__(self) -> str:
        return (
            f"<RequirementEvidence(req='{self.requirement_id}', doc='{self.document_id}')>"
        )


# ---------------------------------------------------------------------------
# Milestone D — Text Chunks + Vector Embeddings
# ---------------------------------------------------------------------------

class DocumentChunk(Base):
    """
    Extracted text chunk from a Document for RAG retrieval.

    embedding: uses pgvector Vector(384) on PostgreSQL; JSON list on SQLite.
    Deleted documents cascade-delete their chunks automatically.
    """
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    section_heading: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    embedding_model: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Dialect-aware: Vector(384) on PostgreSQL, JSON on SQLite
    embedding = _make_vector_column(384)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk_index"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(doc='{self.document_id}', "
            f"chunk={self.chunk_index}, page={self.page_number})>"
        )
