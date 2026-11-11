"""
tests/test_nba_2026_rules.py

Comprehensive tests for NBA Manual for UG Engineering Tier I — 2026 Edition:
  - Deterministic evaluation rules for Criteria 3, 4, 5, and 6
  - Strict boundary ambiguity handling (NEEDS_RULE_CLARIFICATION)
  - Missing and zero data handling (WARNING / NOT_APPLICABLE)
  - Legacy rule backward compatibility
  - Context aggregation service (criteria_context_service)
  - Agent client endpoint registry
"""

import pytest
from sqlalchemy.orm import Session

from app.business_rules.readiness_rules import (
    RequirementStatus,
    evaluate_requirement,
    load_all_rules,
)
from app.business_rules.criterion3_rules import (
    RULE_CO_COMPLETENESS,
    RULE_COPO_MAPPING,
    RULE_SEE_QUESTION_PAPER,
    RULE_INDUSTRIAL_TRAINING,
    RULE_PROJECT_EVALUATION,
    RULE_SDG,
    RULE_CO_ATTAINMENT,
    RULE_PO_PSO_ATTAINMENT,
    evaluate_co_completeness,
    evaluate_copo_mapping,
    evaluate_see_question_paper,
    evaluate_industrial_training,
    evaluate_project_evaluation,
    evaluate_sdg_evidence,
    evaluate_co_attainment,
    evaluate_po_pso_attainment,
)
from app.business_rules.criterion4_rules import (
    RULE_ENROLMENT_RATIO,
    RULE_SUCCESS_RATE,
    RULE_FIRST_YEAR_API,
    RULE_PLACEMENT,
    RULE_PROFESSIONAL_ACTIVITIES,
    RULE_PASS_PERCENTAGE,
    evaluate_enrolment_ratio,
    evaluate_success_rate,
    evaluate_first_year_api,
    evaluate_placement,
    evaluate_professional_activities,
    evaluate_pass_percentage,
)
from app.business_rules.criterion5_rules import (
    RULE_SFR,
    RULE_FQI,
    RULE_CADRE,
    RULE_VISITING,
    RULE_RETENTION,
    RULE_FACULTY_QUALIFICATION,
    evaluate_sfr,
    evaluate_fqi,
    evaluate_faculty_cadre,
    evaluate_visiting_faculty,
    evaluate_faculty_retention,
    evaluate_faculty_qualification,
)
from app.business_rules.criterion6_rules import (
    RULE_MEMBERSHIPS,
    RULE_RESOURCE_PERSONS,
    RULE_FDP_PARTICIPATION,
    RULE_MOOC_CERT,
    RULE_FDP_ORGANIZED,
    RULE_STUDENT_INNOVATION,
    RULE_RESEARCH_PUBS,
    RULE_PHD_STUDENTS,
    RULE_DEVELOPMENT,
    RULE_SPONSORED,
    RULE_CONSULTANCY,
    RULE_SEED_MONEY,
    RULE_LAB_FACILITY,
    evaluate_professional_memberships,
    evaluate_resource_persons,
    evaluate_fdp_participation,
    evaluate_mooc_certification,
    evaluate_fdp_organized,
    evaluate_student_innovation,
    evaluate_research_publications,
    evaluate_phd_students,
    evaluate_development_activities,
    evaluate_sponsored_research,
    evaluate_consultancy_work,
    evaluate_seed_money,
    evaluate_lab_facility,
)
from app.services.agent_client import (
    AVAILABLE_AI_ENDPOINTS,
    _CRITERION_ENDPOINTS,
    register_criterion_endpoint,
    enable_all_criteria_endpoints,
    disable_criteria_endpoints,
)
from app.services.criteria_context_service import (
    get_c3_context,
    get_c4_context,
    get_c5_context,
    get_c6_context,
)

# Ensure all rules are loaded in the registry
load_all_rules()


# ===========================================================================
# 1. CRITERION 3 TESTS
# ===========================================================================

class TestCriterion3Rules:
    """Test Criterion 3 deterministic rules and ambiguity handling."""

    def test_co_completeness_pass(self):
        res = evaluate_co_completeness({"total_subjects": 10, "subjects_with_cos": 10})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 10.0

    def test_copo_mapping_pass(self):
        res = evaluate_copo_mapping({"total_cos": 20, "cos_with_po_map": 20})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 10.0

    def test_co_attainment_requires_clarification_when_unconfigured(self):
        """NBA mandates institutional CO attainment formula; unconfigured returns clarification."""
        res = evaluate_co_attainment({"attainment_formula_configured": False})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION
        assert "institutional clarification" in res.limitations[0].lower()

    def test_co_attainment_scores_when_configured(self):
        res = evaluate_co_attainment({
            "attainment_formula_configured": True,
            "attainment_score": 22.0,
        })
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 22.0

    def test_po_pso_attainment_requires_clarification_when_unconfigured(self):
        res = evaluate_po_pso_attainment({"attainment_formula_configured": False})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION

    def test_sdg_evidence_qualitative(self):
        res = evaluate_sdg_evidence({"reviewer_score": 8.5})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 8.5
        assert res.max_score == 10.0

    def test_industrial_training_max_10(self):
        res = evaluate_industrial_training({"reviewer_score": 12.0})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 10.0
        assert res.max_score == 10.0

    def test_project_evaluation_max_20(self):
        res = evaluate_project_evaluation({"reviewer_score": 18.0})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 18.0
        assert res.max_score == 20.0


# ===========================================================================
# 2. CRITERION 4 TESTS
# ===========================================================================

class TestCriterion4Rules:
    """Test Criterion 4 deterministic rules: ER, SR, API, Placement."""

    def test_enrolment_ratio_bands(self):
        # >= 90% -> 20 marks
        res = evaluate_enrolment_ratio({
            "years": [
                {"N1": 95, "N4": 0, "N": 100},
                {"N1": 92, "N4": 0, "N": 100},
                {"N1": 90, "N4": 0, "N": 100},
            ]
        })
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 20.0

        # >= 70% -> 14 marks
        res70 = evaluate_enrolment_ratio({
            "years": [
                {"N1": 75, "N4": 0, "N": 100},
                {"N1": 70, "N4": 0, "N": 100},
                {"N1": 72, "N4": 0, "N": 100},
            ]
        })
        assert res70.score_attained == 14.0

    def test_success_rate_formula(self):
        res = evaluate_success_rate({
            "batches": [
                {"A": 100, "B": 80, "N": 100, "N2": 10},
                {"A": 100, "B": 85, "N": 100, "N2": 10},
                {"A": 100, "B": 90, "N": 100, "N2": 10},
            ]
        })
        # Denominator max(100, 110) = 110. SRs around 72.7, 77.3, 81.8 -> avg ~ 77.27
        # Points = 1.5 * (77.27 / 10) = 11.59
        assert res.status in (RequirementStatus.PASS.value, RequirementStatus.WARNING.value)
        assert 10.0 <= res.score_attained <= 15.0

    def test_placement_requires_clarification_without_overlap_policy(self):
        res = evaluate_placement({"overlap_policy_configured": False})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION
        assert "double-counting" in res.limitations[0]

    def test_placement_scores_with_overlap_policy(self):
        res = evaluate_placement({
            "overlap_policy_configured": True,
            "years": [
                {"X": 50, "Y": 20, "Z": 10, "FS": 100, "N": 100, "N2": 0},
            ]
        })
        assert res.status == RequirementStatus.PASS.value
        # (80/100)*100 = 80%; Points = 0.3 * 80 = 24 -> max_score 30.0
        assert res.score_attained == 24.0
        assert res.max_score == 30.0

    def test_professional_activities_capped_at_25(self):
        res = evaluate_professional_activities({"reviewer_score": 28.0})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 25.0
        assert res.max_score == 25.0

    def test_legacy_pass_percentage_preserved(self):
        res = evaluate_pass_percentage({"registered_students": 50, "passed_students": 45})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 18.0


# ===========================================================================
# 3. CRITERION 5 TESTS
# ===========================================================================

class TestCriterion5Rules:
    """Test Criterion 5 deterministic rules: SFR, FQI, Cadre, Visiting, Retention."""

    def test_sfr_normal_bands(self):
        # SFR = 14.0 (< 15) -> 30 marks
        res = evaluate_sfr({"years": [{"S": 140, "TF": 10}]})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 30.0

        # SFR = 18.0 (< 19) -> 24 marks
        res18 = evaluate_sfr({"years": [{"S": 180, "TF": 10}]})
        assert res18.score_attained == 24.0

    def test_sfr_exact_boundary_requires_clarification(self):
        """SFR = exactly 15.0, 17.0, 19.0, 21.0, 23.0, 25.0 must return NEEDS_RULE_CLARIFICATION."""
        for boundary in [15.0, 17.0, 19.0, 21.0, 23.0, 25.0]:
            res = evaluate_sfr({"years": [{"S": int(boundary * 10), "TF": 10}]})
            assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION
            assert "strict inequalities" in res.limitations[0]

    def test_sfr_above_25_fails(self):
        res = evaluate_sfr({"years": [{"S": 260, "TF": 10}]})
        assert res.status == RequirementStatus.FAIL.value
        assert res.score_attained == 0.0

    def test_fqi_formula(self):
        # X=4 PhD, Y=6 MTech, S=200 -> RF = 200/20 = 10
        # FQI = 2.5 * [(10*4 + 4*6) / 10] = 2.5 * [64 / 10] = 16.0 (WARNING since < 17.5 out of 25)
        res = evaluate_fqi({"X": 4, "Y": 6, "S": 200})
        assert res.status == RequirementStatus.WARNING.value
        assert res.score_attained == 16.0
        assert res.max_score == 25.0

        # X=5 PhD, Y=5 MTech -> FQI = 2.5 * 7.0 = 17.5 (PASS since >= 17.5)
        res_pass = evaluate_fqi({"X": 5, "Y": 5, "S": 200})
        assert res_pass.status == RequirementStatus.PASS.value
        assert res_pass.score_attained == 17.5

    def test_cadre_zero_professors_and_assoc_professors_fails(self):
        """NBA rule: if AF1=AF2=0, score = 0."""
        res = evaluate_faculty_cadre({"AF1": 0, "AF2": 0, "AF3": 10, "S": 200})
        assert res.status == RequirementStatus.FAIL.value
        assert res.score_attained == 0.0

    def test_retention_boundary_clarification(self):
        """Unresolved boundary year counts (B, C, D > 0) return NEEDS_RULE_CLARIFICATION."""
        res = evaluate_faculty_retention({
            "A": 0, "B": 2, "C": 0, "D": 0, "E": 8, "S": 200,
            "boundary_resolved": False,
        })
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION

    def test_retention_resolved_scores(self):
        res = evaluate_faculty_retention({
            "A": 0, "B": 2, "C": 2, "D": 2, "E": 4, "S": 200,
            "boundary_resolved": True,
        })
        # numerator = 0*0 + 2*1 + 2*2 + 2*3 + 4*4 = 2 + 4 + 6 + 16 = 28
        # RF = 200/20 = 10; FR = (28/10)*2.5 = 7.0
        assert res.score_attained == 7.0
        assert res.max_score == 10.0

    def test_fqi_higher_marks_cap_25(self):
        # X=8 PhD, Y=5 MTech, S=200 -> RF = 10
        # FQI = 2.5 * [(10*8 + 4*5) / 10] = 2.5 * 10 = 25.0
        res = evaluate_fqi({"X": 8, "Y": 5, "S": 200})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 25.0
        assert res.max_score == 25.0

    def test_retention_capped_at_10(self):
        # High retention: 10 faculty with 4+ years -> E=10, RF=10
        # FR = (40 / 10) * 2.50 = 10.0
        res = evaluate_faculty_retention({
            "A": 0, "B": 0, "C": 0, "D": 0, "E": 10, "S": 200,
            "boundary_resolved": True,
        })
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 10.0
        assert res.max_score == 10.0


# ===========================================================================
# 4. CRITERION 6 TESTS
# ===========================================================================

class TestCriterion6Rules:
    """Test Criterion 6 deterministic rules: Research, Patents, Projects, FDPs."""

    def test_resource_persons_boundary_clarification(self):
        # Avg = exactly 2.0 or 3.0 -> NEEDS_RULE_CLARIFICATION
        res = evaluate_resource_persons({"yearly_count": [2, 2, 2]})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION

        # Avg = 4.0 (>3) -> 5 marks
        res4 = evaluate_resource_persons({"yearly_count": [4, 4, 4]})
        assert res4.status == RequirementStatus.PASS.value
        assert res4.score_attained == 5.0

    def test_sponsored_research_boundary_clarification(self):
        # Exact boundary Rs. 20.0 Lakhs -> clarification
        res = evaluate_sponsored_research({"total_grant_lakhs": 20.0, "boundary_resolved": False})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION

        # Above Rs. 20.0 Lakhs -> 15 marks
        res25 = evaluate_sponsored_research({"total_grant_lakhs": 25.0})
        assert res25.status == RequirementStatus.PASS.value
        assert res25.score_attained == 15.0

    def test_seed_money_gap_clarification(self):
        # Rs. 1.5 Lakhs falls in 1L-2L gap (unspecified in NBA manual)
        res = evaluate_seed_money({"received_lakhs": 1.5, "boundary_resolved": False})
        assert res.status == RequirementStatus.NEEDS_RULE_CLARIFICATION

    def test_fdp_organized_qualifying_filter(self):
        """Only programs with duration_days >= 5 qualify."""
        programs = [
            {"duration_days": 5, "year": 2024},
            {"duration_days": 6, "year": 2024},
            {"duration_days": 2, "year": 2024},  # Should NOT count
        ]
        res = evaluate_fdp_organized({"programs": programs})
        # 2 programs * 2 points = 4 points
        assert res.score_attained == 4.0

    def test_legacy_lab_facility_preserved(self):
        res = evaluate_lab_facility({"labs_required": 5, "labs_available": 5})
        assert res.status == RequirementStatus.PASS.value
        assert res.score_attained == 20.0


# ===========================================================================
# 5. AGENT CLIENT & CONTEXT SERVICE TESTS
# ===========================================================================

class TestAgentClientAndContextService:
    """Test registry and context aggregation functions."""

    def test_agent_client_available_endpoints(self):
        assert "CRITERION_3" in AVAILABLE_AI_ENDPOINTS
        assert "CRITERION_4" in AVAILABLE_AI_ENDPOINTS
        assert "CRITERION_5" in AVAILABLE_AI_ENDPOINTS
        assert "CRITERION_6" in AVAILABLE_AI_ENDPOINTS
        assert "INSPECTION" in AVAILABLE_AI_ENDPOINTS
        assert "REPORT" in AVAILABLE_AI_ENDPOINTS
        assert "COMPLIANCE" in AVAILABLE_AI_ENDPOINTS
        assert "DOCUMENT_QUERY" in AVAILABLE_AI_ENDPOINTS

    def test_agent_client_dynamic_endpoint_registration(self):
        # Verify register and disable helpers
        register_criterion_endpoint("CRITERION_4", "/criterion4/analyze")
        assert _CRITERION_ENDPOINTS["CRITERION_4"] == "/criterion4/analyze"
        disable_criteria_endpoints("CRITERION_4")
        assert _CRITERION_ENDPOINTS["CRITERION_4"] is None

    def test_criteria_context_service_aggregators(self, db_session: Session):
        c3 = get_c3_context(db_session, department="CSE")
        assert "total_subjects" in c3
        assert "cos_with_po_map" in c3

        c4 = get_c4_context(db_session, department="CSE")
        assert "registered_students" in c4
        assert "passed_students" in c4

        c5 = get_c5_context(db_session, department="CSE")
        assert "total_faculty" in c5
        assert "X" in c5
        assert "Y" in c5

        c6 = get_c6_context(db_session, department="CSE")
        assert "publication_count" in c6
        assert "total_grant_lakhs" in c6


# ===========================================================================
# 6. OFFICIAL NBA 2026 MANUAL CRITERIA WEIGHTAGES & TOTALS
# ===========================================================================

class TestNBA2026CriteriaSeedTotals:
    """Verify criteria totals and sub-criterion weightages match official NBA 2026 manual."""

    def test_criteria_max_marks_and_weightages(self):
        from app.db.seed_phase4 import CRITERIA_SEED

        criteria_map = {c["code"]: c for c in CRITERIA_SEED}

        # Criterion 3: Total 120 marks
        c3 = criteria_map["CRITERION_3"]
        assert c3["max_marks"] == 120.0
        mandatory_c3 = sum(r["weightage"] for r in c3["requirements"] if r.get("is_mandatory", True))
        assert mandatory_c3 == 120.0

        # Criterion 4: Total 120 marks (4.1=20, 4.2=15, 4.3=10, 4.4=10, 4.5=10, 4.6=30, 4.7=25)
        c4 = criteria_map["CRITERION_4"]
        assert c4["max_marks"] == 120.0
        c4_weightage = sum(r["weightage"] for r in c4["requirements"])
        assert c4_weightage == 120.0
        c4_req_map = {r["code"]: r["weightage"] for r in c4["requirements"]}
        assert c4_req_map["REQ_4_1"] == 20.0
        assert c4_req_map["REQ_4_2"] == 15.0
        assert c4_req_map["REQ_4_3"] == 10.0
        assert c4_req_map["REQ_4_4"] == 10.0
        assert c4_req_map["REQ_4_5"] == 10.0
        assert c4_req_map["REQ_4_6"] == 30.0
        assert c4_req_map["REQ_4_7"] == 25.0

        # Criterion 5: Total 100 marks (5.1=30, 5.2=25, 5.3=25, 5.4=10, 5.5=10)
        c5 = criteria_map["CRITERION_5"]
        assert c5["max_marks"] == 100.0
        c5_weightage = sum(r["weightage"] for r in c5["requirements"])
        assert c5_weightage == 100.0
        c5_req_map = {r["code"]: r["weightage"] for r in c5["requirements"]}
        assert c5_req_map["REQ_5_1"] == 30.0
        assert c5_req_map["REQ_5_2"] == 25.0
        assert c5_req_map["REQ_5_3"] == 25.0
        assert c5_req_map["REQ_5_4"] == 10.0
        assert c5_req_map["REQ_5_5"] == 10.0

        # Criterion 6: Total 120 marks (6.1=60, 6.2=60)
        c6 = criteria_map["CRITERION_6"]
        assert c6["max_marks"] == 120.0
        mandatory_c6 = sum(r["weightage"] for r in c6["requirements"] if r.get("is_mandatory", True))
        assert mandatory_c6 == 120.0
