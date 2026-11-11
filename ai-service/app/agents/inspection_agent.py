# inspection_agent.py
"""
Virtual Inspection Digital Twin Agent for NBA Evaluators & Accreditation Cockpit.

Responsibilities:
1. Act as an interactive "Digital Twin" for NBA Visiting Evaluators and Peer Reviewers.
2. Deterministically compute evidence verification ratios across faculty, achievements,
   publications, patents, research projects, and FDPs.
3. Automatically flag "Red Flag" audit concerns requiring physical on-site verification.
4. Provide an interactive query interface (evaluator cockpit) strictly grounded in verified facts.
5. Strictly adhere to factuality: never hallucinate compliance, metrics, or nonexistent evidence files.
"""

import json
from typing import Any, Dict, Optional

from app.services.model_client import call_model
from app.services.metrics_service import evaluate_department_readiness


def calculate_inspection_verification_ratios(
    department_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministically compute verification ratios across all evidence categories.
    """
    c4 = department_data.get("criterion4", {})
    c5 = department_data.get("criterion5", {})
    c6 = department_data.get("criterion6", {})

    # 1. Faculty Profiles
    faculty_list = c5.get("faculty_members", [])
    total_faculty = len(faculty_list)
    verified_faculty = sum(1 for f in faculty_list if f.get("verified", False))

    # 2. Student Achievements
    ach_list = c4.get("achievements", [])
    total_ach = len(ach_list)
    verified_ach = sum(1 for a in ach_list if a.get("verified", False))

    # 3. Research Publications
    pub_list = c6.get("publications", [])
    total_pubs = len(pub_list)
    verified_pubs = sum(1 for p in pub_list if p.get("verified", False))

    # 4. Patents
    pat_list = c6.get("patents", [])
    total_pats = len(pat_list)
    verified_pats = sum(1 for p in pat_list if p.get("verified", False))

    # 5. Sponsored Projects
    proj_list = c6.get("sponsored_projects", [])
    total_proj = len(proj_list)
    verified_proj = sum(1 for p in proj_list if p.get("verified", False))

    # 6. Consultancy
    consult_list = c6.get("consultancy", [])
    total_consult = len(consult_list)
    verified_consult = sum(1 for c in consult_list if c.get("verified", False))

    # 7. FDPs
    fdp_list = c6.get("fdps", [])
    total_fdps = len(fdp_list)
    verified_fdps = sum(1 for f in fdp_list if f.get("verified", False))

    grand_total = (
        total_faculty + total_ach + total_pubs + total_pats
        + total_proj + total_consult + total_fdps
    )
    grand_verified = (
        verified_faculty + verified_ach + verified_pubs + verified_pats
        + verified_proj + verified_consult + verified_fdps
    )

    overall_ratio_pct = (
        round((grand_verified / grand_total) * 100, 2)
        if grand_total > 0 else 0.0
    )

    return {
        "grand_total_submissions": grand_total,
        "grand_total_verified": grand_verified,
        "grand_total_pending": grand_total - grand_verified,
        "overall_verification_ratio_pct": overall_ratio_pct,
        "category_breakdown": {
            "faculty_profiles": {
                "total": total_faculty,
                "verified": verified_faculty,
                "pending": total_faculty - verified_faculty
            },
            "student_achievements": {
                "total": total_ach,
                "verified": verified_ach,
                "pending": total_ach - verified_ach
            },
            "publications": {
                "total": total_pubs,
                "verified": verified_pubs,
                "pending": total_pubs - verified_pubs
            },
            "patents": {
                "total": total_pats,
                "verified": verified_pats,
                "pending": total_pats - verified_pats
            },
            "sponsored_projects": {
                "total": total_proj,
                "verified": verified_proj,
                "pending": total_proj - verified_proj
            },
            "consultancy": {
                "total": total_consult,
                "verified": verified_consult,
                "pending": total_consult - verified_consult
            },
            "fdps": {
                "total": total_fdps,
                "verified": verified_fdps,
                "pending": total_fdps - verified_fdps
            }
        }
    }


def run_virtual_inspection_audit(
    department_data: Optional[Dict[str, Any]] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Run an end-to-end Virtual Inspection Cockpit audit for visiting evaluators.

    Computes deterministic verification ratios and highlights physical audit red flags.
    """
    if department_data is None:
        department_data = {}

    readiness_eval = evaluate_department_readiness(department_data)
    verification_ratios = calculate_inspection_verification_ratios(department_data)

    audit_dossier = {
        "department": readiness_eval.get("department", "Department Not Specified"),
        "composite_readiness_score": readiness_eval.get("composite_readiness_score", 0.0),
        "overall_status": readiness_eval.get("overall_status", "Non-Compliant"),
        "readiness_verdict": readiness_eval.get("readiness_verdict", "Unknown"),
        "verification_metrics": verification_ratios,
        "criterion_breakdown": readiness_eval.get("criterion_breakdown", {}),
        "gap_summary": readiness_eval.get("gap_summary", {})
    }

    audit_json = json.dumps(audit_dossier, indent=2, default=str)

    prompt = f"""
You are the Virtual Inspection Digital Twin Agent in an
AI-Driven NBA Accreditation Readiness System.

You are acting as an objective Evaluator Cockpit for Visiting NBA Peer Evaluators.
Your job is to audit institutional claims, check documentary evidence ratios,
and pinpoint high-risk items requiring scrutiny during the physical campus visit.

All verification metrics, scores, and gaps have been calculated deterministically by Python.
Python is the sole source of truth for all facts.

==================================================
EVALUATOR AUDIT RULES
==================================================

1. Maintain an objective, rigorous evaluator perspective.
2. Highlight discrepancies between submitted claims and verified proofs.
3. DO NOT recalculate or invent numbers.
4. Flag high-risk audit items ("Red Flags") where documentary proof is pending or missing.
5. Provide actionable inspection checkpoints for the visiting committee.

==================================================
VERIFIED AUDIT DATA
==================================================

{audit_json}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

SECTION 1
Virtual Inspection Cockpit Overview
State the department, composite readiness score, overall verification ratio (verified vs pending proofs),
and an evaluator appraisal of audit readiness.

SECTION 2
Documentary Evidence Verification Audit
Report the evidence verification metrics:
- Overall verification percentage
- Breakdown of verified vs pending entries across Faculty Profiles, Student Achievements,
  Publications, Patents, Research Grants, Consultancy, and FDPs.

SECTION 3
Evaluator Red Flags & High-Risk Areas
List specific non-compliances and documentation gaps that will attract audit penalties:
- SFR or cadre imbalances
- Unindexed or pending publications
- Absence of student-level SEE marks or attainment formulas
- Unverified student or faculty achievements

SECTION 4
On-Site Physical Inspection Checklist
Provide a prioritized checklist of physical files and original registers the visiting team
must demand to inspect on Day 1 of the campus visit (e.g. Master Appointment Orders,
Original Student Registers, Grant Sanction Letters, Patent Gazettes).

SECTION 5
Evaluator Recommendations for Accreditation Chair
Provide formal, objective recommendations for the evaluation team's exit report.
Do not assign unofficial marks; recommend verification actions and conditions.
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3200,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )


def query_inspection_cockpit(
    query: str,
    department_data: Optional[Dict[str, Any]] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Answer an evaluator's specific query about departmental accreditation evidence.

    Grounds all answers strictly in verified Python data.
    """
    if department_data is None:
        department_data = {}

    readiness_eval = evaluate_department_readiness(department_data)
    verification_ratios = calculate_inspection_verification_ratios(department_data)

    context = {
        "department": readiness_eval.get("department", "Department Not Specified"),
        "readiness_eval": readiness_eval,
        "verification_ratios": verification_ratios
    }

    context_json = json.dumps(context, indent=2, default=str)

    prompt = f"""
You are the Virtual Inspection Digital Twin Cockpit responding to an
NBA Peer Reviewer query.

Answer the evaluator query strictly using the verified evidence data below.
If the information requested is not present in the verified record, explicitly state:
"This information is not documented in the verified institutional dataset."

DO NOT invent numbers, names, or compliance verdicts.
Be precise, concise, and refer to specific verified figures.

==================================================
VERIFIED DEPARTMENT EVIDENCE CONTEXT
==================================================

{context_json}

==================================================
EVALUATOR QUERY
==================================================

"{query}"

==================================================
ANSWER
==================================================
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=1500,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )
