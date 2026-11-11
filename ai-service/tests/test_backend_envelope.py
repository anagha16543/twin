"""Regression: the backend's agent_client envelope must not 400 on /criterion3/analyze."""
import os

os.environ["MOCK_LLM"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_criterion3_accepts_backend_envelope():
    payload = {
        "data": {
            "request_id": "r1",
            "correlation_id": "c1",
            "criterion_code": "CRITERION_3",
            "requirement_code": "REQ_3_7",
            "academic_year": "2026-27",
            "department": "Artificial Intelligence and Machine Learning",
            "analysis_task": "general_analysis",
            "structured_data": {"latest_evaluation_status": "WARNING", "score_attained": 16.5, "max_score": 25.0},
            "evidence_passages": [],
        }
    }
    r = TestClient(app).post("/criterion3/analyze", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["criterion"] == "Criterion 3"
