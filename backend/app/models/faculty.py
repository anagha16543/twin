"""
AI-NBA Readiness System — Backend
app/models/faculty.py

FacultyProfile model for academic faculty metadata.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.academic import FacultySubjectAssignment
    from app.models.faculty_data import (
        FacultyCertificate,
        FacultyConsultancy,
        FacultyContribution,
        FacultyExperience,
        FacultyPatent,
        FacultyProject,
        FacultyPublication,
        FacultyQualification,
        FacultyTraining,
    )
    from app.models.user import User


class FacultyProfile(Base):
    """Faculty profile metadata linked 1-to-1 with a User."""
    __tablename__ = "faculty_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    faculty_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    designation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    contact_number: Mapped[str] = mapped_column(
        String(30),
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="faculty_profile",
    )
    subject_assignments: Mapped[List["FacultySubjectAssignment"]] = relationship(
        "FacultySubjectAssignment",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Phase 3 Faculty achievement relationships
    qualifications: Mapped[List["FacultyQualification"]] = relationship(
        "FacultyQualification",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    experiences: Mapped[List["FacultyExperience"]] = relationship(
        "FacultyExperience",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    certificates: Mapped[List["FacultyCertificate"]] = relationship(
        "FacultyCertificate",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    publications: Mapped[List["FacultyPublication"]] = relationship(
        "FacultyPublication",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    patents: Mapped[List["FacultyPatent"]] = relationship(
        "FacultyPatent",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    trainings: Mapped[List["FacultyTraining"]] = relationship(
        "FacultyTraining",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    projects: Mapped[List["FacultyProject"]] = relationship(
        "FacultyProject",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    consultancies: Mapped[List["FacultyConsultancy"]] = relationship(
        "FacultyConsultancy",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    contributions: Mapped[List["FacultyContribution"]] = relationship(
        "FacultyContribution",
        back_populates="faculty_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<FacultyProfile(faculty_id='{self.faculty_id}', name='{self.full_name}')>"
