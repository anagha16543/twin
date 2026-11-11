from data.criterion3_data import criterion3_data
from app.services.model_client import call_model
from app.services.metrics_service import (
    calculate_student_statistics,
    calculate_criterion4_progression_metrics,
    calculate_criterion4_placement_metrics,
    summarize_student_achievements
)





# ============================================================
# 4. STUDENT PERFORMANCE ANALYSIS
# ============================================================

def analyze_student_performance(data=None, mock_response=None):
    """
    Analyze verified student performance data for NBA
    Criterion 3.

    Python calculates exact numerical statistics.
    Groq is used only to explain and organize the
    verified information.
    """

    # --------------------------------------------------------
    # Load verified student data
    # --------------------------------------------------------

    if data is None:

        student_records = criterion3_data["students"]

        data = {
            "student_records": student_records,
            "course_student_count": (
                criterion3_data["grade_distribution"]["registered"]
            ),
            "available_student_records": len(student_records)
        }

    else:

        # Handle both "student_records" and "students" keys flexibly
        student_records = (
            data.get("student_records")
            or data.get("students")
            or []
        )

        course_student_count = data.get(
            "course_student_count",
            len(student_records)
        )
        available_student_records = data.get(
            "available_student_records",
            len(student_records)
        )

        data = {
            "student_records": student_records,
            "course_student_count": course_student_count,
            "available_student_records": available_student_records
        }

    # --------------------------------------------------------
    # Calculate statistics using Python
    # --------------------------------------------------------

    statistics = calculate_student_statistics(
        student_records
    )

    # --------------------------------------------------------
    # Prepare verified summary for the AI
    # --------------------------------------------------------

    missing_count = max(
        0,
        data["course_student_count"] - data["available_student_records"]
    )

    verified_summary = {
        "course_registered_students": data[
            "course_student_count"
        ],

        "available_student_records": data[
            "available_student_records"
        ],

        "missing_student_records": missing_count,

        "statistics": statistics,

        "available_fields": [
            "Student ID",
            "CIE-I",
            "CIE-II",
            "Micro Project",
            "Internal Total",
            "Attendance"
        ],

        "missing_from_student_input": [
            "Student-level SEE marks",
            "Question-level assessment marks",
            "Official CO attainment formula",
            "CO-PO mapping within this student-performance input"
        ]
    }

    # --------------------------------------------------------
    # Prompt for Student Agent
    # --------------------------------------------------------

    prompt = f"""
You are the Student Performance Analysis Agent
in an NBA Accreditation Readiness System.

Your responsibility is to analyze VERIFIED student
performance information related to NBA Criterion 3.

The information below has already been calculated
and verified by Python from backend data.

The backend data is the source of truth.


==================================================
STRICT DATA INTEGRITY RULES
==================================================

1. Use ONLY the verified information supplied below.

2. DO NOT recalculate any statistics.

3. DO NOT change any numerical value.

4. DO NOT invent:
   - student marks
   - student records
   - student IDs
   - CO attainment
   - PO attainment
   - targets
   - thresholds
   - formulas
   - missing assessment results

5. Do not create values for the missing student records.

6. Do not identify students using names, USNs,
   phone numbers, or other personal information.

7. Use only anonymized student IDs if they are explicitly
   supplied.

8. Do not describe performance as:
   - good
   - bad
   - weak
   - strong
   - low
   - high
   - moderate
   - poor
   - effective
   - ineffective
   - fair
   - unfair

   unless an official benchmark or threshold is supplied.

9. Numerical values must be reported exactly as supplied.

10. Do not infer CO attainment from CIE marks.

11. Do not infer SEE performance because student-level
    SEE marks are not included.

12. Do not infer student ability, learning quality,
    fairness, or assessment effectiveness.

13. Do not claim that Criterion 3 is compliant or
    non-compliant.

14. Do not claim that CO-PO mapping does not exist
    in the overall system.

    Instead, if relevant, say:

    "The required CO-PO mapping is not included in the
    student-performance input supplied to this agent."

15. Similarly, if the CO attainment formula is needed,
    say:

    "The official CO attainment formula is not included
    in the student-performance input supplied to this agent."

16. Clearly distinguish:
    - confirmed facts
    - numerical observations
    - missing information
    - further analysis required


==================================================
VERIFIED STUDENT PERFORMANCE INFORMATION
==================================================

{verified_summary}


==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these six sections:

1. Student Performance Summary

2. Available Student Data

3. Confirmed Numerical Observations

4. Missing Student Information

5. Areas Requiring Further Analysis

6. Recommendations


==================================================
SECTION 1
==================================================

Student Performance Summary

State:

- registered student count
- available student-record count
- number of records not included in the supplied dataset
- assessment fields available


==================================================
SECTION 2
==================================================

Available Student Data

List the fields available in the student-performance input.


==================================================
SECTION 3
==================================================

Confirmed Numerical Observations

Report the verified statistics exactly.

Include:

- CIE-I average, minimum, maximum and range
- CIE-II average, minimum, maximum and range
- Micro Project average, minimum, maximum and range
- Internal Total average, minimum, maximum and range
- Attendance average, minimum, maximum and range
- Attendance distribution

Do not add interpretations such as good, weak, high,
low or moderate.


==================================================
SECTION 4
==================================================

Missing Student Information

State only information that is not included in the
current student-performance input.

Do not invent missing values.


==================================================
SECTION 5
==================================================

Areas Requiring Further Analysis

Explain what additional verified information would be
needed for deeper analysis.

Do not claim that such information does not exist
elsewhere in the system.


==================================================
SECTION 6
==================================================

Recommendations

Provide recommendations related to:

- data collection
- data validation
- student-performance analysis
- CO attainment analysis
- evidence preparation

Do not invent accreditation requirements.

Do not claim Criterion 3 compliance or non-compliance.


Remember:

Python has already performed the numerical calculations.

Your job is to organize and explain the verified results,
not to perform arithmetic or create accreditation evidence.
"""


    # --------------------------------------------------------
    # Call Model Client
    # --------------------------------------------------------

    return call_model(
        prompt=prompt,
        max_output_tokens=3000,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )


# ============================================================
# 5. CRITERION 4 STUDENT PERFORMANCE & PROGRESSION ANALYSIS
# ============================================================

def analyze_criterion4_student_performance(
    data: dict,
    mock_response: str = None
) -> str:
    """
    Analyze verified student performance, academic progression,
    and placement/achievement information for NBA Criterion 4.

    Python calculates exact progression rates, placement percentages,
    and achievement categories deterministically.
    The LLM organizes and explains the verified findings.
    """
    if not data:
        data = {}

    cohort_records = data.get("cohorts", [])
    placement_records = data.get("placements", [])
    achievement_records = data.get("achievements", [])

    # 1. Deterministic Python Calculations
    progression_stats = calculate_criterion4_progression_metrics(cohort_records)
    placement_stats = calculate_criterion4_placement_metrics(placement_records)
    achievement_stats = summarize_student_achievements(achievement_records)

    # 2. Identify missing fields
    missing_indicators = []
    if not cohort_records:
        missing_indicators.append("Cohort progression records not provided")
    if not placement_records:
        missing_indicators.append("Placement/higher studies records not provided")
    if not achievement_records:
        missing_indicators.append("Student achievements/activities not provided")
    if data.get("competitive_exams") is None:
        missing_indicators.append("Competitive exams (GATE/CAT/GRE) data not provided")

    verified_summary = {
        "progression_metrics": progression_stats,
        "placement_metrics": placement_stats,
        "achievement_metrics": achievement_stats,
        "missing_indicators": missing_indicators,
        "institution_program": data.get("program", "Not specified"),
        "academic_years_covered": data.get("academic_years_covered", [])
    }

    prompt = f"""
You are the Student Performance Analysis Agent in an
AI-Driven NBA Accreditation Readiness System.

Your responsibility is to analyze VERIFIED student performance,
progression, placement, and achievement information for NBA Criterion 4.

The information below has already been calculated deterministically by Python.
Python is the sole source of truth for all numbers.

==================================================
STRICT DATA INTEGRITY RULES
==================================================

1. Use ONLY the verified metrics and information supplied below.
2. DO NOT recalculate any statistics.
3. DO NOT change any numerical value.
4. DO NOT invent:
   - student names, USNs, or registration IDs
   - completion counts or graduation rates
   - placement numbers, company names, or salary figures
   - student awards or achievements
   - NBA marks, benchmarks, or compliance judgments
5. Clearly distinguish verified records from pending/unverified records.
6. Do not describe results as 'good', 'poor', 'impressive', or 'satisfactory'
   unless explicitly evaluated against official institutional thresholds.
7. If data for a category is missing, explicitly list it as missing.

==================================================
VERIFIED CRITERION 4 INFORMATION
==================================================

{verified_summary}

==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY these five sections:

SECTION 1
Academic Progression and Completion
Report cohort-wise and aggregate completion rates (with and without backlogs).
Preserve numerical percentages exactly.

SECTION 2
Placements, Higher Studies, and Entrepreneurship
Report year-wise and aggregate placement, higher education, and entrepreneurship counts and percentages.
Report median salary if supplied, or state it as not supplied.

SECTION 3
Student Achievements and Professional Activities
Report total achievements, breakdown by category, and verification status.

SECTION 4
Data Quality and Evidence Limitations
List missing indicators, unverified entries, and data gaps.

SECTION 5
Recommendations for Accreditation Evidence
Provide factual, actionable recommendations for collecting and verifying required evidence documents.
Do not claim compliance or non-compliance.
"""

    return call_model(
        prompt=prompt,
        max_output_tokens=3000,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )