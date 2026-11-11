"""
AI-NBA Readiness System — Backend
app/db/seed_phase4.py

Idempotent seed data for NBA Criteria and Requirements (Phase 4).
Aligned with NBA Manual for UG Engineering Tier I — 2026 Edition.

Criteria Overview:
  Criterion 3: Course Outcomes and Program Outcomes (120 marks)
  Criterion 4: Students' Performance (120 marks)
  Criterion 5: Faculty Information (100 marks)
  Criterion 6: Faculty Contributions (120 marks)

Usage:
    python -m app.db.seed_phase4
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Allow running as __main__ from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.phase4 import NBACriterion, NBARequirement

# ---------------------------------------------------------------------------
# Seed data — aligned with NBA UG Engineering Tier I 2026 Edition
# ---------------------------------------------------------------------------

CRITERIA_SEED: list[dict[str, Any]] = [
    {
        "code": "CRITERION_3",
        "name": "Outcome-Based Assessment",
        "description": "Criterion 3 covers Continuous Assessment, SEE question paper evaluation, laboratory/workshop conduct, internships, projects, SDGs, and CO/PO/PSO attainment.",
        "max_marks": 120.0,
        "display_order": 3,
        "requirements": [
            {
                "code": "REQ_3_1",
                "title": "Continuous Assessment (3.1)",
                "description": "Continuous Assessment scheme documentation and implementation.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.co_definition_completeness",
                "display_order": 1,
            },
            {
                "code": "REQ_3_2",
                "title": "SEE Question Paper Evaluation (3.2)",
                "description": "Quality and alignment of Semester End Examination question papers with COs.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.see_question_paper",
                "display_order": 2,
            },
            {
                "code": "REQ_3_3",
                "title": "Laboratory Work and Workshop (3.3)",
                "description": "Documentation and conduct of laboratory/workshop sessions aligned to COs.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.lab_workshop",
                "display_order": 3,
            },
            {
                "code": "REQ_3_4",
                "title": "Industrial Training/Internship (3.4)",
                "description": "Industrial training or internship programs with CO alignment.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.industrial_training",
                "display_order": 4,
            },
            {
                "code": "REQ_3_5",
                "title": "Projects Evaluation (3.5)",
                "description": "Evaluation of projects based on complexity, sustainability, and management.",
                "weightage": 20.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.project_evaluation",
                "display_order": 5,
            },
            {
                "code": "REQ_3_6",
                "title": "Sustainable Development Goals (SDG) (3.6)",
                "description": "Evidence of addressing Sustainable Development Goals in curriculum and projects.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.sdg_evidence",
                "display_order": 6,
            },
            {
                "code": "REQ_3_7",
                "title": "Course Outcome Attainment (3.7)",
                "description": "Measurement and analysis of Course Outcome attainment using direct and indirect tools.",
                "weightage": 25.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.co_attainment_tools",
                "display_order": 7,
            },
            {
                "code": "REQ_3_8",
                "title": "Program Outcome and PSO Attainment (3.8)",
                "description": "Measurement and analysis of Program Outcome and PSO attainment.",
                "weightage": 25.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion3.po_pso_attainment",
                "display_order": 8,
            },
            {
                "code": "REQ_3_COPO",
                "title": "CO-PO Mapping Completeness (Legacy)",
                "description": "Legacy requirement for CO-PO mapping completeness verification.",
                "weightage": 0.0,
                "is_mandatory": False,
                "evaluation_rule_key": "criterion3.copo_mapping_completeness",
                "display_order": 9,
                # Legacy, 0 marks: kept for history but excluded from C3 readiness
                # so the 8 Tier-I sub-criteria (3.1-3.8) form the denominator.
                "is_active": False,
            },
        ],
    },
    {
        "code": "CRITERION_4",
        "name": "Students' Performance",
        "description": "Criterion 4 covers enrolment ratio, success rate without backlogs, academic performance index, placement, and professional activities.",
        "max_marks": 120.0,
        "display_order": 4,
        "requirements": [
            {
                "code": "REQ_4_1",
                "title": "Enrolment Ratio (4.1)",
                "description": "Average enrolment ratio over three years relative to sanctioned intake.",
                "weightage": 20.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.enrolment_ratio",
                "display_order": 1,
            },
            {
                "code": "REQ_4_2",
                "title": "Success Rate without Backlogs (4.2)",
                "description": "Success rate of students completing without backlogs averaged over three batches.",
                "weightage": 15.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.success_rate",
                "display_order": 2,
            },
            {
                "code": "REQ_4_3",
                "title": "Academic Performance (First Year) (4.3)",
                "description": "Academic Performance Index for first-year students.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.first_year_api",
                "display_order": 3,
            },
            {
                "code": "REQ_4_4",
                "title": "Academic Performance (Second Year) (4.4)",
                "description": "Academic Performance Index for second-year students.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.second_year_api",
                "display_order": 4,
            },
            {
                "code": "REQ_4_5",
                "title": "Academic Performance (Third Year) (4.5)",
                "description": "Academic Performance Index for third-year students.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.third_year_api",
                "display_order": 5,
            },
            {
                "code": "REQ_4_6",
                "title": "Placement and Higher Studies (4.6)",
                "description": "Placement, higher studies, and entrepreneurship outcomes over three years.",
                "weightage": 30.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.placement_higher_studies",
                "display_order": 6,
            },
            {
                "code": "REQ_4_7",
                "title": "Professional Activities (4.7)",
                "description": "Professional societies, student participation in events, technical publications.",
                "weightage": 25.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion4.professional_activities",
                "display_order": 7,
            },
        ],
    },
    {
        "code": "CRITERION_5",
        "name": "Faculty Information",
        "description": "Criterion 5 covers student-faculty ratio, faculty qualifications, cadre proportion, visiting faculty, and retention.",
        "max_marks": 100.0,
        "display_order": 5,
        "requirements": [
            {
                "code": "REQ_5_1",
                "title": "Student-Faculty Ratio (5.1)",
                "description": "Average Student-to-Faculty Ratio over three years.",
                "weightage": 30.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion5.student_faculty_ratio",
                "display_order": 1,
            },
            {
                "code": "REQ_5_2",
                "title": "Faculty Qualification Index (5.2)",
                "description": "Faculty Qualification Index based on PhD and MTech/ME qualifications.",
                "weightage": 25.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion5.faculty_qualification_index",
                "display_order": 2,
            },
            {
                "code": "REQ_5_3",
                "title": "Faculty Cadre Proportion (5.3)",
                "description": "Proportion of Professors, Associate Professors, and Assistant Professors relative to required faculty.",
                "weightage": 25.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion5.faculty_cadre_proportion",
                "display_order": 3,
            },
            {
                "code": "REQ_5_4",
                "title": "Visiting/Adjunct/Emeritus Faculty (5.4)",
                "description": "Provision and utilisation of visiting/adjunct/emeritus faculty.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion5.visiting_faculty",
                "display_order": 4,
            },
            {
                "code": "REQ_5_5",
                "title": "Faculty Retention (5.5)",
                "description": "Retention rate of faculty members over a four-year period.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion5.faculty_retention",
                "display_order": 5,
            },
        ],
    },
    {
        "code": "CRITERION_6",
        "name": "Faculty Contributions",
        "description": "Criterion 6 covers professional development, research and development, consultancy, and funded projects.",
        "max_marks": 120.0,
        "display_order": 6,
        "requirements": [
            {
                "code": "REQ_6_1_1",
                "title": "Professional Society Memberships (6.1.1)",
                "description": "Faculty membership in national/international professional bodies.",
                "weightage": 5.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.professional_memberships",
                "display_order": 1,
            },
            {
                "code": "REQ_6_1_2_1",
                "title": "Resource Persons Invited (6.1.2.1)",
                "description": "Average number of resource persons invited per year.",
                "weightage": 5.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.resource_persons",
                "display_order": 2,
            },
            {
                "code": "REQ_6_1_2_2",
                "title": "FDP/STTP Participation (6.1.2.2)",
                "description": "Faculty participation in FDPs and STTPs.",
                "weightage": 5.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.fdp_participation",
                "display_order": 3,
            },
            {
                "code": "REQ_6_1_3",
                "title": "MOOCs Developed (6.1.3)",
                "description": "Number of MOOC courses developed by faculty.",
                "weightage": 7.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.mooc_development",
                "display_order": 4,
            },
            {
                "code": "REQ_6_1_4",
                "title": "MOOC Certification by Students (6.1.4)",
                "description": "Percentage of students completing MOOC certifications.",
                "weightage": 8.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.mooc_certification",
                "display_order": 5,
            },
            {
                "code": "REQ_6_1_5",
                "title": "FDPs/STTPs Organized (6.1.5)",
                "description": "Number of FDPs/STTPs organized by the department.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.fdp_organized",
                "display_order": 6,
            },
            {
                "code": "REQ_6_1_6",
                "title": "Student Innovation Support (6.1.6)",
                "description": "Student participation in innovation, entrepreneurship, and startup activities.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.student_innovation_support",
                "display_order": 7,
            },
            {
                "code": "REQ_6_1_7",
                "title": "Industry Training for Students (6.1.7)",
                "description": "Percentage of students undergoing industry training.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.industry_training",
                "display_order": 8,
            },
            {
                "code": "REQ_6_2_1",
                "title": "Research Publications (6.2.1)",
                "description": "Research publications by faculty in indexed journals.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.research_publications",
                "display_order": 9,
            },
            {
                "code": "REQ_6_2_2",
                "title": "PhD Students Guided (6.2.2)",
                "description": "Number of PhD students enrolled and graduated under faculty supervision.",
                "weightage": 5.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.phd_students",
                "display_order": 10,
            },
            {
                "code": "REQ_6_2_3",
                "title": "Patents and Prototypes (6.2.3)",
                "description": "Patents granted/published and working models/prototypes developed.",
                "weightage": 10.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.development_activities",
                "display_order": 11,
            },
            {
                "code": "REQ_6_2_4",
                "title": "Sponsored Research Projects (6.2.4)",
                "description": "Funded sponsored research projects and total grant amount.",
                "weightage": 15.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.sponsored_research",
                "display_order": 12,
            },
            {
                "code": "REQ_6_2_5",
                "title": "Consultancy Projects (6.2.5)",
                "description": "Consultancy work and revenue generated.",
                "weightage": 15.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.consultancy_work",
                "display_order": 13,
            },
            {
                "code": "REQ_6_2_6",
                "title": "Institutional Seed Money (6.2.6)",
                "description": "Seed money received and utilized for research and innovation.",
                "weightage": 5.0,
                "is_mandatory": True,
                "evaluation_rule_key": "criterion6.seed_money",
                "display_order": 14,
            },
            {
                "code": "REQ_6_1",
                "title": "Laboratory Facility Availability (Legacy)",
                "description": "Legacy placeholder for laboratory facilities. Criterion 6 in NBA 2026 is Faculty Contributions.",
                "weightage": 0.0,
                "is_mandatory": False,
                "evaluation_rule_key": "criterion6.lab_facility_availability",
                "display_order": 15,
            },
        ],
    },
]


def seed_phase4(db: Session) -> None:
    """
    Idempotently seed NBA Criteria and Requirements.

    - Existing records (matched by code) are updated with current metadata.
    - New criteria/requirements are inserted.
    - Safe to run multiple times.
    """
    for item in CRITERIA_SEED:
        criterion_data = dict(item)
        req_data = criterion_data.pop("requirements", [])

        existing_criterion = (
            db.query(NBACriterion)
            .filter(NBACriterion.code == criterion_data["code"])
            .first()
        )
        if existing_criterion is None:
            criterion = NBACriterion(**criterion_data)
            db.add(criterion)
            db.flush()
        else:
            criterion = existing_criterion
            criterion.name = criterion_data["name"]
            criterion.description = criterion_data["description"]
            criterion.max_marks = criterion_data["max_marks"]
            criterion.display_order = criterion_data["display_order"]

        for req in req_data:
            existing_req = (
                db.query(NBARequirement)
                .filter(NBARequirement.code == req["code"])
                .first()
            )
            if existing_req is None:
                requirement = NBARequirement(criterion_id=criterion.id, **req)
                db.add(requirement)
            else:
                existing_req.criterion_id = criterion.id
                existing_req.title = req["title"]
                existing_req.description = req["description"]
                existing_req.weightage = req["weightage"]
                existing_req.evaluation_rule_key = req["evaluation_rule_key"]
                existing_req.display_order = req["display_order"]
                existing_req.is_mandatory = req.get("is_mandatory", True)
                existing_req.is_active = req.get("is_active", True)

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_phase4(db)
        print("Phase 4 seed completed successfully.")
    finally:
        db.close()
