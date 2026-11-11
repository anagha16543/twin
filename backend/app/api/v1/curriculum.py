"""
AI-NBA Readiness System — Backend
app/api/v1/curriculum.py

Endpoints for academic curriculum, outcomes, assessments, attendance, and students:
- Students & Subject Enrolments
- Program Outcomes (POs) & Program-Specific Outcomes (PSOs)
- Course Outcomes (COs) & Mappings (CO-PO, CO-PSO)
- Assessment Schemes & Student Marks (CIE-I, CIE-II, SEE)
- Attendance Records
- Micro-Projects
- Feedback & Surveys
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    require_roles,
    verify_subject_faculty_or_admin,
)
from app.models.academic import AcademicYear, Subject
from app.models.curriculum import (
    AssessmentScheme,
    AttendanceRecord,
    COPOMapping,
    COPSOMapping,
    CourseOutcome,
    FeedbackSurvey,
    MicroProject,
    ProgramOutcome,
    ProgramSpecificOutcome,
    Student,
    StudentAssessmentMark,
    SubjectEnrolment,
)
from app.models.user import User, UserRoleName
from app.schemas.curriculum import (
    AssessmentSchemeCreate,
    AssessmentSchemeResponse,
    AttendanceRecordCreate,
    AttendanceRecordResponse,
    COPOMappingCreate,
    COPOMappingResponse,
    COPSOMappingCreate,
    COPSOMappingResponse,
    CourseOutcomeCreate,
    CourseOutcomeResponse,
    FeedbackSurveyCreate,
    FeedbackSurveyResponse,
    MicroProjectCreate,
    MicroProjectResponse,
    ProgramOutcomeCreate,
    ProgramOutcomeResponse,
    ProgramSpecificOutcomeCreate,
    ProgramSpecificOutcomeResponse,
    StudentAssessmentMarkCreate,
    StudentAssessmentMarkResponse,
    StudentCreate,
    StudentResponse,
    SubjectEnrolmentCreate,
    SubjectEnrolmentResponse,
)

router = APIRouter(tags=["Curriculum, Outcomes & Assessments"])


# =============================================================================
# Students & Enrolments
# =============================================================================

@router.post(
    "/students",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register student (HOD or Admin only)",
)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> StudentResponse:
    normalized_usn = payload.usn.upper().strip()
    existing = db.query(Student).filter(Student.usn == normalized_usn).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student with USN '{normalized_usn}' already exists.",
        )

    year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if not year:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found.")

    student = Student(
        usn=normalized_usn,
        full_name=payload.full_name.strip(),
        email=payload.email.lower().strip() if payload.email else None,
        department=payload.department.strip(),
        current_semester=payload.current_semester,
        academic_year_id=payload.academic_year_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentResponse.model_validate(student)


@router.get(
    "/students",
    response_model=List[StudentResponse],
    summary="List students",
)
def list_students(
    department: Optional[str] = Query(None),
    academic_year_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[StudentResponse]:
    query = db.query(Student)
    if department:
        query = query.filter(Student.department == department)
    if academic_year_id:
        query = query.filter(Student.academic_year_id == academic_year_id)

    students = query.order_by(Student.usn.asc()).all()
    return [StudentResponse.model_validate(s) for s in students]


@router.get(
    "/students/{id}",
    response_model=StudentResponse,
    summary="Get student details",
)
def get_student(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return StudentResponse.model_validate(student)


@router.post(
    "/subjects/{subject_id}/enrolments",
    response_model=SubjectEnrolmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enrol student into subject (Assigned Faculty, HOD, or Admin)",
)
def enrol_student(
    subject_id: uuid.UUID,
    payload: SubjectEnrolmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectEnrolmentResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id).first()
    if not year:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found.")

    existing = (
        db.query(SubjectEnrolment)
        .filter(
            SubjectEnrolment.student_id == payload.student_id,
            SubjectEnrolment.subject_id == subject_id,
            SubjectEnrolment.academic_year_id == payload.academic_year_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this subject for this academic year.",
        )

    enrolment = SubjectEnrolment(
        student_id=payload.student_id,
        subject_id=subject.id,
        academic_year_id=payload.academic_year_id,
        is_active=True,
    )
    db.add(enrolment)
    db.commit()
    db.refresh(enrolment)
    return SubjectEnrolmentResponse.model_validate(enrolment)


@router.get(
    "/subjects/{subject_id}/enrolments",
    response_model=List[SubjectEnrolmentResponse],
    summary="List enrolments for a subject",
)
def list_enrolments(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SubjectEnrolmentResponse]:
    verify_subject_faculty_or_admin(subject_id, current_user, db)
    enrolments = (
        db.query(SubjectEnrolment)
        .filter(SubjectEnrolment.subject_id == subject_id)
        .all()
    )
    return [SubjectEnrolmentResponse.model_validate(e) for e in enrolments]


# =============================================================================
# Program Outcomes (POs) & Program-Specific Outcomes (PSOs)
# =============================================================================

@router.post(
    "/program-outcomes",
    response_model=ProgramOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Program Outcome (HOD or Admin only)",
)
def create_program_outcome(
    payload: ProgramOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> ProgramOutcomeResponse:
    code = payload.code.upper().strip()
    existing = (
        db.query(ProgramOutcome)
        .filter(ProgramOutcome.code == code, ProgramOutcome.department == payload.department.strip())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Program outcome '{code}' already exists for department '{payload.department}'.",
        )

    po = ProgramOutcome(
        code=code,
        description=payload.description.strip(),
        department=payload.department.strip(),
        academic_year_id=payload.academic_year_id,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return ProgramOutcomeResponse.model_validate(po)


@router.get(
    "/program-outcomes",
    response_model=List[ProgramOutcomeResponse],
    summary="List Program Outcomes",
)
def list_program_outcomes(
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProgramOutcomeResponse]:
    query = db.query(ProgramOutcome)
    if department:
        query = query.filter(ProgramOutcome.department == department)
    pos = query.order_by(ProgramOutcome.code.asc()).all()
    return [ProgramOutcomeResponse.model_validate(p) for p in pos]


@router.post(
    "/program-specific-outcomes",
    response_model=ProgramSpecificOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Program-Specific Outcome (HOD or Admin only)",
)
def create_pso(
    payload: ProgramSpecificOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> ProgramSpecificOutcomeResponse:
    code = payload.code.upper().strip()
    existing = (
        db.query(ProgramSpecificOutcome)
        .filter(ProgramSpecificOutcome.code == code, ProgramSpecificOutcome.department == payload.department.strip())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Program-specific outcome '{code}' already exists for department '{payload.department}'.",
        )

    pso = ProgramSpecificOutcome(
        code=code,
        description=payload.description.strip(),
        department=payload.department.strip(),
        academic_year_id=payload.academic_year_id,
    )
    db.add(pso)
    db.commit()
    db.refresh(pso)
    return ProgramSpecificOutcomeResponse.model_validate(pso)


@router.get(
    "/program-specific-outcomes",
    response_model=List[ProgramSpecificOutcomeResponse],
    summary="List Program-Specific Outcomes",
)
def list_psos(
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProgramSpecificOutcomeResponse]:
    query = db.query(ProgramSpecificOutcome)
    if department:
        query = query.filter(ProgramSpecificOutcome.department == department)
    psos = query.order_by(ProgramSpecificOutcome.code.asc()).all()
    return [ProgramSpecificOutcomeResponse.model_validate(p) for p in psos]


# =============================================================================
# Course Outcomes (COs) & Mappings
# =============================================================================

@router.post(
    "/subjects/{subject_id}/course-outcomes",
    response_model=CourseOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Course Outcome for Subject (Assigned Faculty, HOD, or Admin)",
)
def create_course_outcome(
    subject_id: uuid.UUID,
    payload: CourseOutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseOutcomeResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)
    code = payload.code.upper().strip()

    existing = (
        db.query(CourseOutcome)
        .filter(CourseOutcome.code == code, CourseOutcome.subject_id == subject.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course outcome '{code}' already exists for this subject.",
        )

    co = CourseOutcome(
        code=code,
        description=payload.description.strip(),
        subject_id=subject.id,
    )
    db.add(co)
    db.commit()
    db.refresh(co)
    return CourseOutcomeResponse.model_validate(co)


@router.get(
    "/subjects/{subject_id}/course-outcomes",
    response_model=List[CourseOutcomeResponse],
    summary="List Course Outcomes for Subject",
)
def list_course_outcomes(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CourseOutcomeResponse]:
    cos = (
        db.query(CourseOutcome)
        .filter(CourseOutcome.subject_id == subject_id)
        .order_by(CourseOutcome.code.asc())
        .all()
    )
    return [CourseOutcomeResponse.model_validate(c) for c in cos]


@router.post(
    "/course-outcomes/{co_id}/po-mappings",
    response_model=COPOMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map Course Outcome to Program Outcome",
)
def create_co_po_mapping(
    co_id: uuid.UUID,
    payload: COPOMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> COPOMappingResponse:
    co = db.query(CourseOutcome).filter(CourseOutcome.id == co_id).first()
    if not co:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course outcome not found.")
    verify_subject_faculty_or_admin(co.subject_id, current_user, db, require_write_permission=True)

    po = db.query(ProgramOutcome).filter(ProgramOutcome.id == payload.program_outcome_id).first()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program outcome not found.")

    existing = (
        db.query(COPOMapping)
        .filter(
            COPOMapping.course_outcome_id == co.id,
            COPOMapping.program_outcome_id == payload.program_outcome_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CO-PO mapping already exists.")

    mapping = COPOMapping(
        course_outcome_id=co.id,
        program_outcome_id=payload.program_outcome_id,
        correlation_level=payload.correlation_level,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return COPOMappingResponse.model_validate(mapping)


@router.get(
    "/course-outcomes/{co_id}/po-mappings",
    response_model=List[COPOMappingResponse],
    summary="List PO mappings for Course Outcome",
)
def list_co_po_mappings(
    co_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[COPOMappingResponse]:
    mappings = db.query(COPOMapping).filter(COPOMapping.course_outcome_id == co_id).all()
    return [COPOMappingResponse.model_validate(m) for m in mappings]


@router.post(
    "/course-outcomes/{co_id}/pso-mappings",
    response_model=COPSOMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Map Course Outcome to Program-Specific Outcome",
)
def create_co_pso_mapping(
    co_id: uuid.UUID,
    payload: COPSOMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> COPSOMappingResponse:
    co = db.query(CourseOutcome).filter(CourseOutcome.id == co_id).first()
    if not co:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course outcome not found.")
    verify_subject_faculty_or_admin(co.subject_id, current_user, db, require_write_permission=True)

    pso = db.query(ProgramSpecificOutcome).filter(ProgramSpecificOutcome.id == payload.program_specific_outcome_id).first()
    if not pso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program-specific outcome not found.")

    existing = (
        db.query(COPSOMapping)
        .filter(
            COPSOMapping.course_outcome_id == co.id,
            COPSOMapping.program_specific_outcome_id == payload.program_specific_outcome_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CO-PSO mapping already exists.")

    mapping = COPSOMapping(
        course_outcome_id=co.id,
        program_specific_outcome_id=payload.program_specific_outcome_id,
        correlation_level=payload.correlation_level,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return COPSOMappingResponse.model_validate(mapping)


@router.get(
    "/course-outcomes/{co_id}/pso-mappings",
    response_model=List[COPSOMappingResponse],
    summary="List PSO mappings for Course Outcome",
)
def list_co_pso_mappings(
    co_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[COPSOMappingResponse]:
    mappings = db.query(COPSOMapping).filter(COPSOMapping.course_outcome_id == co_id).all()
    return [COPSOMappingResponse.model_validate(m) for m in mappings]


# =============================================================================
# Assessment Schemes & Marks
# =============================================================================

@router.post(
    "/subjects/{subject_id}/assessment-schemes",
    response_model=AssessmentSchemeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Assessment Scheme for Subject (Assigned Faculty, HOD, or Admin)",
)
def create_assessment_scheme(
    subject_id: uuid.UUID,
    payload: AssessmentSchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssessmentSchemeResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)
    existing = (
        db.query(AssessmentScheme)
        .filter(
            AssessmentScheme.subject_id == subject.id,
            AssessmentScheme.name == payload.name.strip(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Assessment scheme '{payload.name}' already exists for this subject.",
        )

    scheme = AssessmentScheme(
        subject_id=subject.id,
        name=payload.name.strip(),
        assessment_type=payload.assessment_type.strip(),
        max_marks=payload.max_marks,
        weightage=payload.weightage,
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return AssessmentSchemeResponse.model_validate(scheme)


@router.get(
    "/subjects/{subject_id}/assessment-schemes",
    response_model=List[AssessmentSchemeResponse],
    summary="List Assessment Schemes for Subject",
)
def list_assessment_schemes(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AssessmentSchemeResponse]:
    schemes = (
        db.query(AssessmentScheme)
        .filter(AssessmentScheme.subject_id == subject_id)
        .order_by(AssessmentScheme.created_at.asc())
        .all()
    )
    return [AssessmentSchemeResponse.model_validate(s) for s in schemes]


@router.post(
    "/subjects/{subject_id}/marks",
    response_model=StudentAssessmentMarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record student assessment mark (Assigned Faculty, HOD, or Admin)",
)
def record_student_mark(
    subject_id: uuid.UUID,
    payload: StudentAssessmentMarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentMarkResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)

    scheme = (
        db.query(AssessmentScheme)
        .filter(
            AssessmentScheme.id == payload.assessment_scheme_id,
            AssessmentScheme.subject_id == subject.id,
        )
        .first()
    )
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment scheme not found for this subject.")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    if payload.marks_obtained > scheme.max_marks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Marks obtained ({payload.marks_obtained}) cannot exceed maximum marks ({scheme.max_marks}).",
        )

    existing = (
        db.query(StudentAssessmentMark)
        .filter(
            StudentAssessmentMark.student_id == payload.student_id,
            StudentAssessmentMark.assessment_scheme_id == scheme.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Marks have already been entered for this student in this assessment.",
        )

    mark = StudentAssessmentMark(
        student_id=payload.student_id,
        subject_id=subject.id,
        assessment_scheme_id=scheme.id,
        marks_obtained=payload.marks_obtained,
        max_marks=scheme.max_marks,
        is_absent=payload.is_absent,
    )
    db.add(mark)
    db.commit()
    db.refresh(mark)
    return StudentAssessmentMarkResponse.model_validate(mark)


@router.get(
    "/subjects/{subject_id}/marks",
    response_model=List[StudentAssessmentMarkResponse],
    summary="List student marks for Subject",
)
def list_student_marks(
    subject_id: uuid.UUID,
    assessment_scheme_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[StudentAssessmentMarkResponse]:
    verify_subject_faculty_or_admin(subject_id, current_user, db)
    query = db.query(StudentAssessmentMark).filter(StudentAssessmentMark.subject_id == subject_id)
    if assessment_scheme_id:
        query = query.filter(StudentAssessmentMark.assessment_scheme_id == assessment_scheme_id)
    marks = query.all()
    return [StudentAssessmentMarkResponse.model_validate(m) for m in marks]


# =============================================================================
# Attendance Records
# =============================================================================

@router.post(
    "/subjects/{subject_id}/attendance",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record student attendance (Assigned Faculty, HOD, or Admin)",
)
def record_attendance(
    subject_id: uuid.UUID,
    payload: AttendanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceRecordResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)

    if payload.classes_attended > payload.classes_held:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Classes attended cannot exceed total classes held.",
        )

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    existing = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == payload.student_id,
            AttendanceRecord.subject_id == subject.id,
            AttendanceRecord.academic_year_id == payload.academic_year_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance record already exists for this student and subject in this academic year.",
        )

    percentage = (payload.classes_attended / payload.classes_held * 100.0) if payload.classes_held > 0 else 0.0

    attendance = AttendanceRecord(
        student_id=payload.student_id,
        subject_id=subject.id,
        academic_year_id=payload.academic_year_id,
        classes_held=payload.classes_held,
        classes_attended=payload.classes_attended,
        attendance_percentage=round(percentage, 2),
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return AttendanceRecordResponse.model_validate(attendance)


@router.get(
    "/subjects/{subject_id}/attendance",
    response_model=List[AttendanceRecordResponse],
    summary="List attendance records for Subject",
)
def list_attendance(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AttendanceRecordResponse]:
    verify_subject_faculty_or_admin(subject_id, current_user, db)
    records = db.query(AttendanceRecord).filter(AttendanceRecord.subject_id == subject_id).all()
    return [AttendanceRecordResponse.model_validate(r) for r in records]


# =============================================================================
# Micro-Projects
# =============================================================================

@router.post(
    "/subjects/{subject_id}/micro-projects",
    response_model=MicroProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record micro-project (Assigned Faculty, HOD, or Admin)",
)
def record_micro_project(
    subject_id: uuid.UUID,
    payload: MicroProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MicroProjectResponse:
    subject = verify_subject_faculty_or_admin(subject_id, current_user, db, require_write_permission=True)
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    project = MicroProject(
        subject_id=subject.id,
        student_id=payload.student_id,
        academic_year_id=payload.academic_year_id,
        guide_faculty_id=payload.guide_faculty_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        marks_obtained=payload.marks_obtained,
        max_marks=payload.max_marks,
        status=payload.status.strip(),
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return MicroProjectResponse.model_validate(project)


@router.get(
    "/subjects/{subject_id}/micro-projects",
    response_model=List[MicroProjectResponse],
    summary="List micro-projects for Subject",
)
def list_micro_projects(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MicroProjectResponse]:
    verify_subject_faculty_or_admin(subject_id, current_user, db)
    projects = db.query(MicroProject).filter(MicroProject.subject_id == subject_id).all()
    return [MicroProjectResponse.model_validate(p) for p in projects]


# =============================================================================
# Feedback & Surveys
# =============================================================================

@router.post(
    "/feedback-surveys",
    response_model=FeedbackSurveyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback / survey record",
)
def submit_feedback(
    payload: FeedbackSurveyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackSurveyResponse:
    feedback = FeedbackSurvey(
        survey_type=payload.survey_type.strip(),
        academic_year_id=payload.academic_year_id,
        subject_id=payload.subject_id,
        student_id=payload.student_id,
        stakeholder_type=payload.stakeholder_type.strip(),
        rating=payload.rating,
        comments=payload.comments.strip() if payload.comments else None,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackSurveyResponse.model_validate(feedback)


@router.get(
    "/feedback-surveys",
    response_model=List[FeedbackSurveyResponse],
    summary="List feedback & surveys (HOD or Admin only)",
)
def list_feedback_surveys(
    subject_id: Optional[uuid.UUID] = Query(None),
    academic_year_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
) -> List[FeedbackSurveyResponse]:
    query = db.query(FeedbackSurvey)
    if subject_id:
        query = query.filter(FeedbackSurvey.subject_id == subject_id)
    if academic_year_id:
        query = query.filter(FeedbackSurvey.academic_year_id == academic_year_id)
    records = query.order_by(FeedbackSurvey.created_at.desc()).all()
    return [FeedbackSurveyResponse.model_validate(r) for r in records]
