"""
AI-NBA Readiness System — Backend
app/models/phase5.py

Phase 5 models:
  - Gap              : Identified accreditation readiness gaps requiring corrective action
  - CorrectiveAction : Trackable remediation tasks assigned to faculty / HOD
  - Notification     : User-targeted persistent in-app notifications
  - BackupRecord     : Metadata for created system archives & backups

Design notes
------------
* All models use standard SQLAlchemy 2.0 mapped_column and Mapped types.
* Enums are stored as strings for SQLite and PostgreSQL compatibility.
* Soft-deleted or inactive records are filtered at the service query layer.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.academic import AcademicYear
    from app.models.phase4 import NBACriterion, NBARequirement, RequirementEvaluation
    from app.models.user import User


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class GapStatus(str, enum.Enum):
    IDENTIFIED = "IDENTIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GapSeverity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionStatus(str, enum.Enum):
    IDENTIFIED = "IDENTIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActionPriority(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NotificationType(str, enum.Enum):
    REGISTRATION_PENDING = "REGISTRATION_PENDING"
    FACULTY_STATUS_CHANGED = "FACULTY_STATUS_CHANGED"
    SUBJECT_ASSIGNED = "SUBJECT_ASSIGNED"
    EVALUATION_WARNING = "EVALUATION_WARNING"
    EVALUATION_FAIL = "EVALUATION_FAIL"
    GAP_ASSIGNED = "GAP_ASSIGNED"
    ACTION_ASSIGNED = "ACTION_ASSIGNED"
    ACTION_OVERDUE = "ACTION_OVERDUE"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    SYSTEM = "SYSTEM"


class BackupStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"
    RESTORED = "RESTORED"


# ---------------------------------------------------------------------------
# Gap Model
# ---------------------------------------------------------------------------

class Gap(Base):
    """
    Represents an identified readiness issue or compliance gap.
    Generated deterministically from failed/warning requirement evaluations or
    missing mandatory evidence, with manual action creation capabilities.
    """
    __tablename__ = "nba_gaps"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nba_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nba_criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=GapSeverity.MEDIUM.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=GapStatus.IDENTIFIED.value,
        index=True,
    )
    identified_from_evaluation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("requirement_evaluations.id", ondelete="SET NULL"),
        nullable=True,
    )
    responsible_evidence_or_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    requirement: Mapped[NBARequirement] = relationship("NBARequirement")
    criterion: Mapped[NBACriterion] = relationship("NBACriterion")
    academic_year: Mapped[AcademicYear] = relationship("AcademicYear")
    evaluation: Mapped[Optional[RequirementEvaluation]] = relationship("RequirementEvaluation")
    created_by: Mapped[Optional[User]] = relationship("User", foreign_keys=[created_by_user_id])
    actions: Mapped[List[CorrectiveAction]] = relationship(
        "CorrectiveAction",
        back_populates="gap",
        cascade="all, delete-orphan",
        order_by="CorrectiveAction.created_at.asc()",
    )


# ---------------------------------------------------------------------------
# CorrectiveAction Model
# ---------------------------------------------------------------------------

class CorrectiveAction(Base):
    """
    Actionable remediation task linked to an identified gap.
    Assigned to a faculty member or HOD with a due date and completion audit.
    """
    __tablename__ = "nba_corrective_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    gap_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("nba_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ActionStatus.IDENTIFIED.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ActionPriority.MEDIUM.value,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    # Relationships
    gap: Mapped[Gap] = relationship("Gap", back_populates="actions")
    assigned_to: Mapped[Optional[User]] = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by: Mapped[Optional[User]] = relationship("User", foreign_keys=[created_by_user_id])


# ---------------------------------------------------------------------------
# Notification Model
# ---------------------------------------------------------------------------

class Notification(Base):
    """
    Persistent in-app notification delivered to a specific user.
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=NotificationType.SYSTEM.value,
        index=True,
    )
    link_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User")


# ---------------------------------------------------------------------------
# BackupRecord Model
# ---------------------------------------------------------------------------

class BackupRecord(Base):
    """
    Audit record of system archives (database dump + uploaded evidence).
    """
    __tablename__ = "system_backup_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    backup_identifier: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    backup_type: Mapped[str] = mapped_column(String(50), nullable=False, default="FULL")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BackupStatus.COMPLETED.value,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_by: Mapped[Optional[User]] = relationship("User")
