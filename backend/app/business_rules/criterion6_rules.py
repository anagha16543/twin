"""
AI-NBA Readiness System — Backend
app/business_rules/criterion6_rules.py

Deterministic evaluation rules for NBA Criterion 6:
Faculty Contributions (120 marks total).

Sources:
  NBA Manual for UG Engineering Tier I — 2026 Edition
  Annexure VII, Criterion 6 (pp. 164-174)
  Working Rulebook: NBA_Criteria_3_4_5_6_Rulebook_2026_Manual_v2.docx

Structure:
  6.1 Professional Development (60 marks):
      6.1.1  Professional memberships           5 marks
      6.1.2.1 Resource persons invited          5 marks
      6.1.2.2 FDP/STTP participation            5 marks
      6.1.3  MOOC courses developed             7 marks
      6.1.4  MOOC certification by students     8 marks
      6.1.5  FDPs/STTPs organized              10 marks
      6.1.6  Student innovation support        10 marks
      6.1.7  Industry training for students    10 marks

  6.2 Research and Development (60 marks):
      6.2.1  Research publications             10 marks
      6.2.2  PhD students guided                5 marks
      6.2.3  Patents and prototypes            10 marks
      6.2.4  Sponsored research projects       15 marks
      6.2.5  Consultancy projects              15 marks
      6.2.6  Institutional seed money           5 marks

Boundary ambiguities:
  Exact boundary values for 6.1.2.1, 6.1.4, 6.1.6, 6.1.7, 6.2.4, 6.2.5, 6.2.6
  return NEEDS_RULE_CLARIFICATION.
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.business_rules.readiness_rules import (
    EvaluationResult,
    RequirementStatus,
    _missing_data_warning,
    _needs_clarification,
)


# ---------------------------------------------------------------------------
# 6.1.1  Professional Society Memberships — 5 marks (qualitative)
# ---------------------------------------------------------------------------

RULE_MEMBERSHIPS = "criterion6.professional_memberships"


def evaluate_professional_memberships(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.1 Professional Society Memberships — 5 marks (qualitative, reviewer-entered)
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_MEMBERSHIPS,
            missing=["reviewer_score"],
            max_score=5.0,
        )
    score = max(0.0, min(float(score), 5.0))
    status = (
        RequirementStatus.PASS.value if score >= 3.5
        else RequirementStatus.WARNING.value if score >= 2.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=5.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by reviewer."],
    )


# ---------------------------------------------------------------------------
# 6.1.2.1  Resource Persons Invited — 5 marks
# ---------------------------------------------------------------------------

RULE_RESOURCE_PERSONS = "criterion6.resource_persons"

_RESOURCE_PERSON_BOUNDARIES = {2.0, 3.0}


def evaluate_resource_persons(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.2.1 Resource Persons Invited — 5 marks

    Expected context keys:
        yearly_count  list[int]  — number of resource persons per year (up to 3 years)
    """
    yearly: Optional[List] = context.get("yearly_count")
    if not yearly:
        return _missing_data_warning(
            rule=RULE_RESOURCE_PERSONS,
            missing=["yearly_count"],
            max_score=5.0,
        )

    avg = sum(yearly) / len(yearly)

    for b in _RESOURCE_PERSON_BOUNDARIES:
        if abs(avg - b) < 1e-9:
            return _needs_clarification(
                rule=RULE_RESOURCE_PERSONS,
                reason=f"Average resource persons = {avg:.4f} is exactly on boundary {b}. Manual uses strict inequalities.",
                max_score=5.0,
                metrics={"avg_resource_persons": avg},
            )

    if avg > 3.0:
        score = 5.0
    elif avg > 2.0:
        score = 2.0
    else:
        score = 0.0

    status = (
        RequirementStatus.PASS.value if score >= 4.0
        else RequirementStatus.WARNING.value if score >= 2.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=score,
        max_score=5.0,
        deterministic_metrics={"avg_resource_persons": round(avg, 4), "yearly_count": yearly},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.1.2.2  FDP/STTP Participation — 5 marks
# ---------------------------------------------------------------------------

RULE_FDP_PARTICIPATION = "criterion6.fdp_participation"


def evaluate_fdp_participation(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.2.2 FDP/STTP Participation — 5 marks

    Expected context keys:
        yearly_attendances  list[int]   — faculty attendance-days per year (3 years)
        RF                  float       — required faculty
        S                   int         — students (to derive RF if not given)
    """
    yearly: Optional[List] = context.get("yearly_attendances")
    rf = context.get("RF")
    s = context.get("S")

    if not yearly:
        return _missing_data_warning(
            rule=RULE_FDP_PARTICIPATION,
            missing=["yearly_attendances"],
            max_score=5.0,
        )

    if rf is None:
        if s is not None:
            rf = s / 20.0
        else:
            return _missing_data_warning(
                rule=RULE_FDP_PARTICIPATION,
                missing=["RF or S"],
                max_score=5.0,
            )

    if rf <= 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=5.0,
            deterministic_metrics={"RF": rf},
            limitations=["RF <= 0."],
        )

    ap_values = []
    for att in yearly[:3]:
        denom = 0.5 * rf
        ap_values.append((att / denom) if denom > 0 else 0.0)

    avg_ap = sum(ap_values) / len(ap_values)
    score = min(avg_ap, 5.0)

    status = (
        RequirementStatus.PASS.value if score >= 3.5
        else RequirementStatus.WARNING.value if score >= 2.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=5.0,
        deterministic_metrics={
            "RF": round(rf, 2),
            "ap_per_year": [round(a, 4) for a in ap_values],
            "avg_ap": round(avg_ap, 4),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.1.3  MOOC Courses Developed — 7 marks (qualitative)
# ---------------------------------------------------------------------------

RULE_MOOC_DEV = "criterion6.mooc_development"


def evaluate_mooc_development(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.3 MOOC Courses Developed — 7 marks (qualitative, reviewer-entered)
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_MOOC_DEV,
            missing=["reviewer_score"],
            max_score=7.0,
        )
    score = max(0.0, min(float(score), 7.0))
    status = (
        RequirementStatus.PASS.value if score >= 5.0
        else RequirementStatus.WARNING.value if score >= 3.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=7.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by reviewer."],
    )


# ---------------------------------------------------------------------------
# 6.1.4  MOOC Certification by Students — 8 marks
# ---------------------------------------------------------------------------

RULE_MOOC_CERT = "criterion6.mooc_certification"

_MOOC_CERT_BOUNDARIES = {20.0, 30.0}


def evaluate_mooc_certification(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.4 MOOC Certification by Students — 8 marks

    Expected context keys:
        certified_students  int    — students with MOOC certification
        total_students      int    — total enrolled students
        reviewer_score      float  — required for exact score within band
        boundary_resolved   bool
    """
    certified = context.get("certified_students")
    total = context.get("total_students")
    reviewer_score = context.get("reviewer_score")
    boundary_resolved = context.get("boundary_resolved", False)

    if certified is None or total is None:
        return _missing_data_warning(
            rule=RULE_MOOC_CERT,
            missing=["certified_students", "total_students"],
            max_score=8.0,
        )

    if total == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=8.0,
            deterministic_metrics={},
            limitations=["Total students = 0."],
        )

    pct = (certified / total) * 100

    for b in _MOOC_CERT_BOUNDARIES:
        if not boundary_resolved and abs(pct - b) < 1e-9:
            return _needs_clarification(
                rule=RULE_MOOC_CERT,
                reason=f"MOOC certification percentage = {pct:.4f}% is exactly on boundary {b}%.",
                max_score=8.0,
                metrics={"certified_pct": pct},
            )

    if reviewer_score is None:
        if pct > 30.0:
            band_note = "Band: >30% -> 6-8 marks; reviewer must specify exact score."
        elif pct > 20.0:
            band_note = "Band: >20%<30% -> 3-5 marks; reviewer must specify exact score."
        else:
            band_note = "Band: <20% -> 0-2 marks; reviewer must specify exact score."
        return EvaluationResult(
            status=RequirementStatus.WARNING.value,
            score_attained=0.0,
            max_score=8.0,
            deterministic_metrics={"certified_pct": round(pct, 2)},
            limitations=[f"reviewer_score required for final score. {band_note}"],
        )

    score = max(0.0, min(float(reviewer_score), 8.0))
    status = (
        RequirementStatus.PASS.value if score >= 5.5
        else RequirementStatus.WARNING.value if score >= 3.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=8.0,
        deterministic_metrics={"certified_pct": round(pct, 2), "reviewer_score": score},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.1.5  FDPs/STTPs Organized — 10 marks
# ---------------------------------------------------------------------------

RULE_FDP_ORGANIZED = "criterion6.fdp_organized"


def evaluate_fdp_organized(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.5 FDPs/STTPs Organized — 10 marks

    Expected context keys:
        programs  list of dicts, each with:
            duration_days  int  — duration (must be >= 5 days)
            year           int
    """
    programs: Optional[List[dict]] = context.get("programs")
    if programs is None:
        return _missing_data_warning(
            rule=RULE_FDP_ORGANIZED,
            missing=["programs (list of {duration_days, year})"],
            max_score=10.0,
        )

    from collections import defaultdict
    per_year: dict = defaultdict(int)
    skipped = []

    for prog in programs:
        dur = prog.get("duration_days", 0)
        yr = prog.get("year", "unknown")
        if dur >= 5:
            per_year[yr] += 1
        else:
            skipped.append(f"Year {yr}: duration {dur} days < 5, skipped.")

    total_points = sum(min(count, 4) * 2 for count in per_year.values())
    score = min(total_points, 10.0)

    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={
            "qualifying_programs_per_year": dict(per_year),
            "total_points_raw": total_points,
        },
        limitations=skipped,
    )


# ---------------------------------------------------------------------------
# 6.1.6  Student Innovation Support — 10 marks
# ---------------------------------------------------------------------------

RULE_STUDENT_INNOVATION = "criterion6.student_innovation_support"

_INNOVATION_BOUNDARIES = {20.0, 30.0}


def evaluate_student_innovation(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.6 Student Innovation/Entrepreneurship Support — 10 marks
    """
    participating = context.get("participating_students")
    total = context.get("total_students")
    reviewer_score = context.get("reviewer_score")
    boundary_resolved = context.get("boundary_resolved", False)

    if participating is None or total is None:
        return _missing_data_warning(
            rule=RULE_STUDENT_INNOVATION,
            missing=["participating_students", "total_students"],
            max_score=10.0,
        )

    if total == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={},
            limitations=["Total students = 0."],
        )

    pct = (participating / total) * 100

    for b in _INNOVATION_BOUNDARIES:
        if not boundary_resolved and abs(pct - b) < 1e-9:
            return _needs_clarification(
                rule=RULE_STUDENT_INNOVATION,
                reason=f"Participation percentage = {pct:.4f}% is exactly on boundary {b}%.",
                max_score=10.0,
                metrics={"participation_pct": pct},
            )

    if reviewer_score is None:
        return EvaluationResult(
            status=RequirementStatus.WARNING.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={"participation_pct": round(pct, 2)},
            limitations=["reviewer_score required for final marks within band."],
        )

    score = max(0.0, min(float(reviewer_score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"participation_pct": round(pct, 2), "reviewer_score": score},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.1.7  Industry Training for Students — 10 marks
# ---------------------------------------------------------------------------

RULE_INDUSTRY_TRAINING = "criterion6.industry_training"

_INDUSTRY_BOUNDARIES = {20.0, 30.0}


def evaluate_industry_training(context: dict[str, Any]) -> EvaluationResult:
    """
    6.1.7 Industry Training for Students — 10 marks
    """
    trained = context.get("trained_students")
    total = context.get("total_students")
    reviewer_score = context.get("reviewer_score")
    boundary_resolved = context.get("boundary_resolved", False)

    if trained is None or total is None:
        return _missing_data_warning(
            rule=RULE_INDUSTRY_TRAINING,
            missing=["trained_students", "total_students"],
            max_score=10.0,
        )

    if total == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={},
            limitations=["Total students = 0."],
        )

    pct = (trained / total) * 100

    for b in _INDUSTRY_BOUNDARIES:
        if not boundary_resolved and abs(pct - b) < 1e-9:
            return _needs_clarification(
                rule=RULE_INDUSTRY_TRAINING,
                reason=f"Training percentage = {pct:.4f}% is exactly on boundary {b}%.",
                max_score=10.0,
                metrics={"training_pct": pct},
            )

    if reviewer_score is None:
        return EvaluationResult(
            status=RequirementStatus.WARNING.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={"training_pct": round(pct, 2)},
            limitations=["reviewer_score required for final marks within band."],
        )

    score = max(0.0, min(float(reviewer_score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"training_pct": round(pct, 2), "reviewer_score": score},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.1  Research Publications — 10 marks
# ---------------------------------------------------------------------------

RULE_RESEARCH_PUBS = "criterion6.research_publications"


def evaluate_research_publications(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.1 Research Publications — 10 marks
    Sub-scores: count (4 marks, deterministic) + quality (6 marks, reviewer-entered)
    """
    count = context.get("publication_count")
    quality = context.get("quality_score")

    if count is None:
        return _missing_data_warning(
            rule=RULE_RESEARCH_PUBS,
            missing=["publication_count"],
            max_score=10.0,
        )

    count_score = min(float(count), 4.0)

    if quality is None:
        return EvaluationResult(
            status=RequirementStatus.WARNING.value,
            score_attained=round(count_score, 2),
            max_score=10.0,
            deterministic_metrics={"publication_count": count, "count_score": count_score},
            limitations=["quality_score (0-6) required from reviewer for full marks."],
        )

    quality_score = max(0.0, min(float(quality), 6.0))
    score = count_score + quality_score

    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={
            "publication_count": count,
            "count_score": count_score,
            "quality_score": quality_score,
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.2  PhD Students Guided — 5 marks
# ---------------------------------------------------------------------------

RULE_PHD_STUDENTS = "criterion6.phd_students"


def evaluate_phd_students(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.2 PhD Students Guided — 5 marks
    enrolled (2 marks) + graduated (3 marks)
    """
    enrolled = context.get("enrolled_count")
    graduated = context.get("graduated_count")

    if enrolled is None and graduated is None:
        return _missing_data_warning(
            rule=RULE_PHD_STUDENTS,
            missing=["enrolled_count", "graduated_count"],
            max_score=5.0,
        )

    enrolled = enrolled or 0
    graduated = graduated or 0

    enrolled_score = min(float(enrolled), 2.0)
    graduated_score = min(float(graduated), 3.0)
    score = enrolled_score + graduated_score

    status = (
        RequirementStatus.PASS.value if score >= 3.5
        else RequirementStatus.WARNING.value if score >= 2.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=5.0,
        deterministic_metrics={
            "enrolled": enrolled,
            "graduated": graduated,
            "enrolled_score": enrolled_score,
            "graduated_score": graduated_score,
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.3  Patents and Prototypes — 10 marks
# ---------------------------------------------------------------------------

RULE_DEVELOPMENT = "criterion6.development_activities"


def evaluate_development_activities(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.3 Patents and Prototypes — 10 marks
    Sub-scores: granted(4) + published(3) + models/prototypes(3)
    """
    granted = context.get("patents_granted", 0)
    published = context.get("patents_published", 0)
    prototypes = context.get("prototypes", 0)

    if granted is None and published is None and prototypes is None:
        return _missing_data_warning(
            rule=RULE_DEVELOPMENT,
            missing=["patents_granted", "patents_published", "prototypes"],
            max_score=10.0,
        )

    g_score = min(float(granted or 0), 4.0)
    p_score = min(float(published or 0), 3.0)
    m_score = min(float(prototypes or 0), 3.0)
    score = g_score + p_score + m_score

    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={
            "patents_granted": granted, "granted_score": g_score,
            "patents_published": published, "published_score": p_score,
            "prototypes": prototypes, "prototype_score": m_score,
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.4  Sponsored Research Projects — 15 marks
# ---------------------------------------------------------------------------

RULE_SPONSORED = "criterion6.sponsored_research"

_SPONSORED_BOUNDARIES_LAKHS = {1.0, 4.0, 8.0, 12.0, 16.0, 20.0}


def evaluate_sponsored_research(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.4 Sponsored Research Projects — 15 marks

    Expected context keys:
        total_grant_lakhs   float  — cumulative grant in INR Lakhs (CAYm1-CAYm3)
        boundary_resolved   bool
    """
    total = context.get("total_grant_lakhs")
    boundary_resolved = context.get("boundary_resolved", False)

    if total is None:
        return _missing_data_warning(
            rule=RULE_SPONSORED,
            missing=["total_grant_lakhs"],
            max_score=15.0,
        )

    for b in _SPONSORED_BOUNDARIES_LAKHS:
        if not boundary_resolved and abs(total - b) < 1e-6:
            return _needs_clarification(
                rule=RULE_SPONSORED,
                reason=f"Total grant = Rs.{total}L is exactly on boundary Rs.{b}L.",
                max_score=15.0,
                metrics={"total_grant_lakhs": total},
            )

    if total > 20.0:
        score = 15.0
    elif total > 16.0:
        score = 12.0
    elif total > 12.0:
        score = 9.0
    elif total > 8.0:
        score = 6.0
    elif total > 4.0:
        score = 3.0
    elif total > 1.0:
        score = 1.0
    else:
        score = 0.0

    status = (
        RequirementStatus.PASS.value if score >= 10.0
        else RequirementStatus.WARNING.value if score >= 5.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=score,
        max_score=15.0,
        deterministic_metrics={"total_grant_lakhs": total},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.5  Consultancy Projects — 15 marks
# ---------------------------------------------------------------------------

RULE_CONSULTANCY = "criterion6.consultancy_work"

_CONSULTANCY_BOUNDARIES_LAKHS = {1.0, 4.0, 8.0, 12.0, 16.0, 20.0}


def evaluate_consultancy_work(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.5 Consultancy Projects — 15 marks
    Same band structure as 6.2.4.
    """
    total = context.get("total_revenue_lakhs")
    boundary_resolved = context.get("boundary_resolved", False)

    if total is None:
        return _missing_data_warning(
            rule=RULE_CONSULTANCY,
            missing=["total_revenue_lakhs"],
            max_score=15.0,
        )

    for b in _CONSULTANCY_BOUNDARIES_LAKHS:
        if not boundary_resolved and abs(total - b) < 1e-6:
            return _needs_clarification(
                rule=RULE_CONSULTANCY,
                reason=f"Total consultancy revenue = Rs.{total}L is exactly on boundary Rs.{b}L.",
                max_score=15.0,
                metrics={"total_revenue_lakhs": total},
            )

    if total > 20.0:
        score = 15.0
    elif total > 16.0:
        score = 12.0
    elif total > 12.0:
        score = 9.0
    elif total > 8.0:
        score = 6.0
    elif total > 4.0:
        score = 3.0
    elif total > 1.0:
        score = 1.0
    else:
        score = 0.0

    status = (
        RequirementStatus.PASS.value if score >= 10.0
        else RequirementStatus.WARNING.value if score >= 5.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=score,
        max_score=15.0,
        deterministic_metrics={"total_revenue_lakhs": total},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 6.2.6  Institutional Seed Money — 5 marks
# ---------------------------------------------------------------------------

RULE_SEED_MONEY = "criterion6.seed_money"

_SEED_BOUNDARIES_LAKHS = {2.0, 4.0, 6.0}


def evaluate_seed_money(context: dict[str, Any]) -> EvaluationResult:
    """
    6.2.6 Institutional Seed Money — 5 marks
    received (3) + utilized (2)
    """
    received = context.get("received_lakhs")
    utilized = context.get("utilized_lakhs")
    boundary_resolved = context.get("boundary_resolved", False)

    if received is None:
        return _missing_data_warning(
            rule=RULE_SEED_MONEY,
            missing=["received_lakhs"],
            max_score=5.0,
        )

    for b in _SEED_BOUNDARIES_LAKHS:
        if not boundary_resolved and abs(received - b) < 1e-6:
            return _needs_clarification(
                rule=RULE_SEED_MONEY,
                reason=f"Seed money received = Rs.{received}L is exactly on boundary Rs.{b}L.",
                max_score=5.0,
                metrics={"received_lakhs": received},
            )

    # Gap: 1L-2L is unspecified in manual
    if not boundary_resolved and 1.0 < received < 2.0:
        return _needs_clarification(
            rule=RULE_SEED_MONEY,
            reason=(
                f"Seed money received = Rs.{received}L falls in the Rs.1L–Rs.2L range "
                "which is unspecified in the NBA manual. "
                "Confirm institutional interpretation."
            ),
            max_score=5.0,
            metrics={"received_lakhs": received},
        )

    if received > 6.0:
        received_score = 3.0
    elif received > 4.0:
        received_score = 2.0
    elif received > 2.0:
        received_score = 1.0
    else:
        received_score = 0.0

    utilized_score = 0.0
    limitations = []
    if utilized is None:
        limitations.append("utilized_lakhs not provided; utilization score = 0.")
    elif received > 0:
        util_pct = (utilized / received) * 100
        if util_pct >= 75:
            utilized_score = 2.0
        elif util_pct >= 50:
            utilized_score = 1.0
        else:
            utilized_score = 0.0

    score = received_score + utilized_score

    status = (
        RequirementStatus.PASS.value if score >= 3.5
        else RequirementStatus.WARNING.value if score >= 2.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=5.0,
        deterministic_metrics={
            "received_lakhs": received,
            "received_score": received_score,
            "utilized_lakhs": utilized,
            "utilized_score": utilized_score,
        },
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Legacy placeholder — preserved for backward compatibility
# ---------------------------------------------------------------------------

RULE_LAB_FACILITY = "criterion6.lab_facility_availability"


def evaluate_lab_facility(context: dict[str, Any]) -> EvaluationResult:
    """
    Legacy placeholder (criterion6.lab_facility_availability).
    Retained for backward compatibility.
    """
    required = context.get("labs_required")
    available = context.get("labs_available")

    if required is None or available is None:
        return _missing_data_warning(
            rule=RULE_LAB_FACILITY,
            missing=["labs_required", "labs_available"],
            max_score=20.0,
        )

    if required == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=20.0,
            deterministic_metrics={"labs_required": 0, "labs_available": 0},
            limitations=["No lab requirement specified."],
        )

    ratio = available / required
    pct = min(ratio * 100, 100)

    if pct >= 100:
        status = RequirementStatus.PASS.value
    elif pct >= 75:
        status = RequirementStatus.WARNING.value
    else:
        status = RequirementStatus.FAIL.value

    return EvaluationResult(
        status=status,
        score_attained=round((pct / 100) * 20, 2),
        max_score=20.0,
        deterministic_metrics={
            "labs_required": required,
            "labs_available": available,
            "availability_pct": round(pct, 2),
        },
        limitations=[
            "LEGACY RULE: Criterion 6 in NBA 2026 covers Faculty Contributions, not Facilities. "
            "This rule key is retained for backward compatibility only."
        ],
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CRITERION6_RULES: dict[str, Any] = {
    # Professional Development (6.1)
    RULE_MEMBERSHIPS: evaluate_professional_memberships,
    RULE_RESOURCE_PERSONS: evaluate_resource_persons,
    RULE_FDP_PARTICIPATION: evaluate_fdp_participation,
    RULE_MOOC_DEV: evaluate_mooc_development,
    RULE_MOOC_CERT: evaluate_mooc_certification,
    RULE_FDP_ORGANIZED: evaluate_fdp_organized,
    RULE_STUDENT_INNOVATION: evaluate_student_innovation,
    RULE_INDUSTRY_TRAINING: evaluate_industry_training,
    # Research and Development (6.2)
    RULE_RESEARCH_PUBS: evaluate_research_publications,
    RULE_PHD_STUDENTS: evaluate_phd_students,
    RULE_DEVELOPMENT: evaluate_development_activities,
    RULE_SPONSORED: evaluate_sponsored_research,
    RULE_CONSULTANCY: evaluate_consultancy_work,
    RULE_SEED_MONEY: evaluate_seed_money,
    # Legacy
    RULE_LAB_FACILITY: evaluate_lab_facility,
}
