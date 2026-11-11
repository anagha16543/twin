"""
AI-NBA Readiness System — Backend
app/business_rules/criterion5_rules.py

Deterministic evaluation rules for NBA Criterion 5:
Faculty Information (100 marks total).

Sources:
  NBA Manual for UG Engineering Tier I — 2026 Edition
  Annexure VII, Criterion 5 (pp. 161-164)
  Working Rulebook: NBA_Criteria_3_4_5_6_Rulebook_2026_Manual_v2.docx

Boundary ambiguities:
  The manual uses strict inequalities for SFR bands (<15, <17, etc.) but
  does not specify the outcome when SFR falls exactly on a boundary value.
  Exact boundary values return NEEDS_RULE_CLARIFICATION.

Formula references:
  5.1  SFR = S / TF averaged over 3 years; bands determine 0-30 marks
  5.2  FQI = 2.5 × [(10X + 4Y) / RF]; RF = S/20; cap 25
  5.3  Marks = [AF1/RF1 + 0.6×(AF2/RF2) + 0.4×(AF3/RF3)] × 12.5; cap 25
       RF1 = RF/9; RF2 = 2×RF/9; RF3 = 6×RF/9
  5.4  Provision (1 mark) + >=50 hrs/yr -> 3 marks/yr (max 3 yrs = 9 marks); total cap 10
  5.5  FR = [(A×0 + B×1 + C×2 + D×3 + E×4) / RF] × 2.50; cap 10; RF = DS/20
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.business_rules.readiness_rules import (
    EvaluationResult,
    RequirementStatus,
    _missing_data_warning,
    _needs_clarification,
)

# Boundary values for SFR bands where the manual is silent on exact equality
_SFR_BOUNDARIES = {15.0, 17.0, 19.0, 21.0, 23.0, 25.0}


# ---------------------------------------------------------------------------
# 5.1  Student-Faculty Ratio — 30 marks
# ---------------------------------------------------------------------------

RULE_SFR = "criterion5.student_faculty_ratio"


def evaluate_sfr(context: dict[str, Any]) -> EvaluationResult:
    """
    5.1 Student-Faculty Ratio (SFR) — 30 marks

    Expected context keys:
        years: list of dicts, each with:
            S   int  — total enrolled students
            TF  int  — total regular faculty

    Bands (manual p.161):
        SFR < 15  -> 30
        SFR < 17  -> 27
        SFR < 19  -> 24
        SFR < 21  -> 21
        SFR < 23  -> 18
        SFR < 25  -> 15
        SFR > 25  ->  0
        SFR == boundary -> NEEDS_RULE_CLARIFICATION
    """
    years: Optional[List[dict]] = context.get("years")
    if not years:
        return _missing_data_warning(
            rule=RULE_SFR,
            missing=["years (list of {S, TF} per year)"],
            max_score=30.0,
        )

    sfr_values = []
    limitations = []
    for i, yr in enumerate(years):
        s = yr.get("S")
        tf = yr.get("TF")
        if s is None or tf is None:
            limitations.append(f"Year {i}: S or TF missing.")
            continue
        if tf == 0:
            limitations.append(f"Year {i}: TF=0 (no faculty), skipped.")
            continue
        sfr_values.append(s / tf)

    if not sfr_values:
        return _missing_data_warning(
            rule=RULE_SFR,
            missing=["valid year records with TF>0"],
            max_score=30.0,
        )

    avg_sfr = sum(sfr_values) / len(sfr_values)

    # Check for exact boundary
    for boundary in _SFR_BOUNDARIES:
        if abs(avg_sfr - boundary) < 1e-9:
            return _needs_clarification(
                rule=RULE_SFR,
                reason=(
                    f"AvgSFR = {avg_sfr:.4f} falls exactly on the boundary value {boundary}. "
                    "The NBA manual uses strict inequalities (<) and does not specify "
                    "whether boundary values belong to the upper or lower band."
                ),
                max_score=30.0,
                metrics={"avg_sfr": avg_sfr, "sfr_per_year": sfr_values},
            )

    if avg_sfr < 15:
        score = 30.0
    elif avg_sfr < 17:
        score = 27.0
    elif avg_sfr < 19:
        score = 24.0
    elif avg_sfr < 21:
        score = 21.0
    elif avg_sfr < 23:
        score = 18.0
    elif avg_sfr < 25:
        score = 15.0
    else:
        score = 0.0

    status = (
        RequirementStatus.PASS.value if score >= 21.0
        else RequirementStatus.WARNING.value if score >= 15.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=score,
        max_score=30.0,
        deterministic_metrics={
            "sfr_per_year": [round(s, 4) for s in sfr_values],
            "avg_sfr": round(avg_sfr, 4),
        },
        limitations=limitations,
    )


# ---------------------------------------------------------------------------
# 5.2  Faculty Qualification Index — 25 marks
# ---------------------------------------------------------------------------

RULE_FQI = "criterion5.faculty_qualification_index"


def evaluate_fqi(context: dict[str, Any]) -> EvaluationResult:
    """
    5.2 Faculty Qualification Index (FQI) — 25 marks

    Expected context keys:
        X   int    — faculty with PhD
        Y   int    — faculty with MTech/ME (without PhD)
        S   int    — total enrolled students (to calculate RF = S/20)
        RF  float  — required faculty (optional; if provided, used directly)

    RF = S / 20 (if RF not provided)
    FQI = 2.5 × [(10X + 4Y) / RF]
    Score = min(FQI, 25.0)
    """
    x = context.get("X")
    y = context.get("Y", 0)
    rf = context.get("RF")
    s = context.get("S")

    missing = []
    if x is None:
        missing.append("X (faculty with PhD)")
    if rf is None and s is None:
        missing.append("RF or S (to compute required faculty)")

    if missing:
        return _missing_data_warning(rule=RULE_FQI, missing=missing, max_score=25.0)

    if rf is None:
        rf = s / 20.0

    if rf <= 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=25.0,
            deterministic_metrics={"RF": rf},
            limitations=["Required faculty RF <= 0; FQI not calculable."],
        )

    fqi = 2.5 * ((10 * x + 4 * y) / rf)
    score = min(fqi, 25.0)

    status = (
        RequirementStatus.PASS.value if score >= 17.5
        else RequirementStatus.WARNING.value if score >= 10.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=25.0,
        deterministic_metrics={
            "X_phd": x,
            "Y_mtech": y,
            "RF": round(rf, 2),
            "FQI": round(fqi, 4),
            "formula": "FQI = 2.5 * (10X + 4Y) / RF, capped at 25",
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 5.3  Faculty Cadre Proportion — 25 marks
# ---------------------------------------------------------------------------

RULE_CADRE = "criterion5.faculty_cadre_proportion"


def evaluate_faculty_cadre(context: dict[str, Any]) -> EvaluationResult:
    """
    5.3 Faculty Cadre Proportion — 25 marks

    Expected context keys:
        AF1  int    — actual Professors
        AF2  int    — actual Associate Professors
        AF3  int    — actual Assistant Professors
        RF   float  — required total faculty (optional; derive from S if not given)
        S    int    — total enrolled students (used if RF not given)
    """
    af1 = context.get("AF1", 0)
    af2 = context.get("AF2", 0)
    af3 = context.get("AF3", 0)
    rf = context.get("RF")
    s = context.get("S")

    if rf is None and s is None:
        return _missing_data_warning(
            rule=RULE_CADRE,
            missing=["RF or S"],
            max_score=25.0,
        )

    if rf is None:
        rf = s / 20.0

    if rf <= 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=25.0,
            deterministic_metrics={"RF": rf},
            limitations=["Required faculty RF <= 0; cadre ratio not calculable."],
        )

    if af1 == 0 and af2 == 0:
        return EvaluationResult(
            status=RequirementStatus.FAIL.value,
            score_attained=0.0,
            max_score=25.0,
            deterministic_metrics={"AF1": af1, "AF2": af2, "AF3": af3, "RF": round(rf, 2)},
            limitations=["AF1 (Professors) and AF2 (Associate Professors) are both zero."],
        )

    rf1 = rf / 9.0
    rf2 = 2.0 * rf / 9.0
    rf3 = 6.0 * rf / 9.0

    term1 = af1 / rf1 if rf1 > 0 else 0.0
    term2 = 0.6 * (af2 / rf2) if rf2 > 0 else 0.0
    term3 = 0.4 * (af3 / rf3) if rf3 > 0 else 0.0

    score_raw = (term1 + term2 + term3) * 12.5
    score = min(score_raw, 25.0)

    status = (
        RequirementStatus.PASS.value if score >= 17.5
        else RequirementStatus.WARNING.value if score >= 10.0
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=25.0,
        deterministic_metrics={
            "AF1": af1, "AF2": af2, "AF3": af3,
            "RF": round(rf, 2),
            "RF1": round(rf1, 2), "RF2": round(rf2, 2), "RF3": round(rf3, 2),
            "score_raw": round(score_raw, 4),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 5.4  Visiting/Adjunct/Emeritus Faculty — 10 marks
# ---------------------------------------------------------------------------

RULE_VISITING = "criterion5.visiting_faculty"


def evaluate_visiting_faculty(context: dict[str, Any]) -> EvaluationResult:
    """
    5.4 Visiting/Adjunct/Emeritus Faculty — 10 marks

    Expected context keys:
        provision_exists  bool           — True if institutional provision exists (1 mark)
        yearly_hours      list[float]    — hours per year (up to 3 years)
    """
    provision = context.get("provision_exists", False)
    yearly_hours: List[float] = context.get("yearly_hours", [])

    if not provision and not yearly_hours:
        return _missing_data_warning(
            rule=RULE_VISITING,
            missing=["provision_exists", "yearly_hours"],
            max_score=10.0,
        )

    score = 1.0 if provision else 0.0
    hours_detail = []
    for i, hours in enumerate(yearly_hours[:3]):
        if hours >= 50:
            score += 3.0
            hours_detail.append(f"Year {i+1}: {hours} hrs (>=50 -> +3 marks)")
        else:
            hours_detail.append(f"Year {i+1}: {hours} hrs (<50 -> 0 marks)")

    score = min(score, 10.0)
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
            "provision_mark": 1.0 if provision else 0.0,
            "hours_detail": hours_detail,
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 5.5  Faculty Retention — 10 marks
# ---------------------------------------------------------------------------

RULE_RETENTION = "criterion5.faculty_retention"


def evaluate_faculty_retention(context: dict[str, Any]) -> EvaluationResult:
    """
    5.5 Faculty Retention — 10 marks

    Per manual formula:
    FR = [(A×0 + B×1 + C×2 + D×3 + E×4) / RF] × 2.50; points limited to 10
    """
    a = context.get("A", 0)
    b = context.get("B", 0)
    c = context.get("C", 0)
    d = context.get("D", 0)
    e = context.get("E", 0)
    rf = context.get("RF")
    ds = context.get("DS")
    s = context.get("S")
    boundary_resolved = context.get("boundary_resolved", False)

    if rf is None:
        if ds is not None:
            rf = ds / 20.0
        elif s is not None:
            rf = s / 20.0
        else:
            return _missing_data_warning(
                rule=RULE_RETENTION,
                missing=["RF or DS or S"],
                max_score=10.0,
            )

    # Check boundary ambiguity
    if not boundary_resolved and (b > 0 or c > 0 or d > 0):
        return _needs_clarification(
            rule=RULE_RETENTION,
            reason=(
                "Faculty retention counts at exactly 1, 2, or 3 year boundaries "
                "(B, C, D > 0) are present but the NBA manual does not specify "
                "whether these belong to the lower or upper retention band. "
                "Set boundary_resolved=True and clarify the institutional interpretation."
            ),
            max_score=10.0,
            metrics={"A": a, "B": b, "C": c, "D": d, "E": e, "RF": rf},
        )

    if rf <= 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={"RF": rf},
            limitations=["RF <= 0; retention formula not calculable."],
        )

    numerator = a * 0 + b * 1 + c * 2 + d * 3 + e * 4
    fr = (numerator / rf) * 2.50
    score = min(fr, 10.0)

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
            "A": a, "B": b, "C": c, "D": d, "E": e,
            "RF": round(rf, 2),
            "FR": round(fr, 4),
            "formula": "FR = [(A*0+B*1+C*2+D*3+E*4)/RF]*2.50, cap 10",
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# Legacy placeholder — preserved for backward compatibility
# ---------------------------------------------------------------------------

RULE_FACULTY_QUALIFICATION = "criterion5.faculty_qualification_ratio"


def evaluate_faculty_qualification(context: dict[str, Any]) -> EvaluationResult:
    """Legacy placeholder retained for backward compatibility."""
    total = context.get("total_faculty")
    qualified = context.get("faculty_with_pg_or_phd")

    if total is None or qualified is None:
        return _missing_data_warning(
            rule=RULE_FACULTY_QUALIFICATION,
            missing=["total_faculty", "faculty_with_pg_or_phd"],
            max_score=20.0,
        )

    if total == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=20.0,
            deterministic_metrics={"total_faculty": 0, "faculty_with_pg_or_phd": 0},
            limitations=["No faculty records found for this department."],
        )

    ratio_pct = (qualified / total) * 100
    if ratio_pct >= 80:
        status = RequirementStatus.PASS.value
    elif ratio_pct >= 60:
        status = RequirementStatus.WARNING.value
    else:
        status = RequirementStatus.FAIL.value

    return EvaluationResult(
        status=status,
        score_attained=round((ratio_pct / 100) * 20, 2),
        max_score=20.0,
        deterministic_metrics={
            "total_faculty": total,
            "faculty_with_pg_or_phd": qualified,
            "qualification_ratio_pct": round(ratio_pct, 2),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CRITERION5_RULES: dict[str, Any] = {
    RULE_SFR: evaluate_sfr,
    RULE_FQI: evaluate_fqi,
    RULE_CADRE: evaluate_faculty_cadre,
    RULE_VISITING: evaluate_visiting_faculty,
    RULE_RETENTION: evaluate_faculty_retention,
    # Legacy
    RULE_FACULTY_QUALIFICATION: evaluate_faculty_qualification,
}
