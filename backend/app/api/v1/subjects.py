"""
AI-NBA Readiness System — Backend
app/api/v1/subjects.py

Endpoints for Academic Years, Subjects, and Faculty Subject Assignments (STEP 6).
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.academic import AcademicYear, FacultySubjectAssignment, Subject
from app.models.faculty import FacultyProfile
from app.models.user import User, UserRoleName
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearResponse,
    SubjectAssignmentCreate,
    SubjectAssignmentResponse,
    SubjectCreate,
    SubjectResponse,
)

router = APIRouter(tags=["Subjects & Academic"])


# =============================================================================
# Academic Years
# =============================================================================

@router.get(
    "/academic-years",
    response_model=List[AcademicYearResponse],
    summary="List academic years",
    description="Retrieve all academic years. Accessible to all authenticated users.",
)
def list_academic_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AcademicYearResponse]:
    """List all academic years."""
    years = db.query(AcademicYear).order_by(AcademicYear.name.desc()).all()
    return [AcademicYearResponse.model_validate(y) for y in years]


@router.post(
    "/academic-years",
    response_model=AcademicYearResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create academic year (HOD or Admin only)",
    description="Register a new academic year period.",
)
def create_academic_year(
    payload: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> AcademicYearResponse:
    """Create a new academic year."""
    if payload.end_date <= payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be strictly after start date.",
        )

    existing = db.query(AcademicYear).filter(AcademicYear.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Academic year '{payload.name}' already exists.",
        )

    academic_year = AcademicYear(
        name=payload.name.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
    )
    db.add(academic_year)
    db.commit()
    db.refresh(academic_year)
    return AcademicYearResponse.model_validate(academic_year)


# =============================================================================
# Subjects
# =============================================================================

@router.get(
    "/subjects",
    response_model=List[SubjectResponse],
    summary="List subjects",
    description="Retrieve subjects with optional filters by department, semester, or academic year.",
)
def list_subjects(
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    academic_year_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SubjectResponse]:
    """List subjects with optional filters."""
    query = db.query(Subject)
    if department:
        query = query.filter(Subject.department == department)
    if semester:
        query = query.filter(Subject.semester == semester)
    if academic_year_id:
        query = query.filter(Subject.academic_year_id == academic_year_id)

    subjects = query.order_by(Subject.code.asc()).all()
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subject (HOD or Admin only)",
    description="Create a new academic subject linked to an academic year.",
)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> SubjectResponse:
    """Create a new subject."""
    # Validate academic year exists
    year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if not year:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced academic year does not exist.",
        )

    # Check for duplicate code in same academic year
    existing = (
        db.query(Subject)
        .filter(
            Subject.code == payload.code.strip(),
            Subject.academic_year_id == payload.academic_year_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subject code '{payload.code}' already exists for this academic year.",
        )

    subject = Subject(
        code=payload.code.strip(),
        name=payload.name.strip(),
        semester=payload.semester,
        academic_year_id=payload.academic_year_id,
        department=payload.department.strip(),
        credits=payload.credits,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectResponse.model_validate(subject)


# =============================================================================
# Subject Assignments
# =============================================================================

@router.post(
    "/subjects/{subject_id}/assignments",
    response_model=SubjectAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign faculty to subject (HOD or Admin only)",
    description="Assign a subject to a faculty member. Prevents duplicate active assignments.",
)
def assign_subject_to_faculty(
    subject_id: uuid.UUID,
    payload: SubjectAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> SubjectAssignmentResponse:
    """Assign a subject to a faculty member."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    faculty = None
    if payload.faculty_profile_id:
        faculty = (
            db.query(FacultyProfile)
            .filter(FacultyProfile.id == payload.faculty_profile_id)
            .first()
        )
    elif payload.faculty_id:
        faculty = (
            db.query(FacultyProfile)
            .filter(FacultyProfile.faculty_id == payload.faculty_id.strip())
            .first()
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either faculty_profile_id or faculty_id must be provided.",
        )

    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found.",
        )

    # Check if an active assignment already exists for this faculty and subject
    active_assignment = (
        db.query(FacultySubjectAssignment)
        .filter(
            FacultySubjectAssignment.subject_id == subject_id,
            FacultySubjectAssignment.faculty_profile_id == faculty.id,
            FacultySubjectAssignment.is_active.is_(True),
        )
        .first()
    )
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faculty member is already actively assigned to this subject.",
        )

    assignment = FacultySubjectAssignment(
        subject_id=subject_id,
        faculty_profile_id=faculty.id,
        is_active=True,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return SubjectAssignmentResponse.model_validate(assignment)


@router.get(
    "/faculty/{faculty_id}/subjects",
    response_model=List[SubjectAssignmentResponse],
    summary="List faculty subject assignments",
    description=(
        "Retrieve all subjects assigned to a given faculty profile (by UUID or faculty ID). "
        "Accessible to HOD, Admin, or the faculty member themselves."
    ),
)
def get_faculty_subjects(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SubjectAssignmentResponse]:
    """Retrieve subjects assigned to a specific faculty member by profile UUID or employee faculty_id."""
    faculty = None
    try:
        fac_uuid = uuid.UUID(faculty_id)
        faculty = db.query(FacultyProfile).filter(FacultyProfile.id == fac_uuid).first()
    except (ValueError, AttributeError):
        pass

    if not faculty:
        faculty = db.query(FacultyProfile).filter(FacultyProfile.faculty_id == faculty_id.strip()).first()

    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty profile not found.",
        )

    # Enforce authorization: must be HOD, ADMIN, or the owner faculty member
    is_admin_or_hod = (
        current_user.has_role(UserRoleName.ADMIN.value)
        or current_user.has_role(UserRoleName.HOD.value)
    )
    is_owner = (
        current_user.faculty_profile is not None
        and current_user.faculty_profile.id == faculty.id
    )

    if not (is_admin_or_hod or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this faculty member's assignments.",
        )

    assignments = (
        db.query(FacultySubjectAssignment)
        .filter(
            FacultySubjectAssignment.faculty_profile_id == faculty.id,
            FacultySubjectAssignment.is_active.is_(True),
        )
        .all()
    )
    return [SubjectAssignmentResponse.model_validate(a) for a in assignments]
