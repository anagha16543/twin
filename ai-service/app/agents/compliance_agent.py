# compliance_agent.py
"""
Compliance Gap Analysis Agent for NBA Accreditation Readiness.

Responsibilities:
1. Deterministically evaluate institutional evidence against official NBA SAR criteria
   (Criteria 3, 4, 5, and 6) using Python business rules.
2. Calculate overall completeness percentages, gap counts, and severity rankings (Critical, Major, Minor).
3. Identify missing mandatory artifacts (e.g. SEE question papers, sanction letters, DOIs, patent gazettes).
4. Produce a factually bounded, audit-ready compliance matrix and prioritized remediation roadmap.
5. Strictly adhere to the principle: Python computes all compliance metrics; LLM organizes and formats findings.
"""

import json
from typing import Any, Dict, Optional

from app.services.model_client import call_model
from app.services.metrics_service import evaluate_department_readiness


def analyze_compliance_gaps(
    department_data: Optional[Dict[str, Any]] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Perform a complete NBA accreditation compliance gap analysis.

    Python deterministically calculates:
    - Composite readiness score
    - Completeness percentages per criterion
    - Critical, Major, and Minor gap counts
    - Required documentary evidence items

    The LLM organizes verified findings into an audit-ready compliance matrix.
    """
    if department_data is None:
        department_data = {}

    # 1. Deterministic Rule-Based Compliance Evaluation in Python
    compliance_evaluation = evaluate_department_readiness(department_data)

    department_name = compliance_evaluation.get("department", "Department Not Specified")
    composite_score = compliance_evaluation.get("composite_readiness_score", 0.0)
    readiness_verdict = compliance_evaluation.get("readiness_verdict", "Unknown")
    overall_status = compliance_evaluation.get("overall_status", "Non-Compliant")
    gap_summary = compliance_evaluation.get("gap_summary", {})
    criterion_breakdown = compliance_evaluation.get("criterion_breakdown", {})

    verified_facts = {
        "department": department_name,
        "composite_readiness_score": composite_score,
        "overall_status": overall_status,
        "readiness_verdict": readiness_verdict,
        "gap_statistics": {
            "total_gaps": gap_summary.get("total_gaps", 0),
            "critical_gaps_count": gap_summary.get("critical_count", 0),
            "major_gaps_count": gap_summary.get("major_count", 0),
            "minor_gaps_count": gap_summary.get("minor_count", 0)
        },
        "critical_gaps_detail": gap_summary.get("critical_gaps", []),
        "major_gaps_detail": gap_summary.get("major_gaps", []),
        "minor_gaps_detail": gap_summary.get("minor_gaps", []),
        "criteria_summary": {
            "criterion3": {
                "completeness_pct": criterion_breakdown.get("criterion3", {}).get("completeness_percentage", 0.0),
                "status": criterion_breakdown.get("criterion3", {}).get("status", "Unknown"),
                "gaps_count": criterion_breakdown.get("criterion3", {}).get("gaps_count", 0)
            },
            "criterion4": {
                "completeness_pct": criterion_breakdown.get("criterion4", {}).get("completeness_percentage", 0.0),
                "status": criterion_breakdown.get("criterion4", {}).get("status", "Unknown"),
                "gaps_count": criterion_breakdown.get("criterion4", {}).get("gaps_count", 0)
            },
            "criterion5": {
                "completeness_pct": criterion_breakdown.get("criterion5", {}).get("completeness_percentage", 0.0),
                "status": criterion_breakdown.get("criterion5", {}).get("status", "Unknown"),
                "gaps_count": criterion_breakdown.get("criterion5", {}).get("gaps_count", 0)
            },
            "criterion6": {
                "completeness_pct": criterion_breakdown.get("criterion6", {}).get("completeness_percentage", 0.0),
                "status": criterion_breakdown.get("criterion6", {}).get("status", "Unknown"),
                "gaps_count": criterion_breakdown.get("criterion6", {}).get("gaps_count", 0)
            }
        }
    }

    verified_facts_json = json.dumps(verified_facts, indent=2, default=str)

    prompt = f"""
You are the Compliance Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to analyze the VERIFIED compliance evaluation and gap audit
for National Board of Accreditation (NBA) readiness across Criteria 3, 4, 5, and 6.

All compliance scores, gap classifications, and checklist metrics have been
calculated deterministically by Python.
Python is the sole source of truth for all facts and numbers.

==================================================
STRICT DATA INTEGRITY & AUDIT RULES
==================================================

1. Use ONLY the verified compliance metrics and gap items supplied below.
2. DO NOT alter any readiness score, percentage, or gap count.
3. DO NOT recalculate or perform arithmetic.
4. DO NOT invent:
   - official NBA marks or final accreditation awards
   - fake regulatory rules or non-existent deficiencies
   - document names or evidence IDs not listed in the facts
5. Maintain strict objectivity: present gaps neutrally with their exact severity (Critical, Major, Minor).
6. Preserve the exact gap IDs (e.g. C3-GAP-001, C5-GAP-001) for audit traceability.

==================================================
VERIFIED COMPLIANCE FACTS & AUDIT DATA
==================================================

{verified_facts_json}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

SECTION 1
Executive Compliance Summary and Verdict
State the department name, composite readiness score, overall status, and readiness verdict.
Summarize the total gap count broken down by Critical, Major, and Minor severity.

SECTION 2
Criterion-by-Criterion Compliance Evaluation
Report the completeness percentage, status, and gap count for each criterion:
- Criterion 3 (Course Outcomes and Program Outcomes)
- Criterion 4 (Students' Performance and Progression)
- Criterion 5 (Faculty Information, Cadre, and SFR)
- Criterion 6 (Faculty Contributions, R&D, Consultancy, and FDPs)

SECTION 3
Critical and Major Gap Matrix
List each Critical and Major gap with:
- Gap ID
- Associated Criterion
- Severity
- Specific Deficiency Description
- Mandatory Evidence / Action Required

SECTION 4
Evidence Verification Shortfalls
Detail the missing documentary proofs (e.g. sanction letters, DOIs, patent gazettes, student appointment orders)
that must be uploaded or resolved to achieve full compliance.

SECTION 5
Prioritized Remediation Action Plan
Provide an auditable, phased action plan:
- Immediate Priority: Resolving Critical non-compliances
- Medium Priority: Addressing Major gaps and document verification
- Low Priority: Refining Minor documentation before peer evaluator visit
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3200,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )
