"""
ai-service/tests/test_agents.py

Comprehensive tests for AI Agents & Services:
  - PII sanitization (privacy_utils)
  - All 8 Agents executing in offline mock mode without external API calls
  - RAG-grounded document query agent with synthetic passages
  - AI Service FastAPI endpoints
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure openai module exists for import
if "openai" not in sys.modules:
    mock_openai = type(sys)("openai")
    mock_openai.OpenAI = MagicMock()
    sys.modules["openai"] = mock_openai

# Add ai-service to path
ai_service_root = Path(__file__).resolve().parents[1]
if str(ai_service_root) not in sys.path:
    sys.path.insert(0, str(ai_service_root))

from app.utils.privacy_utils import (
    SENSITIVE_FACULTY_KEYS,
    sanitize_faculty_record,
    sanitize_faculty_data,
)
from app.agents.assessment_agent import analyze_assessment
from app.agents.student_agent import analyze_student_performance
from app.agents.coordinator_agent import coordinate_criterion3
from app.agents.faculty_agent import analyze_faculty_information, analyze_faculty_contributions
from app.agents.compliance_agent import analyze_compliance_gaps
from app.agents.inspection_agent import run_virtual_inspection_audit
from app.agents.report_agent import generate_inspection_report
from app.agents.document_agent import (
    answer_document_query,
    extract_structured_entities_from_document,
)
from main import app
from fastapi.testclient import TestClient


# ===========================================================================
# 1. PRIVACY SANITIZATION TESTS
# ===========================================================================

class TestPrivacySanitization:
    """Verify strict PII minimization before LLM processing."""

    def test_sensitive_keys_frozenset_present(self):
        assert "phone" in SENSITIVE_FACULTY_KEYS
        assert "email" in SENSITIVE_FACULTY_KEYS
        assert "pan" in SENSITIVE_FACULTY_KEYS
        assert "aadhaar" in SENSITIVE_FACULTY_KEYS
        assert "salary_in_hand" in SENSITIVE_FACULTY_KEYS

    def test_sanitize_faculty_record_removes_pii(self):
        record = {
            "name": "Dr. Alan Turing",
            "designation": "Professor",
            "phone": "+91-9876543210",
            "personal_email": "turing@personal.com",
            "highest_qualification": "Ph.D.",
            "aadhaar": "1234-5678-9012",
        }
        sanitized = sanitize_faculty_record(record)
        assert sanitized["name"] == "Dr. Alan Turing"
        assert sanitized["designation"] == "Professor"
        assert sanitized["highest_qualification"] == "Ph.D."
        assert "phone" not in sanitized
        assert "personal_email" not in sanitized
        assert "aadhaar" not in sanitized

        # Original dict must NOT be mutated
        assert "phone" in record

    def test_sanitize_faculty_data_list(self):
        records = [
            {"name": "Prof A", "mobile": "99999", "department": "CSE"},
            {"name": "Prof B", "pan": "ABCDE1234F", "department": "CSE"},
        ]
        sanitized = sanitize_faculty_data(records)
        assert len(sanitized) == 2
        assert "mobile" not in sanitized[0]
        assert "pan" not in sanitized[1]
        assert sanitized[0]["name"] == "Prof A"
        assert "mobile" in records[0]  # Non-mutating


# ===========================================================================
# 2. ALL 8 AGENTS IN MOCK MODE
# ===========================================================================

class TestAllAgentsMockExecution:
    """Verify all 8 agents run cleanly with mock_response."""

    def test_assessment_agent(self):
        resp = analyze_assessment(mock_response="Mock assessment analysis")
        assert "Mock assessment analysis" in resp

    def test_student_agent(self):
        resp = analyze_student_performance(mock_response="Mock student analysis")
        assert "Mock student analysis" in resp

    def test_coordinator_agent(self):
        resp = coordinate_criterion3(
            assessment_analysis="Assessment findings summary",
            student_analysis="Student performance summary",
            mock_response="Mock coordinator synthesis",
        )
        assert "Mock coordinator synthesis" in resp

    def test_faculty_agent_info(self):
        resp = analyze_faculty_information(
            data={"faculty_members": [], "total_enrolled_students": 100},
            mock_response="Mock faculty information analysis",
        )
        assert "Mock faculty information analysis" in resp

    def test_faculty_agent_contributions(self):
        resp = analyze_faculty_contributions(
            data={"publications": [], "patents": []},
            mock_response="Mock faculty contributions analysis",
        )
        assert "Mock faculty contributions analysis" in resp

    def test_compliance_agent(self):
        resp = analyze_compliance_gaps(mock_response="Mock compliance audit")
        assert "Mock compliance audit" in resp

    def test_inspection_agent(self):
        resp = run_virtual_inspection_audit(mock_response="Mock inspection readiness")
        assert "Mock inspection readiness" in resp

    def test_report_agent(self):
        resp = generate_inspection_report(mock_response="Mock comprehensive report")
        assert "Mock comprehensive report" in resp

    def test_document_agent_rag_query(self):
        passages = [
            {
                "document_name": "Course_Syllabus.pdf",
                "page_number": 3,
                "section_heading": "Course Outcomes",
                "content": "CO1: Understand database design principles.",
            }
        ]
        res = answer_document_query(
            query="What is CO1?",
            passages=passages,
            mock_response="According to Course_Syllabus.pdf page 3, CO1 covers database design.",
        )
        assert res["status"] == "success"
        assert len(res["sources"]) == 1
        assert res["sources"][0]["document_name"] == "Course_Syllabus.pdf"
        assert res["chunks_retrieved_count"] == 1
        assert "database design" in res["answer"]

    def test_document_agent_extract_entities(self):
        text = "Course: CS101. CO1: Basics of Computing."
        res = extract_structured_entities_from_document(
            document_text=text,
            mock_response='{"course": "CS101", "CO1": "Basics of Computing"}',
        )
        assert "CS101" in res


# ===========================================================================
# 3. AI SERVICE FASTAPI ENDPOINTS
# ===========================================================================

class TestAIServiceFastAPI:
    """Verify AI service API endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_check(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_document_query_endpoint(self, client):
        payload = {
            "query": "What is the policy?",
            "passages": [
                {
                    "document_name": "Manual.pdf",
                    "page_number": 10,
                    "content": "Attendance policy requires 75% minimum.",
                }
            ],
        }
        # In test environment MOCK_LLM is true or mock response handles it
        import os
        os.environ["MOCK_LLM"] = "true"
        res = client.post("/document/query", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["sources"]) == 1
