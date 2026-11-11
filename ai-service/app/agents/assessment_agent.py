from data.criterion3_data import criterion3_data
from app.services.model_client import call_model


# ============================================================
# 3. PREPARE ASSESSMENT-ONLY DATA
# ============================================================

def get_assessment_data():
    """
    Prepare only the information required by the
    Assessment Agent.

    Student-level records are intentionally excluded because
    they are handled by the Student Agent.
    """

    assessment_data = {
        "course": criterion3_data["course"],

        "course_outcomes": criterion3_data["course_outcomes"],

        "assessment_scheme": criterion3_data["assessment_scheme"],

        "micro_project": criterion3_data["micro_project"],

        "co_po_pso_mapping": criterion3_data["co_po_pso_mapping"],

        "assessment_co_mapping": (
            criterion3_data["assessment_co_mapping"]
        ),

        "grade_distribution": (
            criterion3_data["grade_distribution"]
        ),

        "data_quality": (
            criterion3_data["data_quality"]
        )
    }

    return assessment_data


# ============================================================
# 4. ASSESSMENT ANALYSIS FUNCTION
# ============================================================

def analyze_assessment(data=None, mock_response=None):
    """
    Analyze Criterion 3 assessment information.

    The Assessment Agent:
    - summarizes the assessment scheme
    - reports assessment-to-CO coverage
    - reports CO-PO-PSO mapping
    - reports course-level grade information
    - identifies explicitly documented data limitations

    It does NOT:
    - calculate CO attainment
    - calculate PO attainment
    - invent marks
    - invent mappings
    - make compliance judgments
    """

    # --------------------------------------------------------
    # Use compact assessment-only data
    # --------------------------------------------------------

    if data is None:
        data = get_assessment_data()


    # ========================================================
    # 5. PROMPT
    # ========================================================

    prompt = f"""
You are the Assessment Analysis Agent in an
NBA Accreditation Readiness System.

Your task is to analyze the supplied assessment information
for Criterion 3.

Use ONLY the data supplied below.

Do not use outside knowledge.

Do not invent information.


==================================================
SUPPLIED ASSESSMENT DATA
==================================================

{data}


==================================================
STRICT DATA INTEGRITY RULES
==================================================

1. Use only the supplied data.

2. Never invent:

   - marks
   - student records
   - CO attainment
   - PO attainment
   - formulas
   - thresholds
   - targets
   - mappings
   - assessment results
   - missing documents

3. Do not calculate CO attainment unless an official
   formula and all required data are explicitly supplied.

4. Do not calculate PO attainment unless an official
   formula and all required data are explicitly supplied.

5. Do not invent an attainment formula.

6. Do not interpret assessment marks as student-obtained
   marks when they represent maximum marks.

7. Clearly distinguish:

   - assessment maximum marks
   - assessment weightage
   - course-level grade information
   - student-level marks

8. Do not claim that Criterion 3 is compliant.

9. Do not claim that Criterion 3 is non-compliant.

10. Do not use unsupported evaluative words such as:

    - good
    - bad
    - strong
    - weak
    - poor
    - high
    - low
    - moderate
    - effective
    - ineffective

    unless the supplied data explicitly supports that
    interpretation using an official benchmark or threshold.

11. Do not infer that something is missing simply because
    it is not mentioned.

12. Report something as missing or unavailable only when
    the supplied data explicitly identifies it as:

    - missing
    - unavailable
    - not provided
    - not supplied
    - not calculated
    - not included

13. Do not make claims about data errors unless an error is
    explicitly demonstrated in the supplied data.

14. Do not perform calculations that are not already present
    in the supplied data.

15. Preserve all numerical values exactly as supplied.

16. Do not expose student names, USNs, phone numbers,
    or other personally identifiable information.

17. Student-level records are handled by the Student Agent.
    Do not reproduce individual student records here.

18. If the data contains a data-quality flag, report the
    flag factually without creating a new interpretation.

19. Do not claim that the available information is the
    complete Criterion 3 evidence unless explicitly stated.


==================================================
IMPORTANT SCOPE DISTINCTION
==================================================

The Assessment Agent is responsible for assessment-level
information.

The Student Agent is responsible for student-level
performance information.

Do not attempt to replace the Student Agent's analysis.


==================================================
OUTPUT FORMAT
==================================================

Return exactly these six sections:


SECTION 1

Assessment Scheme

Report:

- course name
- course code
- semester
- credits
- academic year
- CIE-I marks and weightage
- CIE-II marks and weightage
- Micro Project marks and weightage
- SEE marks and weightage
- total marks


SECTION 2

Course Outcomes and Assessment Coverage

Report:

- CO1
- CO2
- CO3
- CO4

Then report the supplied assessment-to-CO coverage.

Do not invent mappings.


SECTION 3

Micro Project Assessment

Report the supplied Micro Project rubric.

Preserve the supplied marks exactly.


SECTION 4

CO-PO-PSO Mapping

Report the supplied CO-PO-PSO mapping.

Do not calculate any new values.


SECTION 5

Course-Level Grade Information

Report the supplied:

- registered count
- appeared count
- passed count
- pass percentage
- grade distribution

Clearly identify this as course-level information.

Do not confuse it with student-level records handled
by the Student Agent.


SECTION 6

Data Availability and Limitations

Report only limitations explicitly present in the supplied
data.

Examples may include:

- difference between course-level student count and
  available student-level records
- question-level student marks unavailable
- official CO attainment formula unavailable
- official PO attainment formula unavailable

Do not invent additional missing information.

Do not claim compliance or non-compliance.
"""


    # ========================================================
    # 6. CALL MODEL CLIENT
    # ========================================================

    return call_model(
        prompt=prompt,
        max_output_tokens=2500,
        model="openai/gpt-oss-20b",
        reasoning_effort="low",
        mock_response=mock_response
    )