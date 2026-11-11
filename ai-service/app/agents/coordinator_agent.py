import json
from typing import Any, Dict, Optional

from data.criterion3_data import criterion3_data
from app.services.model_client import call_model
from app.services.metrics_service import evaluate_department_readiness


# ============================================================
# 3. GET COMPACT VERIFIED FACTS
# ============================================================

def get_verified_facts(data=None):
    """
    Return only the important verified Criterion 3 facts.

    If external data is supplied, use that data.

    If no data is supplied, use the local
    criterion3_data.py dataset.

    Python is the source of truth for:
    - course information
    - assessment scheme
    - COs
    - assessment-to-CO mapping
    - CO-PO-PSO mapping
    - grade distribution
    - student record count
    - data availability
    """

    # --------------------------------------------------------
    # Use local verified data if no external data is supplied
    # --------------------------------------------------------

    if data is None:
        data = criterion3_data

    # --------------------------------------------------------
    # Return compact verified facts
    # --------------------------------------------------------

    return {
        "course": data["course"],

        "course_outcomes": data["course_outcomes"],

        "assessment_scheme": data["assessment_scheme"],

        "micro_project": data["micro_project"],

        "assessment_co_mapping": data[
            "assessment_co_mapping"
        ],

        "co_po_pso_mapping": data[
            "co_po_pso_mapping"
        ],

        "grade_distribution": data[
            "grade_distribution"
        ],

        "student_record_count": len(
            data["students"]
        ),

        "data_quality": data[
            "data_quality"
        ],

        # Deterministic requirement evaluation forwarded by the backend
        # (None when the agent is run standalone on the local dataset).
        "backend_evaluation": data.get("backend_evaluation")
    }


# ============================================================
# 4. COMPACT AGENT OUTPUT
# ============================================================

def compact_agent_output(text, max_chars=1800):
    """
    Keep agent output small enough to stay within the
    Groq TPM limit.

    The verified Python data remains the source of truth,
    so the full agent output does not need to be sent.
    """

    if not text:
        return ""

    text = str(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n[Agent output truncated]"


# ============================================================
# 5. COORDINATOR FUNCTION
# ============================================================

def coordinate_criterion3(
    assessment_analysis,
    student_analysis,
    data=None,
    mock_response=None
):
    """
    Combine the Assessment Agent and Student Agent outputs.

    The Coordinator is an organizing agent.

    Python-verified data is the factual source of truth.

    If external Criterion 3 data is supplied, it is used.

    If no external data is supplied, the local
    criterion3_data.py dataset is used.

    The LLM must not invent:
    - numbers
    - mappings
    - formulas
    - thresholds
    - attainment values
    - missing evidence
    - recommendations
    """

    # --------------------------------------------------------
    # Get verified facts
    # --------------------------------------------------------

    verified_facts = get_verified_facts(data)

    verified_facts_json = json.dumps(
        verified_facts,
        indent=2,
        default=str
    )

    # --------------------------------------------------------
    # Compact agent outputs
    # --------------------------------------------------------

    assessment_text = compact_agent_output(
        assessment_analysis,
        max_chars=1800
    )

    student_text = compact_agent_output(
        student_analysis,
        max_chars=1800
    )

    # ========================================================
    # 6. COORDINATOR PROMPT
    # ========================================================

    prompt = f"""
You are the Coordinator Agent for an
AI-Driven NBA Accreditation Readiness System.

Produce a factual Criterion 3 report.

Python-verified data is the SOURCE OF TRUTH.

The Assessment Agent and Student Agent outputs are
supporting summaries only.


================ VERIFIED DATA ================

{verified_facts_json}


================ ASSESSMENT AGENT ================

{assessment_text}


================ STUDENT AGENT ================

{student_text}


================ RULES ================

1. Use the Python-verified data for all factual values.

2. Never change a verified number.

3. Never calculate a new number.

4. Never invent CO attainment.

5. Never invent PO attainment.

6. Never invent formulas.

7. Never invent thresholds.

8. Never invent targets.

9. Never invent assessment mappings.

10. Never invent student information.

11. Never expose student names, USNs, or phone numbers.

12. Do not infer relationships between attendance,
    marks, grades, COs, or POs.

13. Do not make compliance judgments.

14. Do not use unsupported words such as:
    good, bad, strong, weak, poor, effective, ineffective,
    satisfactory, unsatisfactory.

15. CO-PO-PSO mapping IS AVAILABLE in the verified data.

16. Do not say that CO-PO-PSO mapping is missing.

17. Use ONLY the verified facts provided in the assessment and student analysis sections below.
    Do not invent assessment-to-CO mappings, student counts, or data availability claims.

18. If an assessment-to-CO mapping is not mentioned in the analysis, do not state it.

19. Report student record counts and data limitations exactly as stated in the analysis.

20. If CO attainment or PO attainment formula information is not present in the analysis, state that it is unavailable.

21. A data limitation is not automatically a recommendation.

22. Do not invent recommendations.

23. Do not invent additional analysis.

24. If no explicit further analysis is supported, write:
    No additional analysis was explicitly identified.

25. If no explicit next step is supported, write:
    No additional next steps were explicitly identified.




================ OUTPUT ================

Return exactly these seven sections:


1. Criterion 3 Summary

Briefly summarize:
- course
- assessment scheme
- assessment-to-CO coverage
- student record availability
- explicit data limitations


2. Assessment Findings

Include:
- course information
- assessment scheme
- COs
- assessment-to-CO mapping
- Micro Project rubric
- CO-PO-PSO mapping
- grade distribution
- relevant data availability


3. Student Performance Findings

Include the verified student statistics supplied by the
Student Agent.

Do not recalculate or interpret them.


4. Combined Observations

Only combine facts explicitly supported by the verified
data and agent outputs.

Do not create new conclusions.


5. Missing Evidence

List only explicitly unavailable information:

- student-level SEE marks
- question-level student marks
- official CO attainment formula
- official PO attainment formula

Do NOT list the 56-versus-60 difference as missing evidence.


6. Further Analysis Required

Only include explicitly supported analysis needs.

Otherwise write:

No additional analysis was explicitly identified.


7. Recommended Next Steps

Only include explicitly stated recommendations from the
agents.

Do not create recommendations from data limitations.

Otherwise write:

No additional next steps were explicitly identified.
"""


    # ========================================================
    # 7. CALL MODEL CLIENT
    # ========================================================

    return call_model(
        prompt=prompt,
        max_output_tokens=1400,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )


# ============================================================
# 8. MULTI-CRITERIA DEPARTMENT COORDINATOR
# ============================================================

def coordinate_department_readiness(
    department_data: Optional[Dict[str, Any]] = None,
    criterion3_summary: Optional[str] = None,
    criterion4_summary: Optional[str] = None,
    criterion5_summary: Optional[str] = None,
    criterion6_summary: Optional[str] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Coordinate and synthesize findings across NBA Criteria 3, 4, 5, and 6.

    Responsibilities:
    1. Resolve potential inconsistencies or duplicate claims across criteria.
    2. Enforce verified Python ground truth for all metrics.
    3. Ensure no agent outputs hallucinate or contradict official datasets.
    4. Produce a coherent, unified departmental assessment synthesis.
    """
    if department_data is None:
        department_data = {}

    # Deterministic ground truth evaluation
    readiness_eval = evaluate_department_readiness(department_data)

    verified_summary = {
        "department": readiness_eval.get("department", "Department Not Specified"),
        "composite_readiness_score": readiness_eval.get("composite_readiness_score", 0.0),
        "overall_status": readiness_eval.get("overall_status", "Non-Compliant"),
        "readiness_verdict": readiness_eval.get("readiness_verdict", "Unknown"),
        "gap_statistics": {
            "total_gaps": readiness_eval.get("gap_summary", {}).get("total_gaps", 0),
            "critical_count": readiness_eval.get("gap_summary", {}).get("critical_count", 0),
            "major_count": readiness_eval.get("gap_summary", {}).get("major_count", 0),
            "minor_count": readiness_eval.get("gap_summary", {}).get("minor_count", 0)
        },
        "criterion_breakdown": {
            "criterion3_completeness_pct": (
                readiness_eval.get("criterion_breakdown", {})
                .get("criterion3", {})
                .get("completeness_percentage", 0.0)
            ),
            "criterion4_completeness_pct": (
                readiness_eval.get("criterion_breakdown", {})
                .get("criterion4", {})
                .get("completeness_percentage", 0.0)
            ),
            "criterion5_completeness_pct": (
                readiness_eval.get("criterion_breakdown", {})
                .get("criterion5", {})
                .get("completeness_percentage", 0.0)
            ),
            "criterion6_completeness_pct": (
                readiness_eval.get("criterion_breakdown", {})
                .get("criterion6", {})
                .get("completeness_percentage", 0.0)
            )
        }
    }

    verified_json = json.dumps(verified_summary, indent=2, default=str)

    c3_text = compact_agent_output(criterion3_summary, max_chars=1200)
    c4_text = compact_agent_output(criterion4_summary, max_chars=1200)
    c5_text = compact_agent_output(criterion5_summary, max_chars=1200)
    c6_text = compact_agent_output(criterion6_summary, max_chars=1200)

    prompt = f"""
You are the Central Coordinator Agent for an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to synthesize multi-agent findings across
NBA Criteria 3, 4, 5, and 6 into a unified departmental readiness synthesis.

Python-verified data is the SOURCE OF TRUTH.
The individual criteria agent summaries are supporting inputs only.

==================================================
VERIFIED DEPARTMENT FACTS
==================================================

{verified_json}

==================================================
CRITERION AGENT SUMMARIES
==================================================

[Criterion 3: Course & Program Outcomes]
{c3_text or "No specific agent text provided; use verified facts."}

[Criterion 4: Student Performance & Progression]
{c4_text or "No specific agent text provided; use verified facts."}

[Criterion 5: Faculty Roster, SFR & Cadre]
{c5_text or "No specific agent text provided; use verified facts."}

[Criterion 6: Faculty Contributions, R&D & FDPs]
{c6_text or "No specific agent text provided; use verified facts."}

==================================================
COORDINATION RULES
==================================================

1. Use verified Python facts for all numerical figures and scores.
2. DO NOT change or invent any metrics.
3. Prevent duplicate claims: ensure items (like faculty achievements or grants) are not double-counted.
4. Maintain factual consistency across all criteria.
5. If an agent summary contradicts the verified data, the verified data takes absolute precedence.

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

1. Consolidated Departmental Readiness Overview
State department, composite score, overall compliance status, and brief synthesis.

2. Criterion-wise Evidence Synthesis
Briefly summarize verified status across:
- Criterion 3 (Curriculum and Outcomes)
- Criterion 4 (Student Success and Placements)
- Criterion 5 (Faculty Strength and SFR)
- Criterion 6 (Research, Patents, and Development)

3. Cross-Criteria Consistency and Duplicate Checks
Confirm that no duplicate achievements or cross-criterion contradictions exist.

4. Consolidated Audit Risks and Missing Evidence
Summarize the critical documentation deficiencies across all criteria.

5. Unified Action Plan for Accreditation Visit
List key coordinated steps the department must take prior to evaluator arrival.
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=2800,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )