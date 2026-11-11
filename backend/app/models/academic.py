"""
AI-NBA Readiness System — Backend
app/models/academic.py

AcademicYear, Subject, and FacultySubjectAssignment models.
"""

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.faculty import FacultyProfile


class AcademicYear(Base):
    """Academic Year entity (e.g. 2026-27)."""
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
    subjects: Mapped[List["Subject"]] = relationship(
        "Subject",
        back_populates="academic_year",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_academic_year_dates"),
    )

    def __repr__(self) -> str:
        return f"<AcademicYear(name='{self.name}', is_active={self.is_active})>"


class Subject(Base):
    """Subject/Course entity under an Academic Year."""
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    credits: Mapped[float] = mapped_column(
        Float,
        default=3.0,
        nullable=False,
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
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear",
        back_populates="subjects",
        lazy="selectin",
    )
    assignments: Mapped[List["FacultySubjectAssignment"]] = relationship(
        "FacultySubjectAssignment",
        back_populates="subject",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("code", "academic_year_id", name="uq_subject_code_academic_year"),
    )

    def __repr__(self) -> str:
        return f"<Subject(code='{self.code}', name='{self.name}')>"


class FacultySubjectAssignment(Base):
    """Assignment of a Subject to a Faculty Member."""
    __tablename__ = "faculty_subject_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("faculty_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile",
        back_populates="subject_assignments",
        lazy="selectin",
    )
    subject: Mapped["Subject"] = relationship(
        "Subject",
        back_populates="assignments",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "faculty_profile_id",
            "subject_id",
            "is_active",
            name="uq_faculty_subject_active",
        ),
    )

    def __repr__(self) -> str:
        return f"<FacultySubjectAssignment(faculty='{self.faculty_profile_id}', subject='{self.subject_id}', is_active={self.is_active})>"
