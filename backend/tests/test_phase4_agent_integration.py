"""
tests/test_phase4_agent_integration.py

Comprehensive tests for Phase 4 Milestone E (Backend-to-AI-Service Integration):
  - AgentAnalysisRequest construction with correlation IDs and structured data
  - C3 endpoint integration and unstructured text response adapter
  - Service unavailable handling on connection error, timeout, or 500 status
  - Immediate UNAVAILABLE response for unimplemented C4, C5, C6 without fake calls
  - Advisory role of AI: ai_drives_compliance is ALWAYS False
  - AI analysis never overrides or decides deterministic compliance status
  - Role-based authorization for AI analysis (HOD/ADMIN only)
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch
import httpx
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.academic import AcademicYear
from app.models.phase4 import (
    EvaluationMode,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementStatus,
)
from app.services.agent_client import (
    AgentAnalysisRequest,
    EvidencePassage,
    call_agent,
)


class TestAgentClientContract:
    """Test the HTTP client communicating with the AI service."""

    def test_request_payload_and_correlation_ids(self):
        req = AgentAnalysisRequest(
            criterion_code="CRITERION_3",
            academic_year="2026-27",
            department="Computer Science & Engineering",
            analysis_task="Evaluate CO-PO attainment coverage",
            structured_data={"total_subjects": 10, "subjects_with_cos": 10},
            evidence_passages=[
                EvidencePassage(
                    passage_id="p1",
                    document_id="doc1",
                    document_name="syllabus.pdf",
                    page_number=1,
                    content="Syllabus for Data Structures",
                )
            ],
        )
        assert req.request_id is not None
        assert req.correlation_id is not None
        assert req.criterion_code == "CRITERION_3"
        assert len(req.evidence_passages) == 1

    def test_c3_successful_response_adapter(self):
        """Simulate successful response from ai-service /criterion3/analyze."""
        req = AgentAnalysisRequest(
            criterion_code="CRITERION_3",
            academic_year="2026-27",
            department="CSE",
            analysis_task="Analyze attainment",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "criterion": "CRITERION_3",
            "analysis": "Department demonstrates strong alignment of COs with Bloom taxonomy.",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client.post", return_value=mock_resp):
            res = call_agent(req)

        assert res.status == "SUCCESS"
        assert res.criterion_code == "CRITERION_3"
        assert len(res.findings) == 1
        assert "strong alignment" in res.findings[0].description
        assert len(res.limitations) > 0  # Documents unstructured adapter limitation

    def test_c4_c5_c6_return_unavailable_immediately(self):
        """C4, C5, C6 return UNAVAILABLE without fabricating results or calling nonexistent endpoints."""
        for crit in ["CRITERION_4", "CRITERION_5", "CRITERION_6"]:
            req = AgentAnalysisRequest(
                criterion_code=crit,
                academic_year="2026-27",
                department="CSE",
                analysis_task="Evaluate performance",
            )
            # Should not call httpx
            with patch("httpx.Client.post") as mock_post:
                res = call_agent(req)
                mock_post.assert_not_called()

            assert res.status == "UNAVAILABLE"
            assert crit in res.limitations[0]

    def test_connection_error_returns_unavailable(self):
        req = AgentAnalysisRequest(
            criterion_code="CRITERION_3",
            academic_year="2026-27",
            department="CSE",
            analysis_task="Analyze",
        )
        with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
            res = call_agent(req)

        assert res.status == "UNAVAILABLE"
        assert "unreachable" in res.error.lower()

    def test_timeout_returns_unavailable(self):
        req = AgentAnalysisRequest(
            criterion_code="CRITERION_3",
            academic_year="2026-27",
            department="CSE",
            analysis_task="Analyze",
        )
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timeout")):
            res = call_agent(req)

        assert res.status == "UNAVAILABLE"
        assert "timeout" in res.error.lower()

    def test_http_error_returns_unavailable_sanitized(self):
        req = AgentAnalysisRequest(
            criterion_code="CRITERION_3",
            academic_year="2026-27",
            department="CSE",
            analysis_task="Analyze",
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        err = httpx.HTTPStatusError("Bad Gateway", request=MagicMock(), response=mock_resp)

        with patch("httpx.Client.post", side_effect=err):
            res = call_agent(req)

        assert res.status == "UNAVAILABLE"
        assert "502" in res.error


class TestAIAnalysisAPIEndpoint:
    """Test /api/v1/analysis/ai-analysis endpoint permissions and behavior."""

    def test_faculty_cannot_trigger_ai_analysis(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        req = db_session.query(NBARequirement).first()
        year = db_session.query(AcademicYear).first()
        payload = {
            "requirement_id": str(req.id),
            "academic_year_id": str(year.id),
            "department": "CSE",
            "analysis_task": "Evaluate attainment",
        }
        res = db_client.post("/api/v1/analysis/ai-analysis", json=payload, headers=faculty_headers)
        assert res.status_code == 403

    def test_hod_triggers_ai_analysis_advisory_only(
        self, db_client: TestClient, db_session: Session, hod_headers: dict
    ):
        req = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_3_1").first()
        year = db_session.query(AcademicYear).first()

        # Seed an existing evaluation first
        eval_record = RequirementEvaluation(
            requirement_id=req.id,
            academic_year_id=year.id,
            department="CSE",
            status=RequirementStatus.PASS.value,
            score_attained=10.0,
            max_score=10.0,
            mode=EvaluationMode.DETERMINISTIC.value,
        )
        db_session.add(eval_record)
        db_session.commit()

        mock_ai_resp = MagicMock()
        mock_ai_resp.status_code = 200
        mock_ai_resp.json.return_value = {
            "criterion": "CRITERION_3",
            "analysis": "All subjects have defined Course Outcomes.",
        }
        mock_ai_resp.raise_for_status = MagicMock()

        payload = {
            "requirement_id": str(req.id),
            "academic_year_id": str(year.id),
            "department": "CSE",
            "analysis_task": "Analyze curriculum",
        }

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_ai_resp
        mock_client_instance.__enter__.return_value = mock_client_instance

        with patch("app.services.agent_client.httpx.Client", return_value=mock_client_instance):
            res = db_client.post(
                "/api/v1/analysis/ai-analysis",
                json=payload,
                headers=hod_headers,
            )

        assert res.status_code == 200
        data = res.json()
        assert data["ai_drives_compliance"] is False  # MUST BE FALSE
        assert data["status"] == "SUCCESS"

        # Verify underlying requirement status remained PASS (not changed by AI)
        db_session.refresh(eval_record)
        assert eval_record.status == RequirementStatus.PASS.value
        assert eval_record.ai_interpretation is not None

    def test_ai_analysis_unimplemented_criterion_returns_unavailable(
        self, db_client: TestClient, db_session: Session, hod_headers: dict
    ):
        # REQ_4_1 is in Criterion 4
        req = db_session.query(NBARequirement).filter(NBARequirement.code == "REQ_4_1").first()
        year = db_session.query(AcademicYear).first()

        payload = {
            "requirement_id": str(req.id),
            "academic_year_id": str(year.id),
            "department": "CSE",
            "analysis_task": "Analyze placement records",
        }
        res = db_client.post(
            "/api/v1/analysis/ai-analysis",
            json=payload,
            headers=hod_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "UNAVAILABLE"
        assert data["ai_drives_compliance"] is False
        assert "not yet implemented" in data["error"]
