"""
AI-NBA Readiness System — Backend
app/models/faculty_data.py

Models for faculty academic and professional achievements:
- Qualifications
- Experience
- Certificates (with version history support)
- Publications
- Patents
- FDPs, Workshops, and Training
- Research Projects
- Consultancy
- Professional & Departmental Contributions

All models support soft deletion.
"""

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
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
    from app.models.faculty import FacultyProfile


class FacultyQualification(Base):
    """Educational qualifications of a faculty member."""
    __tablename__ = "faculty_qualifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    degree: Mapped[str] = mapped_column(String(100), nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(150), nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    university: Mapped[str] = mapped_column(String(200), nullable=False)
    year_of_passing: Mapped[int] = mapped_column(Integer, nullable=False)
    grade_or_percentage: Mapped[str] = mapped_column(String(50), nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationship
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="qualifications", lazy="selectin"
    )


class FacultyExperience(Base):
    """Teaching, industry, and research experience of a faculty member."""
    __tablename__ = "faculty_experiences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    experience_type: Mapped[str] = mapped_column(String(50), default="Teaching", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles_and_responsibilities: Mapped[str] = mapped_column(Text, nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationship
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="experiences", lazy="selectin"
    )


class FacultyCertificate(Base):
    """
    Certificates and credentials with version history retention.
    Historical versions are retained with is_current=False and a reference to the root certificate.
    """
    __tablename__ = "faculty_certificates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issuing_organization: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    credential_id: Mapped[str] = mapped_column(String(100), nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    parent_certificate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_certificates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationship
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="certificates", lazy="selectin"
    )


class FacultyPublication(Base):
    """Academic publications (Journals, Conferences, Books, Chapters)."""
    __tablename__ = "faculty_publications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publication_type: Mapped[str] = mapped_column(String(50), nullable=False)
    journal_or_conference_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issn_or_isbn: Mapped[str] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[date] = mapped_column(Date, nullable=True)
    volume_issue_pages: Mapped[str] = mapped_column(String(100), nullable=True)
    doi_or_url: Mapped[str] = mapped_column(String(255), nullable=True)
    indexing: Mapped[str] = mapped_column(String(100), nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="publications", lazy="selectin"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", lazy="selectin"
    )


class FacultyPatent(Base):
    """Intellectual property and patents filed/granted."""
    __tablename__ = "faculty_patents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    application_number: Mapped[str] = mapped_column(String(100), nullable=False)
    patent_number: Mapped[str] = mapped_column(String(100), nullable=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    grant_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Filed", nullable=False)
    inventors: Mapped[str] = mapped_column(String(255), nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationship
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="patents", lazy="selectin"
    )


class FacultyTraining(Base):
    """FDPs, workshops, STTPs, and specialized trainings attended or organized."""
    __tablename__ = "faculty_trainings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    program_type: Mapped[str] = mapped_column(String(50), nullable=False)
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="Participant", nullable=False)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="trainings", lazy="selectin"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", lazy="selectin"
    )


class FacultyProject(Base):
    """Funded research projects and grants."""
    __tablename__ = "faculty_projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    funding_agency: Mapped[str] = mapped_column(String(200), nullable=False)
    grant_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sanction_date: Mapped[date] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Ongoing", nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="Principal Investigator", nullable=False)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="projects", lazy="selectin"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", lazy="selectin"
    )


class FacultyConsultancy(Base):
    """Industrial and institutional consultancy projects."""
    __tablename__ = "faculty_consultancies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_title: Mapped[str] = mapped_column(String(255), nullable=False)
    client_organization: Mapped[str] = mapped_column(String(200), nullable=False)
    financial_outlay: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Ongoing", nullable=False)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="consultancies", lazy="selectin"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", lazy="selectin"
    )


class FacultyContribution(Base):
    """Departmental, institutional, and professional contributions."""
    __tablename__ = "faculty_contributions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    faculty_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)

    # Soft deletion & auditing
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    faculty_profile: Mapped["FacultyProfile"] = relationship(
        "FacultyProfile", back_populates="contributions", lazy="selectin"
    )
    academic_year: Mapped["AcademicYear"] = relationship(
        "AcademicYear", lazy="selectin"
    )
