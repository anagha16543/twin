"""
AI-NBA Readiness System — Backend
app/services/criteria_context_service.py

Context aggregation service for NBA Criteria 3, 4, 5, and 6.

Responsibilities:
  - Query backend database models for academic, faculty, curriculum, and research data.
  - Structure aggregated data into context dictionaries matching the requirements
    of deterministic evaluation rules (in app/business_rules/criterionX_rules.py).
  - Provide safe defaults and limitation notes when records are missing.
  - Strict Rule: This service performs ONLY data retrieval and aggregation.
    It does NOT compute compliance decisions or assign accreditation scores.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.academic import Subject
from app.models.curriculum import (
    CourseOutcome,
    COPOMapping,
    SubjectEnrolment,
    Student,
    StudentAssessmentMark,
)
from app.models.faculty import FacultyProfile
from app.models.faculty_data import (
    FacultyPublication,
    FacultyPatent,
    FacultyProject,
    FacultyTraining,
    FacultyConsultancy,
    FacultyContribution,
    FacultyQualification,
    FacultyExperience,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Criterion 3 Context Aggregator
# ---------------------------------------------------------------------------

def get_c3_context(
    db: Session,
    department: str,
    academic_year_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Aggregate database records for NBA Criterion 3:
    Course Outcomes and Program Outcomes.
    """
    query = db.query(Subject).filter(Subject.department == department)
    if academic_year_id:
        query = query.filter(Subject.academic_year_id == academic_year_id)
    subjects = query.all()

    total_subjects = len(subjects)
    subjects_with_cos = 0
    all_cos: List[CourseOutcome] = []

    for s in subjects:
        cos = db.query(CourseOutcome).filter(CourseOutcome.subject_id == s.id).all()
        if cos:
            subjects_with_cos += 1
            all_cos.extend(cos)

    total_cos = len(all_cos)
    cos_with_po_map = 0

    if total_cos > 0:
        co_ids = [co.id for co in all_cos]
        mapped_co_ids = (
            db.query(COPOMapping.course_outcome_id)
            .filter(COPOMapping.course_outcome_id.in_(co_ids))
            .distinct()
            .all()
        )
        cos_with_po_map = len(mapped_co_ids)

    return {
        "department": department,
        "academic_year_id": str(academic_year_id) if academic_year_id else None,
        "total_subjects": total_subjects,
        "subjects_with_cos": subjects_with_cos,
        "total_cos": total_cos,
        "cos_with_po_map": cos_with_po_map,
        "attainment_formula_configured": False,  # Requires institutional configuration
    }


# ---------------------------------------------------------------------------
# Criterion 4 Context Aggregator
# ---------------------------------------------------------------------------

def get_c4_context(
    db: Session,
    department: str,
    academic_year_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Aggregate database records for NBA Criterion 4:
    Students' Performance.
    """
    student_query = db.query(Student).filter(Student.department == department)
    total_students = student_query.count()

    enrolment_query = (
        db.query(SubjectEnrolment)
        .join(Subject)
        .filter(Subject.department == department)
    )
    if academic_year_id:
        enrolment_query = enrolment_query.filter(Subject.academic_year_id == academic_year_id)

    registered_students = enrolment_query.count()

    # Pass count from marks
    marks_query = (
        db.query(StudentAssessmentMark)
        .join(Subject, StudentAssessmentMark.subject_id == Subject.id)
        .filter(Subject.department == department)
    )
    if academic_year_id:
        marks_query = marks_query.filter(Subject.academic_year_id == academic_year_id)

    total_marks_records = marks_query.count()
    passed_students = marks_query.filter(StudentAssessmentMark.marks_obtained >= 40.0).count()

    avg_marks = marks_query.with_entities(func.avg(StudentAssessmentMark.marks_obtained)).scalar() or 0.0

    return {
        "department": department,
        "academic_year_id": str(academic_year_id) if academic_year_id else None,
        "registered_students": registered_students or total_students,
        "passed_students": passed_students,
        "successful": passed_students,
        "appeared": registered_students or total_students,
        "mean_percentage": float(avg_marks),
        "overlap_policy_configured": False,
    }


# ---------------------------------------------------------------------------
# Criterion 5 Context Aggregator
# ---------------------------------------------------------------------------

def get_c5_context(
    db: Session,
    department: str,
    academic_year_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Aggregate database records for NBA Criterion 5:
    Faculty Information.
    """
    faculty_profiles = (
        db.query(FacultyProfile)
        .filter(FacultyProfile.department == department)
        .all()
    )

    total_faculty = len(faculty_profiles)
    faculty_ids = [f.id for f in faculty_profiles]

    phd_count = 0
    mtech_count = 0
    pg_or_phd_count = 0

    if faculty_ids:
        quals = (
            db.query(FacultyQualification)
            .filter(FacultyQualification.faculty_id.in_(faculty_ids))
            .all()
        )
        for q in quals:
            degree_lower = (q.degree or "").lower()
            if "ph.d" in degree_lower or "phd" in degree_lower or "doctor" in degree_lower:
                phd_count += 1
                pg_or_phd_count += 1
            elif "m.tech" in degree_lower or "mtech" in degree_lower or "m.e" in degree_lower or "ms" in degree_lower or "master" in degree_lower:
                mtech_count += 1
                pg_or_phd_count += 1

    # Cadre breakdown by designation
    professors = 0
    assoc_professors = 0
    asst_professors = 0

    for f in faculty_profiles:
        desig = (f.designation or "").lower()
        if "associate" in desig:
            assoc_professors += 1
        elif "assistant" in desig:
            asst_professors += 1
        elif "professor" in desig:
            professors += 1
        else:
            asst_professors += 1

    student_count = db.query(Student).filter(Student.department == department).count()

    return {
        "department": department,
        "academic_year_id": str(academic_year_id) if academic_year_id else None,
        "total_faculty": total_faculty,
        "faculty_with_pg_or_phd": pg_or_phd_count,
        "X": phd_count,
        "Y": mtech_count,
        "AF1": professors,
        "AF2": assoc_professors,
        "AF3": asst_professors,
        "S": student_count,
        "TF": total_faculty,
        "years": [{"S": student_count, "TF": total_faculty}] if total_faculty > 0 else [],
    }


# ---------------------------------------------------------------------------
# Criterion 6 Context Aggregator
# ---------------------------------------------------------------------------

def get_c6_context(
    db: Session,
    department: str,
    academic_year_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Aggregate database records for NBA Criterion 6:
    Faculty Contributions.
    """
    faculty_profiles = (
        db.query(FacultyProfile)
        .filter(FacultyProfile.department == department)
        .all()
    )
    faculty_ids = [f.id for f in faculty_profiles]

    pub_count = 0
    patents_granted = 0
    patents_published = 0
    prototypes = 0
    sponsored_grant_lakhs = 0.0
    consultancy_lakhs = 0.0
    seed_money_lakhs = 0.0

    if faculty_ids:
        pub_count = (
            db.query(FacultyPublication)
            .filter(FacultyPublication.faculty_id.in_(faculty_ids))
            .count()
        )

        patents = (
            db.query(FacultyPatent)
            .filter(FacultyPatent.faculty_id.in_(faculty_ids))
            .all()
        )
        for p in patents:
            status_lower = (p.status or "").lower()
            if "grant" in status_lower:
                patents_granted += 1
            elif "publish" in status_lower:
                patents_published += 1

        projects = (
            db.query(FacultyProject)
            .filter(FacultyProject.faculty_id.in_(faculty_ids))
            .all()
        )
        for prj in projects:
            if prj.amount:
                # Assuming amount stored in raw currency; convert to Lakhs if > 1000
                amt = float(prj.amount)
                sponsored_grant_lakhs += amt / 100000.0 if amt > 1000 else amt

        consultancies = (
            db.query(FacultyConsultancy)
            .filter(FacultyConsultancy.faculty_id.in_(faculty_ids))
            .all()
        )
        for c in consultancies:
            if c.amount:
                amt = float(c.amount)
                consultancy_lakhs += amt / 100000.0 if amt > 1000 else amt

    return {
        "department": department,
        "academic_year_id": str(academic_year_id) if academic_year_id else None,
        "publication_count": pub_count,
        "patents_granted": patents_granted,
        "patents_published": patents_published,
        "prototypes": prototypes,
        "total_grant_lakhs": round(sponsored_grant_lakhs, 2),
        "total_revenue_lakhs": round(consultancy_lakhs, 2),
        "received_lakhs": round(seed_money_lakhs, 2),
        "boundary_resolved": False,
    }
