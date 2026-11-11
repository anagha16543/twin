# metrics_service.py
"""
Deterministic Metrics Calculation Service for NBA Accreditation Readiness.

Principle:
All mathematical calculations (means, minimums, maximums, ranges, distributions,
and ratios) are executed deterministically by Python.
The Language Model (LLM) is NEVER allowed to perform arithmetic.
"""

from collections import Counter
from statistics import mean
from typing import Any, Dict, List, Optional


def calculate_student_statistics(
    student_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate exact numerical statistics from student assessment records.

    Safely handles optional columns (e.g. if Attendance or Internal Total
    is not directly supplied in custom inputs, it handles them gracefully
    without raising KeyError).

    Args:
        student_records: List of dictionaries containing student assessment scores.

    Returns:
        Structured dictionary of numerical metrics.
    """
    if not student_records:
        return {
            "record_count": 0,
            "error": "No student records provided for statistical calculation."
        }

    stats: Dict[str, Any] = {
        "record_count": len(student_records)
    }

    # Helper to calculate stats for a numerical field if present
    def compute_field_stats(field_name: str) -> Optional[Dict[str, Any]]:
        values = [
            float(rec[field_name])
            for rec in student_records
            if field_name in rec and rec[field_name] is not None
        ]
        if not values:
            return None

        return {
            "average": round(mean(values), 2),
            "minimum": min(values),
            "maximum": max(values),
            "range": round(max(values) - min(values), 2)
        }

    # 1. CIE-I
    cie1_stats = compute_field_stats("CIE-I")
    if cie1_stats:
        stats["CIE-I"] = cie1_stats

    # 2. CIE-II
    cie2_stats = compute_field_stats("CIE-II")
    if cie2_stats:
        stats["CIE-II"] = cie2_stats

    # 3. Micro Project
    mp_stats = compute_field_stats("Micro Project")
    if mp_stats:
        stats["Micro Project"] = mp_stats

    # 4. Internal Total (use provided field, or sum components if available)
    internal_values = []
    for rec in student_records:
        if "Internal Total" in rec and rec["Internal Total"] is not None:
            internal_values.append(float(rec["Internal Total"]))
        elif "CIE-I" in rec and "CIE-II" in rec and "Micro Project" in rec:
            # Deterministic summation if total wasn't pre-computed
            c1 = float(rec.get("CIE-I", 0) or 0)
            c2 = float(rec.get("CIE-II", 0) or 0)
            mp = float(rec.get("Micro Project", 0) or 0)
            internal_values.append(c1 + c2 + mp)

    if internal_values:
        stats["Internal Total"] = {
            "average": round(mean(internal_values), 2),
            "minimum": min(internal_values),
            "maximum": max(internal_values),
            "range": round(max(internal_values) - min(internal_values), 2)
        }

    # 5. Attendance
    att_values = [
        int(rec["Attendance"])
        for rec in student_records
        if "Attendance" in rec and rec["Attendance"] is not None
    ]
    if att_values:
        stats["Attendance"] = {
            "average": round(mean(att_values), 2),
            "minimum": min(att_values),
            "maximum": max(att_values),
            "range": round(max(att_values) - min(att_values), 2),
            "distribution": dict(sorted(Counter(att_values).items()))
        }
    else:
        stats["Attendance"] = {
            "status": "Attendance records not provided in supplied student input."
        }

    return stats


def calculate_grade_distribution_metrics(
    grade_distribution: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate and summarize course-level grade distributions deterministically.
    """
    registered = grade_distribution.get("registered", 0)
    appeared = grade_distribution.get("appeared", 0)
    passed = grade_distribution.get("passed", 0)

    pass_percentage = (
        round((passed / appeared) * 100, 2)
        if appeared > 0
        else grade_distribution.get("pass_percentage", 0.0)
    )

    grades = grade_distribution.get("grades", {})

    return {
        "registered": registered,
        "appeared": appeared,
        "passed": passed,
        "pass_percentage": pass_percentage,
        "grades": grades
    }


# ============================================================
# CRITERION 4 DETERMINISTIC CALCULATIONS
# ============================================================

def calculate_criterion4_progression_metrics(
    cohort_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic academic progression and completion metrics
    for Criterion 4 across student cohorts.

    Args:
        cohort_records: List of cohort dictionaries containing:
            - batch (e.g., '2020-2024')
            - admitted_count
            - completed_without_backlog
            - completed_with_backlog (optional, default 0)

    Returns:
        Dictionary containing cohort-level and aggregate completion metrics.
    """
    if not cohort_records:
        return {
            "cohort_count": 0,
            "status": "No cohort progression records provided."
        }

    cohort_summaries = []
    total_admitted = 0
    total_completed_without_backlog = 0
    total_completed_with_backlog = 0

    for cohort in cohort_records:
        batch = cohort.get("batch", "Unknown Batch")
        admitted = int(cohort.get("admitted_count", 0))
        without_backlog = int(cohort.get("completed_without_backlog", 0))
        with_backlog = int(cohort.get("completed_with_backlog", 0))

        rate_without_backlog = (
            round((without_backlog / admitted) * 100, 2)
            if admitted > 0 else 0.0
        )
        total_completed = without_backlog + with_backlog
        overall_completion_rate = (
            round((total_completed / admitted) * 100, 2)
            if admitted > 0 else 0.0
        )

        cohort_summaries.append({
            "batch": batch,
            "admitted_count": admitted,
            "completed_without_backlog": without_backlog,
            "completed_with_backlog": with_backlog,
            "total_graduated": total_completed,
            "completion_rate_without_backlog_pct": rate_without_backlog,
            "overall_completion_rate_pct": overall_completion_rate
        })

        total_admitted += admitted
        total_completed_without_backlog += without_backlog
        total_completed_with_backlog += with_backlog

    agg_without_backlog_rate = (
        round((total_completed_without_backlog / total_admitted) * 100, 2)
        if total_admitted > 0 else 0.0
    )
    agg_overall_rate = (
        round(
            (total_completed_without_backlog + total_completed_with_backlog)
            / total_admitted * 100,
            2
        )
        if total_admitted > 0 else 0.0
    )

    return {
        "cohort_count": len(cohort_records),
        "cohorts": cohort_summaries,
        "aggregate": {
            "total_admitted": total_admitted,
            "total_completed_without_backlog": total_completed_without_backlog,
            "total_completed_with_backlog": total_completed_with_backlog,
            "total_graduated": (
                total_completed_without_backlog + total_completed_with_backlog
            ),
            "aggregate_completion_rate_without_backlog_pct": agg_without_backlog_rate,
            "aggregate_overall_completion_rate_pct": agg_overall_rate
        }
    }


def calculate_criterion4_placement_metrics(
    placement_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic placement, higher studies, and entrepreneurship
    metrics for Criterion 4.

    Args:
        placement_records: List of academic-year placement records containing:
            - academic_year (e.g., '2023-24')
            - final_year_students
            - placed_count
            - higher_studies_count
            - entrepreneurship_count (optional, default 0)
            - median_salary_lpa (optional)

    Returns:
        Dictionary containing year-wise and aggregate progression metrics.
    """
    if not placement_records:
        return {
            "record_count": 0,
            "status": "No placement records provided."
        }

    year_summaries = []
    tot_final_year = 0
    tot_placed = 0
    tot_higher_studies = 0
    tot_entrepreneurs = 0

    for rec in placement_records:
        year = rec.get("academic_year", "Unknown Year")
        final_year = int(rec.get("final_year_students", 0))
        placed = int(rec.get("placed_count", 0))
        higher = int(rec.get("higher_studies_count", 0))
        entrepreneur = int(rec.get("entrepreneurship_count", 0))

        progressed = placed + higher + entrepreneur

        placement_pct = (
            round((placed / final_year) * 100, 2)
            if final_year > 0 else 0.0
        )
        total_progression_pct = (
            round((progressed / final_year) * 100, 2)
            if final_year > 0 else 0.0
        )

        year_summaries.append({
            "academic_year": year,
            "final_year_students": final_year,
            "placed_count": placed,
            "higher_studies_count": higher,
            "entrepreneurship_count": entrepreneur,
            "total_progressed": progressed,
            "placement_pct": placement_pct,
            "total_progression_pct": total_progression_pct,
            "median_salary_lpa": rec.get("median_salary_lpa", None)
        })

        tot_final_year += final_year
        tot_placed += placed
        tot_higher_studies += higher
        tot_entrepreneurs += entrepreneur

    tot_progressed = tot_placed + tot_higher_studies + tot_entrepreneurs
    agg_placement_pct = (
        round((tot_placed / tot_final_year) * 100, 2)
        if tot_final_year > 0 else 0.0
    )
    agg_progression_pct = (
        round((tot_progressed / tot_final_year) * 100, 2)
        if tot_final_year > 0 else 0.0
    )

    return {
        "year_count": len(placement_records),
        "years": year_summaries,
        "aggregate": {
            "total_final_year_students": tot_final_year,
            "total_placed": tot_placed,
            "total_higher_studies": tot_higher_studies,
            "total_entrepreneurs": tot_entrepreneurs,
            "total_progressed": tot_progressed,
            "aggregate_placement_pct": agg_placement_pct,
            "aggregate_progression_pct": agg_progression_pct
        }
    }


def summarize_student_achievements(
    achievement_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Summarize student professional achievements, technical competitions,
    and certifications deterministically, categorizing verified vs pending records.
    """
    if not achievement_records:
        return {
            "total_achievements": 0,
            "status": "No student achievement records provided."
        }

    categories = Counter()
    verification_status = Counter()

    for item in achievement_records:
        cat = item.get("category", "Uncategorized")
        is_verified = item.get("verified", False)
        categories[cat] += 1
        verification_status["verified" if is_verified else "pending_verification"] += 1

    return {
        "total_achievements": len(achievement_records),
        "categories": dict(categories),
        "verification_breakdown": dict(verification_status)
    }


# ============================================================
# CRITERION 5 DETERMINISTIC CALCULATIONS (FACULTY INFO)
# ============================================================

def calculate_criterion5_sfr(
    total_students: int,
    regular_faculty_count: int
) -> Dict[str, Any]:
    """
    Calculate deterministic Student-to-Faculty Ratio (SFR) for Criterion 5.

    Formula: SFR = Total Enrolled Students (UG 2nd, 3rd, 4th yr + PG) / Regular Faculty Count

    Args:
        total_students: Total number of students.
        regular_faculty_count: Number of qualified regular faculty members.

    Returns:
        Dictionary containing SFR value and student/faculty counts.
    """
    if regular_faculty_count <= 0:
        return {
            "total_students": total_students,
            "regular_faculty_count": regular_faculty_count,
            "sfr_ratio": None,
            "error": "Regular faculty count must be greater than zero to compute SFR."
        }

    sfr = round(total_students / regular_faculty_count, 2)

    return {
        "total_students": total_students,
        "regular_faculty_count": regular_faculty_count,
        "sfr_ratio": sfr,
        "student_to_faculty_ratio": sfr,
        "sfr_display": f"{sfr}:1"
    }


def calculate_criterion5_cadre_metrics(
    faculty_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic Cadre Ratio and Qualification distribution.

    Designations:
        - Professor
        - Associate Professor
        - Assistant Professor

    Qualifications:
        - Ph.D. / Doctorate
        - Master's (M.Tech / M.E. / M.S.)
    """
    if not faculty_records:
        return {
            "total_faculty": 0,
            "status": "No faculty records provided."
        }

    total_faculty = len(faculty_records)
    prof_count = 0
    assoc_prof_count = 0
    asst_prof_count = 0
    phd_count = 0
    masters_count = 0

    for fac in faculty_records:
        desig = fac.get("designation", "").strip().lower()
        if "assistant professor" in desig or "asst. prof" in desig:
            asst_prof_count += 1
        elif "associate professor" in desig or "assoc. prof" in desig:
            assoc_prof_count += 1
        elif "professor" in desig:
            prof_count += 1
        else:
            asst_prof_count += 1  # Default / other teaching staff

        qual = fac.get("qualification", "").strip().lower()
        if "ph.d" in qual or "phd" in qual or "doctorate" in qual:
            phd_count += 1
        else:
            masters_count += 1

    phd_pct = round((phd_count / total_faculty) * 100, 2) if total_faculty > 0 else 0.0

    return {
        "total_faculty": total_faculty,
        "cadre_counts": {
            "professors": prof_count,
            "associate_professors": assoc_prof_count,
            "assistant_professors": asst_prof_count
        },
        "cadre_ratio_display": f"{prof_count} : {assoc_prof_count} : {asst_prof_count}",
        "qualifications": {
            "phd_count": phd_count,
            "masters_count": masters_count,
            "phd_percentage": phd_pct
        }
    }


def calculate_criterion5_experience_metrics(
    faculty_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic teaching experience and retention metrics.
    """
    if not faculty_records:
        return {
            "status": "No faculty records provided for experience calculation."
        }

    total_exp_list = [
        float(fac["total_experience_years"])
        for fac in faculty_records
        if "total_experience_years" in fac and fac["total_experience_years"] is not None
    ]

    inst_exp_list = [
        float(fac["institution_experience_years"])
        for fac in faculty_records
        if "institution_experience_years" in fac and fac["institution_experience_years"] is not None
    ]

    avg_total_exp = round(mean(total_exp_list), 2) if total_exp_list else 0.0
    avg_inst_exp = round(mean(inst_exp_list), 2) if inst_exp_list else 0.0

    return {
        "faculty_count_with_experience_data": len(total_exp_list),
        "average_total_experience_years": avg_total_exp,
        "max_total_experience_years": max(total_exp_list) if total_exp_list else 0.0,
        "min_total_experience_years": min(total_exp_list) if total_exp_list else 0.0,
        "average_institution_experience_years": avg_inst_exp
    }


# ============================================================
# CRITERION 6 DETERMINISTIC CALCULATIONS (FACULTY CONTRIBUTIONS)
# ============================================================

def calculate_criterion6_publication_metrics(
    publication_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic publication metrics for Criterion 6.

    Strict Rule:
    Only VERIFIED publications are counted as confirmed achievements.
    Unverified submissions are tracked separately under 'pending_verification'.
    """
    if not publication_records:
        return {
            "total_publications_submitted": 0,
            "confirmed_publications_count": 0,
            "status": "No publication records provided."
        }

    total_submitted = len(publication_records)
    verified_records = [p for p in publication_records if p.get("verified", False)]
    pending_records = [p for p in publication_records if not p.get("verified", False)]

    indexing_counts = Counter()
    for pub in verified_records:
        indexing = pub.get("indexing", "Other").strip()
        indexing_counts[indexing] += 1

    return {
        "total_publications_submitted": total_submitted,
        "confirmed_publications_count": len(verified_records),
        "pending_verification_count": len(pending_records),
        "confirmed_indexing_breakdown": dict(indexing_counts),
        "sci_scopus_confirmed_count": (
            indexing_counts.get("SCI", 0)
            + indexing_counts.get("SCIE", 0)
            + indexing_counts.get("Scopus", 0)
        )
    }


def calculate_criterion6_patent_metrics(
    patent_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic intellectual property / patent metrics.
    Tracks status: Granted, Published, Filed.
    """
    if not patent_records:
        return {
            "total_patents_submitted": 0,
            "confirmed_patents_count": 0,
            "status": "No patent records provided."
        }

    total_submitted = len(patent_records)
    verified_records = [p for p in patent_records if p.get("verified", False)]
    pending_records = [p for p in patent_records if not p.get("verified", False)]

    status_counts = Counter()
    for pat in verified_records:
        status = pat.get("status", "Filed").strip().title()
        status_counts[status] += 1

    return {
        "total_patents_submitted": total_submitted,
        "confirmed_patents_count": len(verified_records),
        "pending_verification_count": len(pending_records),
        "confirmed_status_breakdown": dict(status_counts),
        "confirmed_granted_count": status_counts.get("Granted", 0),
        "confirmed_published_count": status_counts.get("Published", 0),
        "confirmed_filed_count": status_counts.get("Filed", 0)
    }


def calculate_criterion6_project_metrics(
    project_records: List[Dict[str, Any]],
    consultancy_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic R&D project grant totals and consultancy revenue.
    All funding values are computed in INR Lakhs.
    """
    # 1. Sponsored R&D Projects
    verified_projects = [
        p for p in project_records
        if p.get("verified", False)
    ]
    tot_project_funding_lakhs = sum(
        float(p.get("funding_amount_lakhs", 0.0) or 0.0)
        for p in verified_projects
    )

    # 2. Consultancy
    verified_consultancy = [
        c for c in consultancy_records
        if c.get("verified", False)
    ]
    tot_consultancy_revenue_lakhs = sum(
        float(c.get("revenue_amount_lakhs", 0.0) or 0.0)
        for c in verified_consultancy
    )

    return {
        "sponsored_projects": {
            "submitted_count": len(project_records),
            "confirmed_count": len(verified_projects),
            "pending_count": len(project_records) - len(verified_projects),
            "total_funding_amount_lakhs": round(tot_project_funding_lakhs, 2)
        },
        "consultancy": {
            "submitted_count": len(consultancy_records),
            "confirmed_count": len(verified_consultancy),
            "pending_count": len(consultancy_records) - len(verified_consultancy),
            "total_revenue_amount_lakhs": round(tot_consultancy_revenue_lakhs, 2)
        },
        "aggregate_research_revenue_lakhs": round(
            tot_project_funding_lakhs + tot_consultancy_revenue_lakhs, 2
        )
    }


def calculate_criterion6_fdp_metrics(
    fdp_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate deterministic FDP / STTP participation and organization metrics.
    """
    if not fdp_records:
        return {
            "total_fdp_records": 0,
            "status": "No FDP records provided."
        }

    verified_fdps = [f for f in fdp_records if f.get("verified", False)]
    pending_fdps = [f for f in fdp_records if not f.get("verified", False)]

    roles = Counter()
    for f in verified_fdps:
        role = f.get("role", "Attended").strip().title()
        roles[role] += 1

    return {
        "total_fdp_submitted": len(fdp_records),
        "confirmed_fdp_count": len(verified_fdps),
        "pending_verification_count": len(pending_fdps),
        "confirmed_roles": dict(roles)
    }


# ============================================================
# NBA COMPLIANCE AND READINESS DETERMINISTIC EVALUATION
# ============================================================

def evaluate_criterion3_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluate Criterion 3 course and assessment data
    against NBA accreditation rubrics.
    """
    if not data:
        data = {}

    gaps: List[Dict[str, Any]] = []
    total_checks = 6
    passed_checks = 0

    cos = data.get("course_outcomes", [])
    if cos and len(cos) >= 4:
        passed_checks += 1
    elif cos:
        passed_checks += 0.5
        gaps.append({
            "id": "C3-GAP-001",
            "criterion": "Criterion 3",
            "rule": "Course Outcomes Count",
            "severity": "Minor",
            "description": f"Only {len(cos)} COs defined. NBA recommends 4 to 6 COs per course.",
            "evidence_required": "Updated Course Syllabus and Course Articulation Matrix"
        })
    else:
        gaps.append({
            "id": "C3-GAP-001",
            "criterion": "Criterion 3",
            "rule": "Course Outcomes Count",
            "severity": "Critical",
            "description": "No Course Outcomes (COs) defined for the course.",
            "evidence_required": "Approved Course Syllabus with CO statements"
        })

    scheme = data.get("assessment_scheme", {})
    if scheme and ("CIE" in scheme or "CIE-I" in scheme) and ("SEE" in scheme or "End Semester" in scheme):
        passed_checks += 1
    elif scheme:
        passed_checks += 0.5
        gaps.append({
            "id": "C3-GAP-002",
            "criterion": "Criterion 3",
            "rule": "Assessment Scheme",
            "severity": "Major",
            "description": "Incomplete assessment scheme: CIE or SEE component missing.",
            "evidence_required": "Academic Regulations and Assessment Weightage Scheme"
        })
    else:
        gaps.append({
            "id": "C3-GAP-002",
            "criterion": "Criterion 3",
            "rule": "Assessment Scheme",
            "severity": "Critical",
            "description": "No formal assessment scheme defined.",
            "evidence_required": "Institutional Examination and Evaluation Manual"
        })

    assessment_mapping = data.get("assessment_co_mapping", {})
    if assessment_mapping and len(assessment_mapping) >= 2:
        passed_checks += 1
    else:
        gaps.append({
            "id": "C3-GAP-003",
            "criterion": "Criterion 3",
            "rule": "Assessment-to-CO Mapping",
            "severity": "Major",
            "description": "Assessment-to-CO mapping table is incomplete or missing.",
            "evidence_required": "Assessment Mapping Matrix linking questions/tools to COs"
        })

    co_po_mapping = data.get("co_po_pso_mapping", {})
    if co_po_mapping and len(co_po_mapping) >= 4:
        passed_checks += 1
    elif co_po_mapping:
        passed_checks += 0.5
        gaps.append({
            "id": "C3-GAP-004",
            "criterion": "Criterion 3",
            "rule": "CO-PO Mapping Matrix",
            "severity": "Minor",
            "description": "CO-PO-PSO mapping is only partially specified.",
            "evidence_required": "Complete Program Articulation Matrix (CO-PO-PSO)"
        })
    else:
        gaps.append({
            "id": "C3-GAP-004",
            "criterion": "Criterion 3",
            "rule": "CO-PO Mapping Matrix",
            "severity": "Critical",
            "description": "No CO-PO-PSO correlation matrix available.",
            "evidence_required": "Department Curriculum Book with CO-PO Mapping"
        })

    data_quality = data.get("data_quality", {})
    co_formula_present = data_quality.get("official_co_attainment_formula_available", False)
    if co_formula_present:
        passed_checks += 1
    else:
        gaps.append({
            "id": "C3-GAP-005",
            "criterion": "Criterion 3",
            "rule": "CO Attainment Formula",
            "severity": "Critical",
            "description": "Official CO direct attainment calculation formula and threshold not documented.",
            "evidence_required": "Departmental Assessment and Attainment Policy Document"
        })

    see_marks_present = data_quality.get("student_level_see_marks_available", False)
    if see_marks_present:
        passed_checks += 1
    else:
        gaps.append({
            "id": "C3-GAP-006",
            "criterion": "Criterion 3",
            "rule": "Summative Assessment Data",
            "severity": "Major",
            "description": "Student-level SEE component marks are missing; only course-level grade distribution available.",
            "evidence_required": "University / Controller of Examinations Mark Sheets"
        })

    completeness_pct = round((passed_checks / total_checks) * 100, 2)
    if completeness_pct >= 85:
        status = "Compliant"
    elif completeness_pct >= 60:
        status = "Partially Compliant"
    else:
        status = "Needs Improvement"

    return {
        "criterion": "Criterion 3",
        "completeness_percentage": completeness_pct,
        "status": status,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "gaps_count": len(gaps),
        "gaps": gaps
    }


def evaluate_criterion4_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluate Criterion 4 student performance and progression
    against NBA accreditation rubrics.
    """
    if not data:
        data = {}

    gaps: List[Dict[str, Any]] = []
    total_checks = 4
    passed_checks = 0

    cohort_records = data.get("cohorts", [])
    placement_records = data.get("placements", [])
    achievement_records = data.get("achievements", [])

    prog_metrics = calculate_criterion4_progression_metrics(cohort_records)
    if prog_metrics.get("cohort_count", 0) > 0:
        agg = prog_metrics.get("aggregate", {})
        rate_without_backlog = agg.get("aggregate_completion_rate_without_backlog_pct", 0.0)
        overall_rate = agg.get("aggregate_overall_completion_rate_pct", 0.0)

        if rate_without_backlog >= 60.0 and overall_rate >= 80.0:
            passed_checks += 1
        elif overall_rate >= 70.0:
            passed_checks += 0.5
            gaps.append({
                "id": "C4-GAP-001",
                "criterion": "Criterion 4",
                "rule": "Academic Progression Rate",
                "severity": "Major",
                "description": f"Completion without backlog ({rate_without_backlog}%) is below optimal NBA target (60%).",
                "evidence_required": "Remedial Coaching Records and Mentorship Logs"
            })
        else:
            gaps.append({
                "id": "C4-GAP-001",
                "criterion": "Criterion 4",
                "rule": "Academic Progression Rate",
                "severity": "Critical",
                "description": f"Overall graduation rate ({overall_rate}%) is low (< 70%).",
                "evidence_required": "Student Support Policy and Academic Retention Analysis"
            })
    else:
        gaps.append({
            "id": "C4-GAP-001",
            "criterion": "Criterion 4",
            "rule": "Academic Progression Data",
            "severity": "Critical",
            "description": "No cohort progression data provided.",
            "evidence_required": "Official Cohort Enrolment and Graduation Registers"
        })

    place_metrics = calculate_criterion4_placement_metrics(placement_records)
    if place_metrics.get("year_count", 0) > 0:
        agg_place = place_metrics.get("aggregate", {})
        progression_rate = agg_place.get("aggregate_progression_pct", 0.0)

        if progression_rate >= 80.0:
            passed_checks += 1
        elif progression_rate >= 60.0:
            passed_checks += 0.75
            gaps.append({
                "id": "C4-GAP-002",
                "criterion": "Criterion 4",
                "rule": "Career Progression Rate",
                "severity": "Minor",
                "description": f"Placement and progression rate is {progression_rate}%. Target for full score is >= 80%.",
                "evidence_required": "Training & Placement Cell Annual Report and Offer Letters"
            })
        else:
            gaps.append({
                "id": "C4-GAP-002",
                "criterion": "Criterion 4",
                "rule": "Career Progression Rate",
                "severity": "Major",
                "description": f"Placement and progression rate ({progression_rate}%) is below 60%.",
                "evidence_required": "Career Guidance and Industry Interaction Action Plan"
            })
    else:
        gaps.append({
            "id": "C4-GAP-002",
            "criterion": "Criterion 4",
            "rule": "Placement Records",
            "severity": "Critical",
            "description": "No placement or higher education records provided.",
            "evidence_required": "Verified Placement Registers and Higher Education Admission Proofs"
        })

    achieve_summary = summarize_student_achievements(achievement_records)
    total_ach = achieve_summary.get("total_achievements", 0)
    pending_ach = achieve_summary.get("verification_breakdown", {}).get("pending_verification", 0)

    if total_ach > 0:
        if pending_ach == 0:
            passed_checks += 1
        else:
            passed_checks += 0.5
            gaps.append({
                "id": "C4-GAP-003",
                "criterion": "Criterion 4",
                "rule": "Achievement Verification",
                "severity": "Minor",
                "description": f"{pending_ach} out of {total_ach} student achievements are missing verification proof documents.",
                "evidence_required": "Participation and Award Certificates for Pending Entries"
            })
    else:
        gaps.append({
            "id": "C4-GAP-003",
            "criterion": "Criterion 4",
            "rule": "Student Achievements",
            "severity": "Major",
            "description": "No student co-curricular, technical, or sports achievements logged.",
            "evidence_required": "Student Activity Register and Event Participation Certificates"
        })

    if data.get("competitive_exams") is not None:
        passed_checks += 1
    else:
        gaps.append({
            "id": "C4-GAP-004",
            "criterion": "Criterion 4",
            "rule": "Competitive Examinations",
            "severity": "Minor",
            "description": "Data on competitive exams (GATE, CAT, GRE, TOEFL, IELTS) is not documented.",
            "evidence_required": "Student Scorecards for Competitive Examinations"
        })

    completeness_pct = round((passed_checks / total_checks) * 100, 2)
    if completeness_pct >= 85:
        status = "Compliant"
    elif completeness_pct >= 60:
        status = "Partially Compliant"
    else:
        status = "Needs Improvement"

    return {
        "criterion": "Criterion 4",
        "completeness_percentage": completeness_pct,
        "status": status,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "progression_metrics": prog_metrics,
        "placement_metrics": place_metrics,
        "gaps_count": len(gaps),
        "gaps": gaps
    }


def evaluate_criterion5_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluate Criterion 5 faculty data against NBA rubrics.
    """
    if not data:
        data = {}

    gaps: List[Dict[str, Any]] = []
    total_checks = 5
    passed_checks = 0

    faculty_records = data.get("faculty_members", [])
    total_students = int(data.get("total_enrolled_students", 0))

    sfr_metrics = calculate_criterion5_sfr(total_students, len(faculty_records))
    sfr = sfr_metrics.get("sfr_ratio") or sfr_metrics.get("student_to_faculty_ratio") or 0.0

    if sfr > 0:
        if sfr <= 15.0:
            passed_checks += 1
        elif sfr <= 20.0:
            passed_checks += 0.7
            gaps.append({
                "id": "C5-GAP-001",
                "criterion": "Criterion 5",
                "rule": "Student-to-Faculty Ratio",
                "severity": "Minor",
                "description": f"SFR is {sfr}:1. Optimal target for full marks is <= 15:1.",
                "evidence_required": "Faculty Recruitment Plan and Workload Distribution Matrix"
            })
        elif sfr <= 25.0:
            passed_checks += 0.3
            gaps.append({
                "id": "C5-GAP-001",
                "criterion": "Criterion 5",
                "rule": "Student-to-Faculty Ratio",
                "severity": "Major",
                "description": f"SFR is {sfr}:1, which incurs an NBA penalty. Recommended <= 20:1.",
                "evidence_required": "Urgent Faculty Recruitment Sanction Order"
            })
        else:
            gaps.append({
                "id": "C5-GAP-001",
                "criterion": "Criterion 5",
                "rule": "Student-to-Faculty Ratio",
                "severity": "Critical",
                "description": f"SFR is {sfr}:1, which exceeds the NBA ceiling of 25:1 (Zero marks).",
                "evidence_required": "Emergency Faculty Hiring and Board Approval"
            })
    else:
        gaps.append({
            "id": "C5-GAP-001",
            "criterion": "Criterion 5",
            "rule": "Student-to-Faculty Ratio",
            "severity": "Critical",
            "description": "Student intake or faculty count is zero or missing.",
            "evidence_required": "Sanctioned Student Intake and Faculty Appointment Orders"
        })

    cadre_metrics = calculate_criterion5_cadre_metrics(faculty_records)
    cadre_counts = cadre_metrics.get("cadre_counts", {})
    profs = cadre_counts.get("professors", 0)
    assoc_profs = cadre_counts.get("associate_professors", 0)
    asst_profs = cadre_counts.get("assistant_professors", 0)

    if profs >= 1 and assoc_profs >= 2:
        passed_checks += 1
    elif profs >= 1 or assoc_profs >= 1:
        passed_checks += 0.5
        gaps.append({
            "id": "C5-GAP-002",
            "criterion": "Criterion 5",
            "rule": "Cadre Ratio",
            "severity": "Major",
            "description": f"Cadre distribution ({profs}:{assoc_profs}:{asst_profs}) has deficit in Professors/Associate Professors against NBA norm (1:2:6).",
            "evidence_required": "Cadre Promotion Policy and CAS Documentation"
        })
    else:
        gaps.append({
            "id": "C5-GAP-002",
            "criterion": "Criterion 5",
            "rule": "Cadre Ratio",
            "severity": "Critical",
            "description": "Senior faculty shortage: No full Professors or Associate Professors in the cadre.",
            "evidence_required": "Senior Faculty Recruitment and Retention Strategy"
        })

    qual = cadre_metrics.get("qualifications", {})
    phd_pct = qual.get("phd_percentage", 0.0)

    if phd_pct >= 30.0:
        passed_checks += 1
    elif phd_pct >= 20.0:
        passed_checks += 0.5
        gaps.append({
            "id": "C5-GAP-003",
            "criterion": "Criterion 5",
            "rule": "Faculty Ph.D. Ratio",
            "severity": "Major",
            "description": f"Faculty with Ph.D. is {phd_pct}%. NBA minimum benchmark is >= 30%.",
            "evidence_required": "Faculty Quality Improvement (QIP) and Ph.D. Enrolment Orders"
        })
    else:
        gaps.append({
            "id": "C5-GAP-003",
            "criterion": "Criterion 5",
            "rule": "Faculty Ph.D. Ratio",
            "severity": "Critical",
            "description": f"Critically low Ph.D. faculty ratio ({phd_pct}%). Benchmark is >= 30%.",
            "evidence_required": "Ph.D. Hiring Mandate and Faculty Higher Education Support"
        })

    exp_metrics = calculate_criterion5_experience_metrics(faculty_records)
    avg_inst_exp = exp_metrics.get("average_institution_experience_years", 0.0)

    if avg_inst_exp >= 3.0:
        passed_checks += 1
    elif avg_inst_exp >= 1.5:
        passed_checks += 0.5
        gaps.append({
            "id": "C5-GAP-004",
            "criterion": "Criterion 5",
            "rule": "Faculty Retention",
            "severity": "Minor",
            "description": f"Average institution experience is {avg_inst_exp} years (target >= 3.0 years).",
            "evidence_required": "Faculty Service Registers and Retention Policy"
        })
    else:
        gaps.append({
            "id": "C5-GAP-004",
            "criterion": "Criterion 5",
            "rule": "Faculty Retention",
            "severity": "Major",
            "description": f"High faculty turnover: average institutional stay is only {avg_inst_exp} years.",
            "evidence_required": "Institutional Human Resources and Service Rule Audits"
        })

    unverified_faculty = [f for f in faculty_records if not f.get("verified", False)]
    if len(faculty_records) > 0 and len(unverified_faculty) == 0:
        passed_checks += 1
    elif len(faculty_records) > 0:
        passed_checks += 0.5
        gaps.append({
            "id": "C5-GAP-005",
            "criterion": "Criterion 5",
            "rule": "Faculty Profile Verification",
            "severity": "Major",
            "description": f"{len(unverified_faculty)} faculty records are pending official HR document verification.",
            "evidence_required": "Appointment Orders, Joining Reports, and Degree Certificates"
        })
    else:
        gaps.append({
            "id": "C5-GAP-005",
            "criterion": "Criterion 5",
            "rule": "Faculty Roster",
            "severity": "Critical",
            "description": "No faculty members submitted for verification.",
            "evidence_required": "Approved Department Faculty Roster"
        })

    completeness_pct = round((passed_checks / total_checks) * 100, 2)
    if completeness_pct >= 85:
        status = "Compliant"
    elif completeness_pct >= 60:
        status = "Partially Compliant"
    else:
        status = "Needs Improvement"

    return {
        "criterion": "Criterion 5",
        "completeness_percentage": completeness_pct,
        "status": status,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "sfr_metrics": sfr_metrics,
        "cadre_metrics": cadre_metrics,
        "experience_metrics": exp_metrics,
        "gaps_count": len(gaps),
        "gaps": gaps
    }


def evaluate_criterion6_compliance(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluate Criterion 6 faculty contributions against NBA rubrics.
    """
    if not data:
        data = {}

    gaps: List[Dict[str, Any]] = []
    total_checks = 5
    passed_checks = 0

    publications = data.get("publications", [])
    patents = data.get("patents", [])
    projects = data.get("sponsored_projects", [])
    consultancy = data.get("consultancy", [])
    fdps = data.get("fdps", [])

    pub_metrics = calculate_criterion6_publication_metrics(publications)
    confirmed_pubs = pub_metrics.get("confirmed_publications_count", 0)
    sci_scopus = pub_metrics.get("sci_scopus_confirmed_count", 0)
    pending_pubs = pub_metrics.get("pending_verification_count", 0)

    if confirmed_pubs >= 3:
        if sci_scopus >= 2:
            passed_checks += 1
        else:
            passed_checks += 0.75
            gaps.append({
                "id": "C6-GAP-001",
                "criterion": "Criterion 6",
                "rule": "Journal Indexing Quality",
                "severity": "Minor",
                "description": f"Only {sci_scopus} publications are indexed in SCI/Scopus. Prioritize higher indexed venues.",
                "evidence_required": "Scopus / Web of Science Indexing Verification Pages"
            })
    elif confirmed_pubs > 0:
        passed_checks += 0.5
        gaps.append({
            "id": "C6-GAP-001",
            "criterion": "Criterion 6",
            "rule": "Research Publications Count",
            "severity": "Major",
            "description": f"Low publication volume ({confirmed_pubs} confirmed papers). Target >= 1 paper per faculty annually.",
            "evidence_required": "Journal Reprints, Conference Proceedings, and DOIs"
        })
    else:
        gaps.append({
            "id": "C6-GAP-001",
            "criterion": "Criterion 6",
            "rule": "Research Publications Count",
            "severity": "Critical",
            "description": "No confirmed research publications with documentary evidence.",
            "evidence_required": "Department Research Repository and Publication Reprints"
        })

    if pending_pubs > 0:
        gaps.append({
            "id": "C6-GAP-001B",
            "criterion": "Criterion 6",
            "rule": "Publication Verification",
            "severity": "Minor",
            "description": f"{pending_pubs} publications are pending DOI / proof document verification.",
            "evidence_required": "Paper DOIs and Acceptance/Publication Letters"
        })

    pat_metrics = calculate_criterion6_patent_metrics(patents)
    confirmed_pats = pat_metrics.get("confirmed_patents_count", 0)
    granted = pat_metrics.get("confirmed_granted_count", 0)
    published = pat_metrics.get("confirmed_published_count", 0)

    if confirmed_pats > 0 and (granted > 0 or published > 0):
        passed_checks += 1
    elif confirmed_pats > 0:
        passed_checks += 0.5
        gaps.append({
            "id": "C6-GAP-002",
            "criterion": "Criterion 6",
            "rule": "Patent Commercialization / Grant",
            "severity": "Minor",
            "description": "Patents are currently in Filed status; none yet Published or Granted.",
            "evidence_required": "Patent Journal Publication Gazette / Grant Certificates"
        })
    else:
        gaps.append({
            "id": "C6-GAP-002",
            "criterion": "Criterion 6",
            "rule": "Intellectual Property",
            "severity": "Major",
            "description": "No confirmed patent filings or grants recorded for the department.",
            "evidence_required": "Indian Patent Office Application Filing Receipts / Form 1"
        })

    proj_metrics = calculate_criterion6_project_metrics(projects, consultancy)
    spons = proj_metrics.get("sponsored_projects", {})
    funding_lakhs = spons.get("total_funding_amount_lakhs", 0.0)

    if funding_lakhs >= 10.0:
        passed_checks += 1
    elif funding_lakhs > 0:
        passed_checks += 0.75
        gaps.append({
            "id": "C6-GAP-003",
            "criterion": "Criterion 6",
            "rule": "Sponsored Research Quantum",
            "severity": "Minor",
            "description": f"Sponsored research grant total is INR {funding_lakhs} Lakhs. Target for maximum score is >= 10 Lakhs.",
            "evidence_required": "Grant Sanction Orders and Fund Utilization Certificates"
        })
    else:
        gaps.append({
            "id": "C6-GAP-003",
            "criterion": "Criterion 6",
            "rule": "Sponsored Research",
            "severity": "Major",
            "description": "Zero sponsored research grants or external funding recorded.",
            "evidence_required": "Research Grant Applications and Sanction Letters"
        })

    consult = proj_metrics.get("consultancy", {})
    rev_lakhs = consult.get("total_revenue_amount_lakhs", 0.0)

    if rev_lakhs >= 2.0:
        passed_checks += 1
    elif rev_lakhs > 0:
        passed_checks += 0.5
        gaps.append({
            "id": "C6-GAP-004",
            "criterion": "Criterion 6",
            "rule": "Consultancy Revenue",
            "severity": "Minor",
            "description": f"Consultancy revenue is INR {rev_lakhs} Lakhs (benchmark >= 2 Lakhs).",
            "evidence_required": "Client Invoices, Bank Remittance Proofs, and MoUs"
        })
    else:
        gaps.append({
            "id": "C6-GAP-004",
            "criterion": "Criterion 6",
            "rule": "Industrial Consultancy",
            "severity": "Major",
            "description": "No industrial consultancy revenue logged.",
            "evidence_required": "Industry Consultancy Contracts and Work Orders"
        })

    fdp_metrics = calculate_criterion6_fdp_metrics(fdps)
    confirmed_fdp = fdp_metrics.get("confirmed_fdp_count", 0)

    if confirmed_fdp >= 3:
        passed_checks += 1
    elif confirmed_fdp > 0:
        passed_checks += 0.5
        gaps.append({
            "id": "C6-GAP-005",
            "criterion": "Criterion 6",
            "rule": "Faculty Development Participation",
            "severity": "Minor",
            "description": f"Only {confirmed_fdp} confirmed FDP participation records. Target is active participation for all faculty.",
            "evidence_required": "FDP Completion Certificates and Attendance Proofs"
        })
    else:
        gaps.append({
            "id": "C6-GAP-005",
            "criterion": "Criterion 6",
            "rule": "Faculty Development Programs",
            "severity": "Major",
            "description": "No confirmed FDP or STTP participation records provided.",
            "evidence_required": "AICTE/ATAL/NPTEL FDP Certificates"
        })

    completeness_pct = round((passed_checks / total_checks) * 100, 2)
    if completeness_pct >= 85:
        status = "Compliant"
    elif completeness_pct >= 60:
        status = "Partially Compliant"
    else:
        status = "Needs Improvement"

    return {
        "criterion": "Criterion 6",
        "completeness_percentage": completeness_pct,
        "status": status,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "publication_metrics": pub_metrics,
        "patent_metrics": pat_metrics,
        "project_metrics": proj_metrics,
        "fdp_metrics": fdp_metrics,
        "gaps_count": len(gaps),
        "gaps": gaps
    }


def evaluate_department_readiness(
    department_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministically synthesize readiness metrics and compliance statuses
    across Criteria 3, 4, 5, and 6.
    """
    if not department_data:
        department_data = {}

    c3_input = department_data.get("criterion3", {})
    c4_input = department_data.get("criterion4", {})
    c5_input = department_data.get("criterion5", {})
    c6_input = department_data.get("criterion6", {})

    c3_eval = evaluate_criterion3_compliance(c3_input)
    c4_eval = evaluate_criterion4_compliance(c4_input)
    c5_eval = evaluate_criterion5_compliance(c5_input)
    c6_eval = evaluate_criterion6_compliance(c6_input)

    weights = {
        "criterion3": 0.25,
        "criterion4": 0.25,
        "criterion5": 0.25,
        "criterion6": 0.25
    }

    composite_score = round(
        c3_eval["completeness_percentage"] * weights["criterion3"]
        + c4_eval["completeness_percentage"] * weights["criterion4"]
        + c5_eval["completeness_percentage"] * weights["criterion5"]
        + c6_eval["completeness_percentage"] * weights["criterion6"],
        2
    )

    all_gaps: List[Dict[str, Any]] = (
        c3_eval["gaps"] + c4_eval["gaps"] + c5_eval["gaps"] + c6_eval["gaps"]
    )

    critical_gaps = [g for g in all_gaps if g.get("severity") == "Critical"]
    major_gaps = [g for g in all_gaps if g.get("severity") == "Major"]
    minor_gaps = [g for g in all_gaps if g.get("severity") == "Minor"]

    if len(critical_gaps) > 0 or composite_score < 60.0:
        verdict = "Low Readiness - Critical Action Required"
        status = "Non-Compliant"
    elif len(major_gaps) > 3 or composite_score < 80.0:
        verdict = "Moderate Readiness - Gaps Identified"
        status = "Partially Compliant"
    else:
        verdict = "High Readiness - Inspection Ready"
        status = "Compliant"

    return {
        "department": department_data.get("department", "Department Not Specified"),
        "composite_readiness_score": composite_score,
        "overall_status": status,
        "readiness_verdict": verdict,
        "criterion_breakdown": {
            "criterion3": c3_eval,
            "criterion4": c4_eval,
            "criterion5": c5_eval,
            "criterion6": c6_eval
        },
        "gap_summary": {
            "total_gaps": len(all_gaps),
            "critical_count": len(critical_gaps),
            "major_count": len(major_gaps),
            "minor_count": len(minor_gaps),
            "critical_gaps": critical_gaps,
            "major_gaps": major_gaps,
            "minor_gaps": minor_gaps
        }
    }
