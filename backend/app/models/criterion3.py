"""
AI-NBA Readiness System — Backend
app/models/criterion3.py

Criterion 3 (Outcome-Based Assessment) working data:

  AssessmentCOMap         one assessment component (question / test part) -> one CO
  AttainmentConfig        program-approved CO/PO attainment methodology (3.7.2 / 3.8)
  COIndirectAttainment    course-exit-survey result per CO (indirect CO attainment)
  POIndirectAttainment    survey result per PO/PSO (Table 3.8.2)
  AttainmentSnapshot      persisted result of a deterministic attainment computation
  C3RubricScore           reviewer scores for the manual's rubric components
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AssessmentCOMap(Base):
    __tablename__ = "c3_assessment_co_maps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_scheme_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    assessment_scheme = relationship("AssessmentScheme", lazy="selectin")
    course_outcome = relationship("CourseOutcome", lazy="selectin")

    __table_args__ = (UniqueConstraint("assessment_scheme_id", name="uq_c3_assessment_one_co"),)


class AttainmentConfig(Base):
    __tablename__ = "c3_attainment_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    # A student "attains" a CO when they score >= this % of the CO's marks.
    student_threshold_pct: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    # Attainment level from % of students attaining the CO.
    level3_pct: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)
    level2_pct: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    level1_pct: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    # Direct attainment = CIE weight x CIE level + SEE weight x SEE level
    cie_weight: Mapped[float] = mapped_column(Float, default=40.0, nullable=False)
    see_weight: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    # Final attainment = direct weight x direct + indirect weight x indirect
    direct_weight: Mapped[float] = mapped_column(Float, default=80.0, nullable=False)
    indirect_weight: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    co_target_level: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    po_target_level: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (UniqueConstraint("department", "academic_year_id", name="uq_c3_config_dept_year"),)


class COIndirectAttainment(Base):
    __tablename__ = "c3_co_indirect"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # % of respondents rating the CO as achieved in the course exit survey
    survey_pct: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class POIndirectAttainment(Base):
    __tablename__ = "c3_po_indirect"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    survey_name: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome_code: Mapped[str] = mapped_column(String(20), nullable=False)  # PO1..PO11, PSO1..
    level: Mapped[float] = mapped_column(Float, nullable=False)  # 0..3
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("department", "academic_year_id", "survey_name", "outcome_code",
                         name="uq_c3_po_indirect"),
    )


class AttainmentSnapshot(Base):
    __tablename__ = "c3_attainment_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    computed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class C3RubricScore(Base):
    __tablename__ = "c3_rubric_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    rubric_code: Mapped[str] = mapped_column(String(10), nullable=False)    # "3.1"
    component_key: Mapped[str] = mapped_column(String(5), nullable=False)   # "A"
    score: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("department", "academic_year_id", "rubric_code", "component_key",
                         name="uq_c3_rubric_score"),
    )
