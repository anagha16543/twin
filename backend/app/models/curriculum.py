"""
AI-NBA Readiness System — Backend
app/models/curriculum.py

Models for academic curriculum, outcomes, assessments, and students:
- Students
- Subject Enrolments
- Program Outcomes (POs) & Program-Specific Outcomes (PSOs)
- Course Outcomes (COs)
- CO-PO & CO-PSO Mappings
- Assessment Schemes & Student Marks (CIE-I, CIE-II, SEE)
- Attendance Records
- Micro-Projects
- Feedback & Surveys
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.academic import AcademicYear, Subject
    from app.models.faculty import FacultyProfile


class Student(Base):
    """Student entity with unique USN and academic tracking."""
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usn: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_semester: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", lazy="selectin")
    enrolments: Mapped[List["SubjectEnrolment"]] = relationship(
        "SubjectEnrolment", back_populates="student", cascade="all, delete-orphan", lazy="selectin"
    )
    assessment_marks: Mapped[List["StudentAssessmentMark"]] = relationship(
        "StudentAssessmentMark", back_populates="student", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[List["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )
    micro_projects: Mapped[List["MicroProject"]] = relationship(
        "MicroProject", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student(usn='{self.usn}', name='{self.full_name}')>"


class SubjectEnrolment(Base):
    """Enrolment linking a student to an academic subject."""
    __tablename__ = "subject_enrolments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="enrolments", lazy="selectin")
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "student_id", "subject_id", "academic_year_id", name="uq_student_subject_academic_year"
        ),
    )


class ProgramOutcome(Base):
    """Program Outcomes (POs) defined for a department."""
    __tablename__ = "program_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("code", "department", name="uq_po_code_department"),
    )

    def __repr__(self) -> str:
        return f"<ProgramOutcome(code='{self.code}', dept='{self.department}')>"


class ProgramSpecificOutcome(Base):
    """Program-Specific Outcomes (PSOs) defined for a department."""
    __tablename__ = "program_specific_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("code", "department", name="uq_pso_code_department"),
    )

    def __repr__(self) -> str:
        return f"<ProgramSpecificOutcome(code='{self.code}', dept='{self.department}')>"


class CourseOutcome(Base):
    """Course Outcomes (COs) defined for a specific subject."""
    __tablename__ = "course_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    po_mappings: Mapped[List["COPOMapping"]] = relationship(
        "COPOMapping", back_populates="course_outcome", cascade="all, delete-orphan", lazy="selectin"
    )
    pso_mappings: Mapped[List["COPSOMapping"]] = relationship(
        "COPSOMapping", back_populates="course_outcome", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("code", "subject_id", name="uq_co_code_subject"),
    )

    def __repr__(self) -> str:
        return f"<CourseOutcome(code='{self.code}', subject='{self.subject_id}')>"


class COPOMapping(Base):
    """Mapping between Course Outcome and Program Outcome with correlation 1, 2, or 3."""
    __tablename__ = "co_po_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("program_outcomes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    correlation_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    course_outcome: Mapped["CourseOutcome"] = relationship("CourseOutcome", back_populates="po_mappings", lazy="selectin")
    program_outcome: Mapped["ProgramOutcome"] = relationship("ProgramOutcome", lazy="selectin")

    __table_args__ = (
        CheckConstraint("correlation_level IN (1, 2, 3)", name="ck_co_po_correlation_level"),
        UniqueConstraint("course_outcome_id", "program_outcome_id", name="uq_co_po_mapping"),
    )


class COPSOMapping(Base):
    """Mapping between Course Outcome and Program-Specific Outcome with correlation 1, 2, or 3."""
    __tablename__ = "co_pso_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    course_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("course_outcomes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_specific_outcome_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("program_specific_outcomes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    correlation_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    course_outcome: Mapped["CourseOutcome"] = relationship("CourseOutcome", back_populates="pso_mappings", lazy="selectin")
    program_specific_outcome: Mapped["ProgramSpecificOutcome"] = relationship("ProgramSpecificOutcome", lazy="selectin")

    __table_args__ = (
        CheckConstraint("correlation_level IN (1, 2, 3)", name="ck_co_pso_correlation_level"),
        UniqueConstraint("course_outcome_id", "program_specific_outcome_id", name="uq_co_pso_mapping"),
    )


class AssessmentScheme(Base):
    """Assessment components for a subject (e.g. CIE-I, CIE-II, SEE)."""
    __tablename__ = "assessment_schemes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    weightage: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")

    __table_args__ = (
        CheckConstraint("max_marks > 0", name="ck_assessment_scheme_max_marks"),
        UniqueConstraint("subject_id", "name", name="uq_assessment_scheme_subject_name"),
    )

    def __repr__(self) -> str:
        return f"<AssessmentScheme(name='{self.name}', subject='{self.subject_id}')>"


class StudentAssessmentMark(Base):
    """Marks obtained by a student in an assessment component."""
    __tablename__ = "student_assessment_marks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_scheme_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marks_obtained: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="assessment_marks", lazy="selectin")
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    assessment_scheme: Mapped["AssessmentScheme"] = relationship("AssessmentScheme", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "marks_obtained >= 0 AND marks_obtained <= max_marks",
            name="ck_student_marks_range",
        ),
        UniqueConstraint("student_id", "assessment_scheme_id", name="uq_student_assessment_scheme"),
    )


class AttendanceRecord(Base):
    """Attendance summary for a student in a subject."""
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    classes_held: Mapped[int] = mapped_column(Integer, nullable=False)
    classes_attended: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="attendance_records", lazy="selectin")
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "classes_held >= 0 AND classes_attended >= 0 AND classes_attended <= classes_held",
            name="ck_attendance_classes_range",
        ),
        UniqueConstraint(
            "student_id", "subject_id", "academic_year_id", name="uq_student_subject_attendance"
        ),
    )


class MicroProject(Base):
    """Micro-project evaluation records."""
    __tablename__ = "micro_projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    guide_faculty_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("faculty_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    marks_obtained: Mapped[float] = mapped_column(Float, nullable=True)
    max_marks: Mapped[float] = mapped_column(Float, default=10.0, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Proposed", nullable=False)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="micro_projects", lazy="selectin")
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", lazy="selectin")
    guide_faculty: Mapped["FacultyProfile"] = relationship("FacultyProfile", lazy="selectin")


class FeedbackSurvey(Base):
    """Stakeholder feedback and course exit survey ratings."""
    __tablename__ = "feedback_surveys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    survey_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stakeholder_type: Mapped[str] = mapped_column(String(50), default="STUDENT", nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", lazy="selectin")
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", lazy="selectin")
    student: Mapped["Student"] = relationship("Student", lazy="selectin")

    __table_args__ = (
        CheckConstraint("rating >= 1.0 AND rating <= 5.0", name="ck_feedback_rating_range"),
    )
