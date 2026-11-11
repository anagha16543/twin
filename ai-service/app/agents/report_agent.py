# report_agent.py
"""
Accreditation Report Generation Agent for NBA Accreditation Readiness.

Responsibilities:
1. Synthesize multi-agent findings, deterministic metrics, and compliance evaluations
   into an inspection-ready Self-Assessment Report (SAR) in GitHub Flavored Markdown (GFM).
2. Format clean, professional markdown tables for:
   - Faculty metrics (SFR, Cadre distribution, Ph.D. ratio, experience)
   - Student performance (Cohort graduation, placement rates, median salary)
   - Faculty research (Indexed publications, patents, research grants, consultancy)
   - Accreditation compliance gap matrix and risk ratings
3. Include an auditable Evidence Registry with document IDs and verification badges.
4. Expose an explicit "Data Limitations and Missing Artifacts" appendix for evaluation integrity.
5. Adhere to the core rule: Python supplies verified numbers; the agent handles document assembly.
"""

import json
from typing import Any, Dict, Optional

from app.services.model_client import call_model
from app.services.metrics_service import evaluate_department_readiness


def generate_inspection_report(
    department_data: Optional[Dict[str, Any]] = None,
    coordinator_summary: Optional[str] = None,
    compliance_analysis: Optional[str] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Generate an auditable, inspection-ready NBA Self-Assessment Report.

    Args:
        department_data: Dictionary containing verified Criteria 3, 4, 5, and 6 datasets.
        coordinator_summary: Optional summary text from the Coordinator Agent.
        compliance_analysis: Optional gap analysis from the Compliance Agent.
        mock_response: Optional mock string for offline unit testing.

    Returns:
        Structured GitHub Flavored Markdown report string.
    """
    if department_data is None:
        department_data = {}

    # 1. Evaluate departmental readiness deterministically
    readiness_eval = evaluate_department_readiness(department_data)

    department = readiness_eval.get("department", "Department Not Specified")
    composite_score = readiness_eval.get("composite_readiness_score", 0.0)
    readiness_verdict = readiness_eval.get("readiness_verdict", "Unknown")
    criterion_breakdown = readiness_eval.get("criterion_breakdown", {})
    gap_summary = readiness_eval.get("gap_summary", {})

    # 2. Extract metrics for tabular formatting
    c3 = criterion_breakdown.get("criterion3", {})
    c4 = criterion_breakdown.get("criterion4", {})
    c5 = criterion_breakdown.get("criterion5", {})
    c6 = criterion_breakdown.get("criterion6", {})

    verified_dossier = {
        "department": department,
        "composite_score": composite_score,
        "readiness_verdict": readiness_verdict,
        "overall_status": readiness_eval.get("overall_status", "Non-Compliant"),
        "criterion_completeness": {
            "Criterion 3": c3.get("completeness_percentage", 0.0),
            "Criterion 4": c4.get("completeness_percentage", 0.0),
            "Criterion 5": c5.get("completeness_percentage", 0.0),
            "Criterion 6": c6.get("completeness_percentage", 0.0)
        },
        "faculty_metrics": {
            "sfr": c5.get("sfr_metrics", {}).get("student_to_faculty_ratio", "N/A"),
            "cadre_ratio": c5.get("cadre_metrics", {}).get("cadre_ratio_display", "N/A"),
            "phd_percentage": c5.get("cadre_metrics", {}).get("qualifications", {}).get("phd_percentage", "N/A"),
            "avg_experience_years": c5.get("experience_metrics", {}).get("average_total_experience_years", "N/A"),
            "avg_institution_stay_years": c5.get("experience_metrics", {}).get("average_institution_experience_years", "N/A")
        },
        "student_metrics": {
            "graduation_rate_no_backlog_pct": (
                c4.get("progression_metrics", {})
                .get("aggregate", {})
                .get("aggregate_completion_rate_without_backlog_pct", "N/A")
            ),
            "overall_graduation_rate_pct": (
                c4.get("progression_metrics", {})
                .get("aggregate", {})
                .get("aggregate_overall_completion_rate_pct", "N/A")
            ),
            "career_progression_pct": (
                c4.get("placement_metrics", {})
                .get("aggregate", {})
                .get("aggregate_progression_pct", "N/A")
            ),
            "placement_pct": (
                c4.get("placement_metrics", {})
                .get("aggregate", {})
                .get("aggregate_placement_pct", "N/A")
            )
        },
        "research_metrics": {
            "confirmed_publications": c6.get("publication_metrics", {}).get("confirmed_publications_count", 0),
            "sci_scopus_papers": c6.get("publication_metrics", {}).get("sci_scopus_confirmed_count", 0),
            "confirmed_patents": c6.get("patent_metrics", {}).get("confirmed_patents_count", 0),
            "research_grants_lakhs": (
                c6.get("project_metrics", {})
                .get("sponsored_projects", {})
                .get("total_funding_amount_lakhs", 0.0)
            ),
            "consultancy_revenue_lakhs": (
                c6.get("project_metrics", {})
                .get("consultancy", {})
                .get("total_revenue_amount_lakhs", 0.0)
            ),
            "aggregate_research_revenue_lakhs": (
                c6.get("project_metrics", {})
                .get("aggregate_research_revenue_lakhs", 0.0)
            ),
            "confirmed_fdps": c6.get("fdp_metrics", {}).get("confirmed_fdp_count", 0)
        },
        "critical_gaps": gap_summary.get("critical_gaps", []),
        "major_gaps": gap_summary.get("major_gaps", []),
        "minor_gaps": gap_summary.get("minor_gaps", [])
    }

    dossier_json = json.dumps(verified_dossier, indent=2, default=str)

    prompt = f"""
You are the Accreditation Report Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to generate a comprehensive, inspection-ready
Self-Assessment Report (SAR) in clean GitHub Flavored Markdown (GFM).

The report will be presented to Department Heads, Deans, and Visiting NBA Peer Evaluators.
All numerical values and compliance determinations have already been verified in Python.
Python is the sole source of truth for all figures.

==================================================
DOCUMENTATION RULES
==================================================

1. Use standard GitHub Flavored Markdown (GFM) including clean tables (`| Header | Header |`).
2. DO NOT change or invent any numerical values.
3. DO NOT invent faculty names, student names, paper titles, or funding agencies.
4. Clearly distinguish verified facts from pending documentation.
5. Provide professional headings, clean tables, and an auditable appendix.

==================================================
VERIFIED ACCREDITATION DOSSIER
==================================================

{dossier_json}

Supporting Coordinator Summary:
{coordinator_summary or "Consolidated department facts supplied in dossier above."}

Supporting Compliance Analysis:
{compliance_analysis or "Gap analysis metrics supplied in dossier above."}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these six sections formatted in GitHub Flavored Markdown:

# NBA Self-Assessment Readiness Dossier

## 1. Executive Summary & Readiness Verdict
State the academic department, overall composite readiness score (0-100), compliance verdict,
and an executive appraisal of department readiness. Include a markdown table summarizing
the completeness percentage and compliance status across Criteria 3, 4, 5, and 6.

## 2. Criterion 5: Faculty Profile & Academic Cadre
Present a clean markdown table of key faculty indicators:
- Student-to-Faculty Ratio (SFR)
- Cadre Distribution (Professors : Associate Professors : Assistant Professors)
- Ph.D. Faculty Percentage
- Average Teaching Experience & Institutional Stay
Summarize faculty stability and cadre balance.

## 3. Criterion 4: Student Academic Performance & Placement
Present a clean markdown table of student outcomes:
- Graduation rate without backlog
- Overall graduation rate
- Placement and Higher Studies progression percentage
Summarize student academic progression and career readiness.

## 4. Criterion 6: Research, Innovations & Faculty Development
Present a clean markdown table of faculty contributions:
- Confirmed Publications (including SCI/Scopus breakdown)
- Patents (Granted, Published, Filed)
- Sponsored Research Funding (INR Lakhs)
- Industrial Consultancy Revenue (INR Lakhs)
- Faculty Development Programs (FDPs) attended/organized

## 5. Compliance Gap Analysis Matrix
Present a clean markdown table listing all Critical and Major gaps:
| Gap ID | Criterion | Severity | Deficient Area | Mandatory Evidence Required |
Explain the immediate risks these pose during an on-site peer evaluation.

## 6. Limitations, Pending Proofs & Verification Appendix
Explicitly list unverified items, pending documentation proofs, and data limitations
(e.g. unverified publications, pending HR appointments, missing SEE individual marks).
State the clear declaration:
"All numerical metrics are deterministically computed in Python without generative LLM extrapolation."
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3600,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )
