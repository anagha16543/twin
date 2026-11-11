"""
AI-NBA Readiness System — Backend
app/business_rules/criterion3_rules.py

Deterministic evaluation rules for NBA Criterion 3:
Course Outcomes & Program Outcomes (CO-PO Attainment).
Total: 120 marks.

Sources:
  NBA Manual for UG Engineering Tier I — 2026 Edition
  Annexure VII, Criterion 3 (pp. 155-157)
  Working Rulebook: NBA_Criteria_3_4_5_6_Rulebook_2026_Manual_v2.docx

Rule contract:
  Every rule function receives a `context` dict containing structured data
  fetched from the backend database, and returns an EvaluationResult named-tuple:

    EvaluationResult(
        status:             RequirementStatus value string
        score_attained:     float
        max_score:          float
        deterministic_metrics: dict
        limitations:        list[str]
    )

Numerical calculations are performed entirely in Python.
The LLM must not be consulted for numerical results or compliance decisions.
"""

from __future__ import annotations

from typing import Any

from app.business_rules.readiness_rules import (
    EvaluationResult,
    RequirementStatus,
    _missing_data_warning,
    _needs_clarification,
)


# ---------------------------------------------------------------------------
# 3.1  Continuous Assessment / CO Definition Completeness (10 marks)
# ---------------------------------------------------------------------------

RULE_CO_COMPLETENESS = "criterion3.co_definition_completeness"
RULE_CONTINUOUS_ASSESSMENT = "criterion3.continuous_assessment"


def evaluate_co_completeness(context: dict[str, Any]) -> EvaluationResult:
    """
    Check that all subjects in the academic year have at least one CO defined.

    Expected context keys:
        total_subjects      int — total subjects in the year/department
        subjects_with_cos   int — subjects that have >= 1 CO defined
    """
    total = context.get("total_subjects")
    with_cos = context.get("subjects_with_cos")

    if total is None or with_cos is None:
        return _missing_data_warning(
            rule=RULE_CO_COMPLETENESS,
            missing=["total_subjects", "subjects_with_cos"],
            max_score=10.0,
        )

    if total == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={"total_subjects": total, "subjects_with_cos": with_cos},
            limitations=["No subjects found for this academic year."],
        )

    coverage_pct = (with_cos / total) * 100

    if coverage_pct >= 100:
        status = RequirementStatus.PASS.value
    elif coverage_pct >= 80:
        status = RequirementStatus.WARNING.value
    else:
        status = RequirementStatus.FAIL.value

    return EvaluationResult(
        status=status,
        score_attained=round((coverage_pct / 100) * 10, 2),
        max_score=10.0,
        deterministic_metrics={
            "total_subjects": total,
            "subjects_with_cos": with_cos,
            "co_coverage_pct": round(coverage_pct, 2),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 3.2  CO-PO Mapping Completeness (10 marks)
# ---------------------------------------------------------------------------

RULE_COPO_MAPPING = "criterion3.copo_mapping_completeness"


def evaluate_copo_mapping(context: dict[str, Any]) -> EvaluationResult:
    """
    Check that every Course Outcome is mapped to at least one Program Outcome.

    Expected context keys:
        total_cos       int
        cos_with_po_map int
    """
    total_cos = context.get("total_cos")
    mapped = context.get("cos_with_po_map")

    if total_cos is None or mapped is None:
        return _missing_data_warning(
            rule=RULE_COPO_MAPPING,
            missing=["total_cos", "cos_with_po_map"],
            max_score=10.0,
        )

    if total_cos == 0:
        return EvaluationResult(
            status=RequirementStatus.NOT_APPLICABLE.value,
            score_attained=0.0,
            max_score=10.0,
            deterministic_metrics={"total_cos": total_cos, "cos_with_po_map": mapped},
            limitations=["No COs found."],
        )

    pct = (mapped / total_cos) * 100
    status = (
        RequirementStatus.PASS.value if pct >= 100
        else RequirementStatus.WARNING.value if pct >= 80
        else RequirementStatus.FAIL.value
    )

    return EvaluationResult(
        status=status,
        score_attained=round((pct / 100) * 10, 2),
        max_score=10.0,
        deterministic_metrics={
            "total_cos": total_cos,
            "cos_with_po_map": mapped,
            "mapping_coverage_pct": round(pct, 2),
        },
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 3.3  SEE Question Paper Quality (10 marks)
# ---------------------------------------------------------------------------

RULE_SEE_QUESTION_PAPER = "criterion3.see_question_paper"


def evaluate_see_question_paper(context: dict[str, Any]) -> EvaluationResult:
    """
    3.3 Quality of Semester End Examination Question Papers (10 marks).
    Qualitative rubric / reviewer-evaluated.
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_SEE_QUESTION_PAPER,
            missing=["reviewer_score"],
            max_score=10.0,
        )
    score = max(0.0, min(float(score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# 3.4  Lab and Workshop Conduct (10 marks)
# ---------------------------------------------------------------------------

RULE_LAB_WORKSHOP = "criterion3.lab_workshop"


def evaluate_lab_workshop(context: dict[str, Any]) -> EvaluationResult:
    """
    3.4 Lab and Workshop Conduct (10 marks).
    Qualitative rubric / reviewer-evaluated.
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_LAB_WORKSHOP,
            missing=["reviewer_score"],
            max_score=10.0,
        )
    score = max(0.0, min(float(score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# 3.4  Industrial Training / Internship (10 marks)
# ---------------------------------------------------------------------------

RULE_INDUSTRIAL_TRAINING = "criterion3.industrial_training"


def evaluate_industrial_training(context: dict[str, Any]) -> EvaluationResult:
    """
    3.4 Evaluation of Industrial Training or Internship Programs (10 marks).
    Qualitative rubric / reviewer-evaluated.
    Manual Annexure VII, p. 156: 10 marks max.
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_INDUSTRIAL_TRAINING,
            missing=["reviewer_score"],
            max_score=10.0,
        )
    score = max(0.0, min(float(score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# 3.5  Project Evaluation (20 marks)
# ---------------------------------------------------------------------------

RULE_PROJECT_EVALUATION = "criterion3.project_evaluation"


def evaluate_project_evaluation(context: dict[str, Any]) -> EvaluationResult:
    """
    3.5 Evaluation of Projects (20 marks).
    Qualitative rubric / reviewer-evaluated.
    Manual Annexure VII, p. 156: 20 marks max.
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_PROJECT_EVALUATION,
            missing=["reviewer_score"],
            max_score=20.0,
        )
    score = max(0.0, min(float(score), 20.0))
    status = (
        RequirementStatus.PASS.value if score >= 14.0
        else RequirementStatus.WARNING.value if score >= 8.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=20.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# 3.6  Sustainable Development Goals (SDG) (10 marks)
# ---------------------------------------------------------------------------

RULE_SDG = "criterion3.sdg_evidence"


def evaluate_sdg_evidence(context: dict[str, Any]) -> EvaluationResult:
    """
    3.6 Evidence of Addressing Sustainable Development Goals (SDG) (10 marks).
    Qualitative rubric / reviewer-evaluated.
    Manual Annexure VII, p. 156: 10 marks max.
    """
    score = context.get("reviewer_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_SDG,
            missing=["reviewer_score"],
            max_score=10.0,
        )
    score = max(0.0, min(float(score), 10.0))
    status = (
        RequirementStatus.PASS.value if score >= 7.0
        else RequirementStatus.WARNING.value if score >= 4.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=10.0,
        deterministic_metrics={"reviewer_score": score},
        limitations=["Qualitative rubric; score entered by NBA reviewer."],
    )


# ---------------------------------------------------------------------------
# 3.7  CO Attainment (25 marks)
# ---------------------------------------------------------------------------

RULE_CO_ATTAINMENT = "criterion3.co_attainment_tools"


def evaluate_co_attainment(context: dict[str, Any]) -> EvaluationResult:
    """
    3.7 Course Outcome Attainment (25 marks).

    NBA Tier-I requires institution-specific direct and indirect assessment
    processes. If attainment_formula_configured is False, returns
    NEEDS_RULE_CLARIFICATION.
    """
    configured = context.get("attainment_formula_configured", False)
    if not configured:
        return _needs_clarification(
            rule=RULE_CO_ATTAINMENT,
            reason=(
                "NBA Tier-I requires each institution to configure and approve "
                "its specific direct and indirect CO attainment calculation methodology. "
                "Set attainment_formula_configured=True with verified institutional thresholds."
            ),
            max_score=25.0,
        )

    score = context.get("attainment_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_CO_ATTAINMENT,
            missing=["attainment_score"],
            max_score=25.0,
        )
    score = max(0.0, min(float(score), 25.0))
    status = (
        RequirementStatus.PASS.value if score >= 17.5
        else RequirementStatus.WARNING.value if score >= 10.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=25.0,
        deterministic_metrics={"attainment_score": score},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# 3.8  PO and PSO Attainment (25 marks)
# ---------------------------------------------------------------------------

RULE_PO_PSO_ATTAINMENT = "criterion3.po_pso_attainment"


def evaluate_po_pso_attainment(context: dict[str, Any]) -> EvaluationResult:
    """
    3.8 Program Outcomes and PSO Attainment (25 marks).

    NBA Tier-I requires institution-specific PO/PSO attainment calculation methodology.
    If attainment_formula_configured is False, returns NEEDS_RULE_CLARIFICATION.
    """
    configured = context.get("attainment_formula_configured", False)
    if not configured:
        return _needs_clarification(
            rule=RULE_PO_PSO_ATTAINMENT,
            reason=(
                "NBA Tier-I requires institutionally configured and approved "
                "PO/PSO attainment targets and assessment formulas. "
                "Set attainment_formula_configured=True with institutional benchmarks."
            ),
            max_score=25.0,
        )

    score = context.get("attainment_score")
    if score is None:
        return _missing_data_warning(
            rule=RULE_PO_PSO_ATTAINMENT,
            missing=["attainment_score"],
            max_score=25.0,
        )
    score = max(0.0, min(float(score), 25.0))
    status = (
        RequirementStatus.PASS.value if score >= 17.5
        else RequirementStatus.WARNING.value if score >= 10.0
        else RequirementStatus.FAIL.value
    )
    return EvaluationResult(
        status=status,
        score_attained=round(score, 2),
        max_score=25.0,
        deterministic_metrics={"attainment_score": score},
        limitations=[],
    )


# ---------------------------------------------------------------------------
# Rubric evaluation — NBA Tier-I 2026 Manual, Annexure VII (Criterion 3)
# ---------------------------------------------------------------------------
#
# Each sub-criterion is split exactly as the manual's evaluation guidelines.
# Component kinds:
#   "reviewer" : scored by the HOD/IQAC reviewer from evidence (0..max)
#   "computed" : derived by the backend from uploaded marks / curriculum data
#                (criterion3_service). Never accepted from the browser in the
#                Criterion 3 run endpoint.
#
# Status thresholds (internal readiness indicator, not an official NBA grade):
#   PASS    >= 70% of the sub-criterion maximum
#   WARNING >= 40%
#   FAIL    <  40%

C3_RUBRIC: dict[str, dict[str, Any]] = {
    "3.1": {
        "title": "Evaluation of Continuous Assessment",
        "max": 10.0,
        "components": [
            {"key": "A", "max": 2.0, "kind": "reviewer",
             "label": "Process for setting and evaluation of internal question papers",
             "exhibit": "Process for setting internal question papers, model answers, evaluation and compliance."},
            {"key": "B", "max": 3.0, "kind": "reviewer",
             "label": "Quality of questions, appropriateness of mapping with the COs",
             "exhibit": "Quality of unit tests / class tests / mid-term tests / assignments."},
            {"key": "C", "max": 3.0, "kind": "computed",
             "label": "Assessment of CO coverage in unit tests / mid-terms / assignments",
             "exhibit": "Documentary evidence of mapping questions with COs.",
             "formula": "3 x (COs assessed by at least one CIE component / total COs of courses with marks uploaded)"},
            {"key": "D", "max": 2.0, "kind": "reviewer",
             "label": "Sharing of post-evaluation feedback with students",
             "exhibit": "Evidence of sharing post-evaluation feedback for performance improvement."},
        ],
    },
    "3.2": {
        "title": "Evaluation of the Semester End Exam (SEE) Question Paper",
        "max": 10.0,
        "components": [
            {"key": "A", "max": 3.0, "kind": "reviewer",
             "label": "Process for setting and evaluation of the SEE question paper",
             "exhibit": "Process for setting the SEE paper, evaluation and compliance."},
            {"key": "B", "max": 5.0, "kind": "reviewer",
             "label": "Quality of questions, appropriateness of mapping with the COs",
             "exhibit": "Assessment of the quality of the SEE question paper."},
            {"key": "C", "max": 2.0, "kind": "reviewer",
             "label": "Transparency of post-evaluation process",
             "exhibit": "Evidence of transparency of the post-evaluation process."},
        ],
    },
    "3.3": {
        "title": "Evaluation of Laboratory Work and Workshop",
        "max": 10.0,
        "components": [
            {"key": "A", "max": 5.0, "kind": "reviewer",
             "label": "Evaluation of experiments conducted in workshops / laboratories",
             "exhibit": "Evidence of evaluation of the laboratory experiments."},
            {"key": "B", "max": 5.0, "kind": "reviewer",
             "label": "Use of rubrics for assessing student performance with relevance to COs/POs",
             "exhibit": "Rubrics developed and used during workshops / laboratories."},
        ],
    },
    "3.4": {
        "title": "Evaluation of Industrial Training / Internship",
        "max": 10.0,
        "components": [
            {"key": "A", "max": 4.0, "kind": "reviewer",
             "label": "Relevance of internships / industrial training",
             "exhibit": "Documentary evidence of internships and their relevance in terms of POs."},
            {"key": "B", "max": 6.0, "kind": "reviewer",
             "label": "Rubrics for assessing internships and mapping with POs",
             "exhibit": "Rubrics developed and used during internships / industrial training."},
        ],
    },
    "3.5": {
        "title": "Evaluation of Projects",
        "max": 20.0,
        "components": [
            {"key": "A", "max": 10.0, "kind": "reviewer",
             "label": "Rubrics for complexity, cost, relevance to environment and sustainability",
             "exhibit": "Rubrics assessing complexity, cost, environment and sustainability."},
            {"key": "B", "max": 10.0, "kind": "reviewer",
             "label": "Rubrics for team work, communication and project management",
             "exhibit": "Rubrics assessing individual and team performance."},
        ],
    },
    "3.6": {
        "title": "Evidence of Addressing Sustainable Development Goals (SDG)",
        "max": 10.0,
        "components": [
            {"key": "A", "max": 10.0, "kind": "reviewer",
             "label": "Evidence of addressing SDGs relevant to the program",
             "exhibit": "Student project activities through course work, research work and projects."},
        ],
    },
    "3.7": {
        "title": "Attainment of Course Outcomes",
        "max": 25.0,
        "requires_attainment_config": True,
        "components": [
            {"key": "A", "max": 2.0, "kind": "reviewer",
             "label": "3.7.1 A - List of assessment tools and processes",
             "exhibit": "Documentary evidence for assessment tools and processes used to measure COs."},
            {"key": "B", "max": 3.0, "kind": "reviewer",
             "label": "3.7.1 B - Quality / relevance of assessment tools and processes",
             "exhibit": "Data collection, verification, analysis and decision-making evidence."},
            {"key": "C", "max": 20.0, "kind": "computed",
             "label": "3.7.2 - Attainment of COs of all courses w.r.t. set attainment levels",
             "exhibit": "Methodology to define set levels and its compliance.",
             "formula": "20 x (COs whose final attainment level >= CO target level / total COs assessed)"},
        ],
    },
    "3.8": {
        "title": "Attainment of Program Outcomes and Program Specific Outcomes",
        "max": 25.0,
        "requires_attainment_config": True,
        "components": [
            {"key": "A", "max": 10.0, "kind": "reviewer",
             "label": "Verification of documents, results and level of attainment of each PO/PSO",
             "exhibit": "Documentary evidence towards attainment levels of POs and PSOs from core courses."},
            {"key": "B", "max": 15.0, "kind": "computed",
             "label": "Assessment of overall levels of attainment",
             "exhibit": "Overall PO/PSO attainment (Table 3.8.3).",
             "formula": "15 x (mean overall PO/PSO attainment level / 3)"},
        ],
    },
}

# Requirement code (seed) -> rubric code
REQUIREMENT_TO_RUBRIC: dict[str, str] = {f"REQ_3_{i}": f"3.{i}" for i in range(1, 9)}


def evaluate_rubric(rubric_code: str, context: dict[str, Any]) -> EvaluationResult:
    """
    Deterministic rubric evaluation for one Criterion 3 sub-criterion.

    Expected context:
        components: {"A": float, "B": float, ...}   scores per rubric component
        attainment_formula_configured: bool          (3.7 / 3.8 only)
        supporting_metrics: dict (optional)           copied into metrics
    """
    rubric = C3_RUBRIC[rubric_code]
    max_total = float(rubric["max"])
    rule = f"criterion3.rubric_{rubric_code}"

    if rubric.get("requires_attainment_config") and not context.get("attainment_formula_configured", False):
        return _needs_clarification(
            rule=rule,
            reason=(
                "NBA Tier-I requires the program to set and approve its CO/PO attainment "
                "levels and methodology. Approve the attainment configuration (targets, "
                "level thresholds, direct/indirect weights) before this sub-criterion can be scored."
            ),
            max_score=max_total,
            metrics={"supporting_metrics": context.get("supporting_metrics", {})},
        )

    supplied = context.get("components") or {}
    scores: dict[str, float] = {}
    missing: list[str] = []
    limitations: list[str] = list(context.get("limitations") or [])
    for comp in rubric["components"]:
        raw = supplied.get(comp["key"])
        if raw is None or raw == "":
            missing.append(f"{comp['key']} ({comp['label']})")
            scores[comp["key"]] = 0.0
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            missing.append(f"{comp['key']} (non-numeric)")
            scores[comp["key"]] = 0.0
            continue
        scores[comp["key"]] = round(max(0.0, min(val, float(comp["max"]))), 2)

    total = round(sum(scores.values()), 2)
    pct = (total / max_total * 100.0) if max_total else 0.0

    if missing:
        status = RequirementStatus.WARNING.value
        limitations.insert(0, "Not yet scored: " + "; ".join(missing))
    elif pct >= 70.0:
        status = RequirementStatus.PASS.value
    elif pct >= 40.0:
        status = RequirementStatus.WARNING.value
    else:
        status = RequirementStatus.FAIL.value

    return EvaluationResult(
        status=status,
        score_attained=total,
        max_score=max_total,
        deterministic_metrics={
            "rubric": rubric_code,
            "components": {
                c["key"]: {"score": scores[c["key"]], "max": c["max"], "kind": c["kind"]}
                for c in rubric["components"]
            },
            "percentage": round(pct, 2),
            "supporting_metrics": context.get("supporting_metrics", {}),
        },
        limitations=limitations,
    )


def _rubric_aware(rubric_code: str, legacy):
    """Use the rubric when the context carries `components`; else the legacy rule."""
    def _rule(context: dict[str, Any]) -> EvaluationResult:
        if isinstance(context, dict) and "components" in context:
            return evaluate_rubric(rubric_code, context)
        return legacy(context)
    return _rule


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CRITERION3_RULES: dict[str, Any] = {
    RULE_CO_COMPLETENESS: _rubric_aware("3.1", evaluate_co_completeness),
    RULE_CONTINUOUS_ASSESSMENT: _rubric_aware("3.1", evaluate_co_completeness),
    RULE_COPO_MAPPING: evaluate_copo_mapping,
    RULE_SEE_QUESTION_PAPER: _rubric_aware("3.2", evaluate_see_question_paper),
    RULE_LAB_WORKSHOP: _rubric_aware("3.3", evaluate_lab_workshop),
    RULE_INDUSTRIAL_TRAINING: _rubric_aware("3.4", evaluate_industrial_training),
    RULE_PROJECT_EVALUATION: _rubric_aware("3.5", evaluate_project_evaluation),
    RULE_SDG: _rubric_aware("3.6", evaluate_sdg_evidence),
    RULE_CO_ATTAINMENT: _rubric_aware("3.7", evaluate_co_attainment),
    RULE_PO_PSO_ATTAINMENT: _rubric_aware("3.8", evaluate_po_pso_attainment),
}
