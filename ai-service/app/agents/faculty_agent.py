# faculty_agent.py
"""
Faculty Information Analysis Agent for NBA Criterion 5.

Responsibilities:
1. Process verified faculty roster data, designations, qualifications, and teaching experience.
2. Calculate deterministic Student-to-Faculty Ratio (SFR), Cadre Ratio, and Ph.D. percentages.
3. Enforce strict privacy protection (PII minimization): strip personal phones, emails,
   addresses, and identity numbers before model generation.
4. Detect data completeness issues, missing proof documents, and unverified records.
5. Produce structured, auditable findings without inventing faculty credentials.
"""

from typing import Any, Dict, Optional

from app.services.model_client import call_model
from app.services.metrics_service import (
    calculate_criterion5_sfr,
    calculate_criterion5_cadre_metrics,
    calculate_criterion5_experience_metrics,
    calculate_criterion6_publication_metrics,
    calculate_criterion6_patent_metrics,
    calculate_criterion6_project_metrics,
    calculate_criterion6_fdp_metrics
)
from app.utils.privacy_utils import sanitize_faculty_data


def analyze_faculty_information(
    data: Optional[Dict[str, Any]] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Analyze verified faculty information for NBA Criterion 5.

    Python performs all SFR, Cadre, and experience calculations deterministically.
    Groq is used solely to explain, contextualize, and organize verified findings.
    """
    if data is None:
        data = {}

    raw_faculty = data.get("faculty_members", [])
    total_students = int(data.get("total_enrolled_students", 0))

    # 1. PII Sanitization (Privacy Protection)
    sanitized_faculty = sanitize_faculty_data(raw_faculty)

    # 2. Deterministic Mathematical Calculations in Python
    faculty_count = len(sanitized_faculty)
    sfr_metrics = calculate_criterion5_sfr(
        total_students=total_students,
        regular_faculty_count=faculty_count
    )
    cadre_metrics = calculate_criterion5_cadre_metrics(sanitized_faculty)
    experience_metrics = calculate_criterion5_experience_metrics(sanitized_faculty)

    # 3. Assess record verification and data completeness
    verified_records_count = sum(
        1 for f in sanitized_faculty if f.get("verified", False)
    )
    pending_records_count = faculty_count - verified_records_count

    missing_indicators = []
    if total_students <= 0:
        missing_indicators.append("Total enrolled student intake count not provided")
    if faculty_count == 0:
        missing_indicators.append("No faculty roster records provided")
    if any("total_experience_years" not in f for f in sanitized_faculty):
        missing_indicators.append("Experience data missing for one or more faculty members")

    # 4. Prepare verified facts summary for LLM
    verified_summary = {
        "department": data.get("department", "Not specified"),
        "academic_year": data.get("academic_year", "Not specified"),
        "total_enrolled_students": total_students,
        "faculty_headcount": faculty_count,
        "sfr_metrics": sfr_metrics,
        "cadre_metrics": cadre_metrics,
        "experience_metrics": experience_metrics,
        "verification_audit": {
            "verified_records": verified_records_count,
            "pending_verification": pending_records_count
        },
        "sanitized_faculty_roster": sanitized_faculty,
        "missing_indicators": missing_indicators
    }

    # 5. Formulate Factually Bounded Prompt
    prompt = f"""
You are the Faculty Information Analysis Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to analyze VERIFIED faculty information
for NBA Criterion 5 (Faculty Information & Contributions).

All mathematical values (SFR, Cadre Ratio, Ph.D. percentage, and experience means)
have already been calculated deterministically by Python.
Python is the sole source of truth for all figures.

==================================================
STRICT DATA INTEGRITY & PRIVACY RULES
==================================================

1. Use ONLY the verified metrics and sanitized information supplied below.
2. DO NOT recalculate any numbers or alter percentages.
3. DO NOT invent:
   - faculty names, credentials, degrees, or designations
   - Student-to-Faculty Ratio (SFR) values or compliance scores
   - teaching workloads or course assignments
   - service years or dates of joining
4. NEVER output private personal identifiers (phone numbers, personal emails, home addresses).
5. Clearly distinguish verified faculty records from records pending verification.
6. Do not make compliance claims such as 'Criterion 5 is compliant' or 'non-compliant'
   unless explicitly validated against an official institutional threshold.
7. If data for a category is missing, explicitly state that it is unavailable.

==================================================
VERIFIED FACULTY INFORMATION (CRITERION 5)
==================================================

{verified_summary}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

SECTION 1
Faculty Roster and Cadre Ratio Summary
Report total faculty headcount, breakdown by designation (Professors, Associate Professors, Assistant Professors),
and Cadre Ratio. Report highest qualifications and Ph.D. percentage.

SECTION 2
Student-to-Faculty Ratio (SFR) Analysis
Report total enrolled students, qualified regular faculty count, and computed SFR ratio.
Do not claim compliance or non-compliance.

SECTION 3
Faculty Experience and Teaching Distribution
Report average total teaching experience, maximum/minimum experience, and average institution tenure.

SECTION 4
Data Completeness and Evidence Verification Audit
Report verified record count vs records pending verification.
List specific missing documentation (e.g. appointment orders, qualification certificates).

SECTION 5
Recommendations for Criterion 5 Evidence
Provide actionable, factual recommendations for evidence collection and audit preparation.
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3000,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )


# ============================================================
# CRITERION 6 FACULTY CONTRIBUTIONS ANALYSIS
# ============================================================

def analyze_faculty_contributions(
    data: Optional[Dict[str, Any]] = None,
    mock_response: Optional[str] = None
) -> str:
    """
    Analyze verified faculty research, publications, patents, funded projects,
    consultancy, and FDPs for NBA Criterion 6.

    Strict Rule:
    Only VERIFIED contributions are counted as confirmed achievements.
    Pending/unverified submissions are reported separately.
    All financial totals and counts are calculated deterministically by Python.
    """
    if data is None:
        data = {}

    publications = data.get("publications", [])
    patents = data.get("patents", [])
    projects = data.get("sponsored_projects", [])
    consultancy = data.get("consultancy", [])
    fdps = data.get("fdps", [])

    # 1. Deterministic Python Calculations
    pub_metrics = calculate_criterion6_publication_metrics(publications)
    patent_metrics = calculate_criterion6_patent_metrics(patents)
    project_metrics = calculate_criterion6_project_metrics(projects, consultancy)
    fdp_metrics = calculate_criterion6_fdp_metrics(fdps)

    # 2. Evidence Audit Overview
    total_submissions = (
        len(publications) + len(patents) + len(projects) + len(consultancy) + len(fdps)
    )
    total_confirmed = (
        pub_metrics["confirmed_publications_count"]
        + patent_metrics["confirmed_patents_count"]
        + project_metrics["sponsored_projects"]["confirmed_count"]
        + project_metrics["consultancy"]["confirmed_count"]
        + fdp_metrics.get("confirmed_fdp_count", 0)
    )
    total_pending = total_submissions - total_confirmed

    verified_summary = {
        "department": data.get("department", "Not specified"),
        "academic_years_covered": data.get("academic_years_covered", []),
        "publications_summary": pub_metrics,
        "patents_summary": patent_metrics,
        "research_funding_summary": project_metrics,
        "fdp_summary": fdp_metrics,
        "overall_verification_status": {
            "total_contributions_logged": total_submissions,
            "confirmed_verified_contributions": total_confirmed,
            "pending_verification": total_pending
        }
    }

    prompt = f"""
You are the Faculty Contributions Analysis Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to analyze VERIFIED faculty contributions
for NBA Criterion 6 (Faculty Contributions, R&D, Consultancy, FDPs).

All numerical counts and financial totals have been calculated deterministically by Python.
Python is the sole source of truth for all numbers.

==================================================
STRICT DATA INTEGRITY & EVIDENCE RULES
==================================================

1. Use ONLY the verified metrics and summary supplied below.
2. DO NOT recalculate any totals or funding amounts.
3. DO NOT invent:
   - paper titles, journal names, impact factors, or citation counts
   - patent titles, application numbers, or patent statuses
   - grant amounts, funding agencies (e.g. DST, AICTE), or consultancy clients
   - FDP titles, organizers, or certificates
4. CRITICAL: Never count unverified or pending entries as confirmed achievements.
5. Clearly distinguish between confirmed/verified records and entries pending documentation.
6. Do not make compliance claims or award unofficial NBA marks.
7. Preserve all figures in INR Lakhs exactly as supplied.

==================================================
VERIFIED FACULTY CONTRIBUTIONS (CRITERION 6)
==================================================

{verified_summary}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

SECTION 1
Research Publications and Journal Indexing
Report total publications submitted, confirmed publications count, and pending verification count.
Break down confirmed publications by indexing (SCI, SCIE, Scopus, UGC-CARE, Conferences).

SECTION 2
Intellectual Property and Patents
Report confirmed patents count vs pending count.
Break down confirmed patents by status: Granted, Published, Filed.

SECTION 3
Sponsored Research Projects and Consultancy Revenue
Report confirmed sponsored projects count and total grant funding in INR Lakhs.
Report confirmed consultancy projects count and total revenue in INR Lakhs.
Report aggregate research and consultancy revenue.

SECTION 4
Faculty Development Programs (FDPs) and STTPs
Report confirmed FDP count vs pending count.
Break down confirmed participation vs organized programs.

SECTION 5
Evidence Verification Audit and Recommendations
Report overall verified contributions vs pending verification.
Provide actionable, factual recommendations for retrieving proof documents (DOIs, sanction letters, patent certificates).
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3000,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )
