"""
AI-NBA Readiness System — Backend
app/business_rules/criterion4_rules.py

Deterministic evaluation rules for NBA Criterion 4:
Students' Performance (120 marks total).

Sources:
  NBA Manual for UG Engineering Tier I — 2026 Edition
  Annexure VII, Criterion 4 (pp. 157-161)
  Working Rulebook: NBA_Criteria_3_4_5_6_Rulebook_2026_Manual_v2.docx

Boundary ambiguities:
  Where the manual leaves exact boundary behaviour (< vs <=) undefined,
  or double-counting policies unspecified, the rule returns
  NEEDS_RULE_CLARIFICATION instead of guessing.

Formula references:
  4.1  ER = (N1 + N4) / N averaged over CAY, CAYm1, CAYm2; max 20
  4.2  SR = B/A × 100; AvgSR = mean(SR over 3 batches); Points = 1.5 × (AvgSR/10)
       If A < N+N2 use N+N2 as denominator; max 15
  4.3-4.5  API = (MeanGPA or Mean%/10) × (Successful/Appeared); 10 marks each
  4.6  P = [(X+Y+Z)/FS]×100; Points = 0.3 × AvgP; if FS < N+N2 use N+N2; max 30
  4.7  Professional Activities (qualitative, reviewer-entered): max 25
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
# 4.1  Enrolment Ratio — 20 marks
# ---------------------------------------------------------------------------

RULE_ENROLMENT_RATIO = "criterion4.enrolment_ratio"


def evaluate_enrolment_ratio(context: dict[str, Any]) -> EvaluationResult:
    """
    4.1 Enrolment Ratio (ER) — 20 marks

    Expected context keys:
        years: list of dicts, each with:
            N1   int  — students admitted through regular entry
            N4   int  — students admitted in lateral/other entry (if any)
            N    int  — sanctioned intake

    Bands:
        AvgER >= 0.90 -> 20
        AvgER >= 0.80 -> 17
        AvgER >= 0.70 -> 14
        AvgER >= 0.60 -> 11
        AvgER >= 0.50 ->  8
        AvgER >= 0.40 ->  5
        else          ->  0
    """
    years: Optional[List[dict]] = context.get("years")

    if not years:
        return _missing_data_warning(
            rule=RULE_ENROLMENT_RATIO,
            missing=["years (list of {N1, N4, N} per year)"],
            max_score=20.0,
        )

    er_values = []
    limitations = []
    for i, yr in enumerate(years):
        n1 = yr.get("N1")
        n4 = yr.get("N4", 0)
        n = yr.get("N")
        if n1 is None or n is None:
            limitations.append(f"Year index {i}: N1 or N missing.")
            continue
        if n == 0:
            limitations.append(f"Year index {i}: N=0 (sanctioned intake zero), skipped.")
            continue
        er_values.append((n1 + n4) / n)

    if not er_values:
        return _missing_data_warning(
            rule=RULE_ENROLMENT_RATIO,
            missing=["valid year records with N>0"],
            max_score=20.0,
        )

    avg_er = sum(er_values) / len(er_values)

    if avg_er >= 0.90:
        score = 20.0
    elif avg_er >= 0.80:
        score = 17.0
    elif avg_er >= 0.70:
        score = 14.0
    elif avg_er >= 0.60:
        score = 11.0
    elif avg_er >= 0.50:
        score = 8.0
    elif avg_er >= 0.40:
        score = 5.0
    else:
        score = 0.0

    status = (
        RequirementStatus.PASS.value if score >= 14.0
        else RequirementStatus.WARNING.value if score >= 8.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=score,
        max_score=20.0,
        deterministic_metrics={
            "er_per_year": [round(e, 4) for e in er_values],
            "avg_er": round(avg_er, 4),
        },
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# 4.2  Success Rate — 15 marks
# ---------------------------------------------------------------------------

RULE_SUCCESS_RATE = "criterion4.success_rate"


def evaluate_success_rate(context: dict[str, Any]) -> EvaluationResult:
    """
    4.2 Success Rate without Backlogs — 15 marks

    Expected context keys:
        batches: list of dicts, each with:
            A   int  — students appeared
            B   int  — students passed without backlogs
            N   int  — sanctioned intake
            N2  int  — lateral entry intake

    SR_batch = B / max(A, N+N2) * 100
    AvgSR = mean(SR across batches)
    Points = min(1.5 * (AvgSR / 10), 15.0)
    """
    batches: Optional[List[dict]] = context.get("batches")

    if not batches:
        return _missing_data_warning(
            rule=RULE_SUCCESS_RATE,
            missing=["batches (list of {A, B, N, N2} per batch)"],
            max_score=15.0,
        )

    sr_values = []
    limitations = []
    for i, batch in enumerate(batches):
        a = batch.get("A")
        b = batch.get("B")
        n = batch.get("N", 0)
        n2 = batch.get("N2", 0)
        if a is None or b is None:
            limitations.append(f"Batch {i}: A or B missing.")
            continue
        denominator = max(a, n + n2)
        if denominator == 0:
            limitations.append(f"Batch {i}: denominator zero, skipped.")
            continue
        if a < (n + n2):
            limitations.append(
                f"Batch {i}: appeared={a} < N+N2={n+n2}; "
                "using N+N2 as denominator per manual note."
            )
        sr = (b / denominator) * 100
        sr_values.append(sr)

    if not sr_values:
        return _missing_data_warning(
            rule=RULE_SUCCESS_RATE,
            missing=["valid batch records"],
            max_score=15.0,
        )

    avg_sr = sum(sr_values) / len(sr_values)
    score = min(1.5 * (avg_sr / 10), 15.0)

    status = (
        RequirementStatus.PASS.value if score >= 10.5
        else RequirementStatus.WARNING.value if score >= 6.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=15.0,
        deterministic_metrics={
            "sr_per_batch": [round(s, 2) for s in sr_values],
            "avg_sr": round(avg_sr, 2),
            "formula": "Points = 1.5 * (AvgSR / 10), capped at 15",
        },
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# 4.3-4.5  Academic Performance Index — 10 marks each
# ---------------------------------------------------------------------------

RULE_FIRST_YEAR_API = "criterion4.first_year_api"
RULE_SECOND_YEAR_API = "criterion4.second_year_api"
RULE_THIRD_YEAR_API = "criterion4.third_year_api"


def _evaluate_api(context: dict[str, Any], rule: str, max_score: float = 10.0) -> EvaluationResult:
    """
    Academic Performance Index for a given year.

    Expected context keys:
        mean_gpa         float  — mean GPA (use if available)
        mean_percentage  float  — mean % (use if GPA unavailable; API = mean%/10)
        successful       int    — students who passed
        appeared         int    — students who appeared
    """
    mean_gpa = context.get("mean_gpa")
    mean_pct = context.get("mean_percentage")
    successful = context.get("successful")
    appeared = context.get("appeared")

    missing = []
    if mean_gpa is None and mean_pct is None:
        missing.append("mean_gpa or mean_percentage")
    if successful is None:
        missing.append("successful")
    if appeared is None:
        missing.append("appeared")

    if missing:
        return _missing_data_warning(rule=rule, missing=missing, max_score=max_score)

    if appeared == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=max_score,
            deterministic_metrics={"appeared": 0},
            limitations=["No students appeared; API not calculable."],
        )

    gpa_term = mean_gpa if mean_gpa is not None else (mean_pct / 10.0)
    gpa_term = max(0.0, min(10.0, gpa_term))

    api = gpa_term * (successful / appeared)
    score = min(api * max_score / 10.0, max_score)

    status = (
        RequirementStatus.PASS.value if score >= 0.7 * max_score
        else RequirementStatus.WARNING.value if score >= 0.4 * max_score
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=max_score,
        deterministic_metrics={
            "gpa_term_used": round(gpa_term, 4),
            "successful": successful,
            "appeared": appeared,
            "api": round(api, 4),
            "formula": "API = gpa_term * (successful/appeared); score = API * max/10",
        },
        limitations=[],
    )


def evaluate_first_year_api(context: dict[str, Any]) -> EvaluationResult:
    return _evaluate_api(context, RULE_FIRST_YEAR_API)


def evaluate_second_year_api(context: dict[str, Any]) -> EvaluationResult:
    return _evaluate_api(context, RULE_SECOND_YEAR_API)


def evaluate_third_year_api(context: dict[str, Any]) -> EvaluationResult:
    return _evaluate_api(context, RULE_THIRD_YEAR_API)


# ---------------------------------------------------------------------------
# 4.6  Placement and Higher Studies — 30 marks
# ---------------------------------------------------------------------------

RULE_PLACEMENT = "criterion4.placement_higher_studies"


def evaluate_placement(context: dict[str, Any]) -> EvaluationResult:
    """
    4.6 Placement, Higher Studies, and Entrepreneurship — 30 marks

    Expected context keys:
        years: list of dicts, each with:
            X    int  — students placed
            Y    int  — students in higher studies
            Z    int  — students as entrepreneurs
            FS   int  — final-semester students
            N    int  — sanctioned intake
            N2   int  — lateral entry intake
        overlap_policy_configured: bool  — True if institution has defined
            double-counting policy for students in multiple categories
    """
    overlap_configured = context.get("overlap_policy_configured", False)
    if not overlap_configured:
        return _needs_clarification(
            rule=RULE_PLACEMENT,
            reason=(
                "The NBA manual does not specify whether a student counted "
                "in placement (X), higher studies (Y), AND entrepreneurship (Z) "
                "simultaneously should be counted once or multiple times. "
                "Configure the institution's double-counting policy before scoring."
            ),
            max_score=30.0,
        )

    years: Optional[List[dict]] = context.get("years")
    if not years:
        return _missing_data_warning(
            rule=RULE_PLACEMENT,
            missing=["years (list of {X, Y, Z, FS, N, N2} per year)"],
            max_score=30.0,
        )

    p_values = []
    limitations = []
    for i, yr in enumerate(years):
        x = yr.get("X", 0)
        y = yr.get("Y", 0)
        z = yr.get("Z", 0)
        fs = yr.get("FS")
        n = yr.get("N", 0)
        n2 = yr.get("N2", 0)
        if fs is None:
            limitations.append(f"Year {i}: FS missing.")
            continue
        denominator = max(fs, n + n2)
        if denominator == 0:
            limitations.append(f"Year {i}: denominator zero, skipped.")
            continue
        if fs < (n + n2):
            limitations.append(f"Year {i}: FS={fs} < N+N2={n+n2}; using N+N2.")
        p = ((x + y + z) / denominator) * 100
        p_values.append(p)

    if not p_values:
        return _missing_data_warning(
            rule=RULE_PLACEMENT,
            missing=["valid year records"],
            max_score=30.0,
        )

    avg_p = sum(p_values) / len(p_values)
    score = min(0.3 * avg_p, 30.0)

    status = (
        RequirementStatus.PASS.value if score >= 21.0
        else RequirementStatus.WARNING.value if score >= 12.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=30.0,
        deterministic_metrics={
            "p_per_year": [round(p, 2) for p in p_values],
            "avg_p": round(avg_p, 2),
            "formula": "Points = 0.3 * AvgP, capped at 30",
        },
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# 4.7  Professional Activities (qualitative, reviewer-entered) — 25 marks
# ---------------------------------------------------------------------------

RULE_PROFESSIONAL_ACTIVITIES = "criterion4.professional_activities"


def evaluate_professional_activities(context: dict[str, Any]) -> EvaluationResult:
    """
    4.7 Professional Activities — 25 marks (qualitative rubric, reviewer-entered)
    """
    reviewer_score = context.get("reviewer_score")
    if reviewer_score is None:
        return _missing_data_warning(
            rule=RULE_PROFESSIONAL_ACTIVITIES,
            missing=["reviewer_score (qualitative rubric, must be entered by NBA reviewer)"],
            max_score=25.0,
        )

    score = max(0.0, min(float(reviewer_score), 25.0))
    status = (
        RequirementStatus.PASS.value if score >= 17.5
        else RequirementStatus.WARNING.value if score >= 10.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=25.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Score is qualitative and was entered by the NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# Legacy placeholder — preserved for backward compatibility
# ---------------------------------------------------------------------------

RULE_PASS_PERCENTAGE = "criterion4.pass_percentage"


def evaluate_pass_percentage(context: dict[str, Any]) -> EvaluationResult:
    """
    Legacy placeholder rule (criterion4.pass_percentage).
    Retained for backward compatibility with existing test seeds.
    """
    registered = context.get("registered_students")
    passed = context.get("passed_students")

    if registered is None or passed is None:
        return _missing_data_warning(
            rule=RULE_PASS_PERCENTAGE,
            missing=["registered_students", "passed_students"],
            max_score=20.0,
        )

    if registered == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=20.0,
            deterministic_metrics={"registered_students": 0, "passed_students": 0},
            limitations=["No registered students found."],
        )

    pass_pct = (passed / registered) * 100

    if pass_pct >= 80:
        status = RequirementStatus.PASS.value
    elif pass_pct >= 60:
        status = RequirementStatus.WARNING.value
    else:
        status = RequirementStatus.FAIL.value

    return EvaluationResult(
        status=status,
        score_attained=round((pass_pct / 100) * 20, 2),
        max_score=20.0,
        deterministic_metrics={
            "registered_students": registered,
            "passed_students": passed,
            "pass_percentage": round(pass_pct, 2),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CRITERION4_RULES: dict[str, Any] = {
    RULE_ENROLMENT_RATIO: evaluate_enrolment_ratio,
    RULE_SUCCESS_RATE: evaluate_success_rate,
    RULE_FIRST_YEAR_API: evaluate_first_year_api,
    RULE_SECOND_YEAR_API: evaluate_second_year_api,
    RULE_THIRD_YEAR_API: evaluate_third_year_api,
    RULE_PLACEMENT: evaluate_placement,
    RULE_PROFESSIONAL_ACTIVITIES: evaluate_professional_activities,
    # Legacy
    RULE_PASS_PERCENTAGE: evaluate_pass_percentage,
}
