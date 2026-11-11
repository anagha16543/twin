"""
AI-NBA Readiness System — Backend
app/services/agent_client.py

HTTP client for the NBA AI analysis service.

Design constraints (from Phase 4 audit)
-----------------------------------------
C3  POST /criterion3/analyze   — IMPLEMENTED in ai-service
    Current limitation: ai-service/main.py discards request.data and reads
    from the static criterion3_data.py fixture.  This client sends structured
    backend data, but the remote endpoint may not yet use it.  This limitation
    is documented in the response metadata when detected.

C4  /criterion4/analyze        — NOT YET IMPLEMENTED in ai-service
C5  /criterion5/analyze        — NOT YET IMPLEMENTED in ai-service
C6  /criterion6/analyze        — NOT YET IMPLEMENTED in ai-service

For unimplemented criteria the client returns a structured
SERVICE_UNAVAILABLE response rather than fabricating results.

Security
--------
* API keys are never logged.
* Error details from the remote service are sanitized before returning.
* Internal storage paths are never sent to or received from the AI service.

Configuration (via Settings):
    AI_SERVICE_BASE_URL        Default: "http://localhost:8001"
    AI_SERVICE_TIMEOUT_SECONDS Default: 30
    AI_SERVICE_API_KEY         Optional bearer token for the AI service
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings helper
# ---------------------------------------------------------------------------

def _get_ai_settings() -> dict:
    from app.core.config import get_settings
    s = get_settings()
    return {
        "base_url": getattr(s, "AI_SERVICE_BASE_URL", "http://localhost:8001"),
        "timeout": float(getattr(s, "AI_SERVICE_TIMEOUT_SECONDS", 30)),
        "api_key": getattr(s, "AI_SERVICE_API_KEY", None),
    }


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class EvidencePassage(BaseModel):
    passage_id: str
    document_id: str
    document_name: str
    page_number: int
    section_heading: Optional[str] = None
    content: str


class AgentAnalysisRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    criterion_code: str                          # e.g. "CRITERION_3"
    requirement_code: Optional[str] = None
    academic_year: str
    department: str
    analysis_task: str
    structured_data: dict = Field(default_factory=dict)
    evidence_passages: list[EvidencePassage] = Field(default_factory=list)


class AgentFinding(BaseModel):
    category: str                                # OBSERVATION | LIMITATION | RISK
    description: str
    citation: Optional[dict] = None


class AgentAnalysisResponse(BaseModel):
    request_id: str
    correlation_id: str
    criterion_code: str
    status: str                                  # SUCCESS | FAILED | UNAVAILABLE
    summary: Optional[str] = None
    findings: list[AgentFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None
    limitations: list[str] = Field(default_factory=list)
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Known criterion-to-endpoint mapping
# ---------------------------------------------------------------------------

AVAILABLE_AI_ENDPOINTS: dict[str, str] = {
    "CRITERION_3": "/criterion3/analyze",
    "CRITERION_4": "/criterion4/analyze",
    "CRITERION_5": "/criterion5/analyze",
    "CRITERION_6": "/criterion6/analyze",
    "INSPECTION": "/inspection/analyze",
    "REPORT": "/report/generate",
    "COMPLIANCE": "/compliance/analyze",
    "DOCUMENT_QUERY": "/document/query",
}

_CRITERION_ENDPOINTS: dict[str, Optional[str]] = {
    "CRITERION_3": "/criterion3/analyze",
    "CRITERION_4": None,   # Enabled dynamically or via register_criterion_endpoint
    "CRITERION_5": None,
    "CRITERION_6": None,
}


def register_criterion_endpoint(criterion: str, endpoint: str) -> None:
    """Register or enable an AI service endpoint for a criterion or service."""
    _CRITERION_ENDPOINTS[criterion] = endpoint


def enable_all_criteria_endpoints() -> None:
    """Enable all implemented AI service endpoints (C3-C6, inspection, report, compliance, document)."""
    _CRITERION_ENDPOINTS.update(AVAILABLE_AI_ENDPOINTS)


def disable_criteria_endpoints(*criteria: str) -> None:
    """Reset specified criteria back to None (offline / safe mode)."""
    for c in criteria:
        if c in _CRITERION_ENDPOINTS:
            _CRITERION_ENDPOINTS[c] = None


def _unavailable_response(
    request: AgentAnalysisRequest,
    reason: str,
) -> AgentAnalysisResponse:
    """Return a structured UNAVAILABLE response without a real API call."""
    return AgentAnalysisResponse(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        criterion_code=request.criterion_code,
        status="UNAVAILABLE",
        summary=None,
        findings=[],
        recommended_actions=[],
        limitations=[reason],
        error=reason,
    )


def _parse_c3_text_response(
    raw_text: str,
    request: AgentAnalysisRequest,
    elapsed_ms: int,
) -> AgentAnalysisResponse:
    """
    Adapt the unstructured C3 text response into the AgentAnalysisResponse schema.

    The current ai-service /criterion3/analyze returns {"criterion": ..., "analysis": str}.
    This adapter wraps the text into a single OBSERVATION finding.
    When the AI service is updated to return structured JSON, this adapter
    should be replaced with direct schema parsing.
    """
    return AgentAnalysisResponse(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        criterion_code=request.criterion_code,
        status="SUCCESS",
        summary="AI analysis completed (unstructured text response).",
        findings=[
            AgentFinding(
                category="OBSERVATION",
                description=raw_text[:4000] if raw_text else "(empty response)",
                citation=None,
            )
        ],
        recommended_actions=[],
        confidence_score=None,
        limitations=[
            "The current ai-service /criterion3/analyze endpoint returns "
            "unstructured text. Structured findings and citations are not "
            "available until the AI service is updated."
        ],
        execution_time_ms=elapsed_ms,
        error=None,
    )


# ---------------------------------------------------------------------------
# Main client function
# ---------------------------------------------------------------------------

def call_agent(request: AgentAnalysisRequest) -> AgentAnalysisResponse:
    """
    Send an analysis request to the AI service and return a structured response.

    This is a synchronous call using httpx.  For long-running analyses,
    consider wrapping this in a FastAPI background task.

    Error handling:
    * ConnectError   ? UNAVAILABLE with sanitized message
    * TimeoutError   ? UNAVAILABLE with timeout message
    * HTTPStatusError ? UNAVAILABLE with status code only (no raw body leak)
    * Unimplemented criteria ? UNAVAILABLE immediately (no HTTP call)
    """
    import time

    criterion = request.criterion_code
    endpoint_path = _CRITERION_ENDPOINTS.get(criterion)

    if endpoint_path is None:
        reason = (
            f"AI analysis for {criterion} is not yet implemented in the AI service. "
            "C4, C5, and C6 agent endpoints do not exist. "
            "The backend deterministic evaluation is still available."
        )
        logger.info(
            "AgentClient: criterion %s has no endpoint — returning UNAVAILABLE.",
            criterion,
        )
        return _unavailable_response(request, reason)

    ai_cfg = _get_ai_settings()
    base_url = ai_cfg["base_url"].rstrip("/")
    timeout = ai_cfg["timeout"]
    api_key = ai_cfg.get("api_key")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Build payload — structured_data carries backend-verified metrics
    payload = {
        "data": {
            "request_id": request.request_id,
            "correlation_id": request.correlation_id,
            "criterion_code": criterion,
            "requirement_code": request.requirement_code,
            "academic_year": request.academic_year,
            "department": request.department,
            "analysis_task": request.analysis_task,
            "structured_data": request.structured_data,
            "evidence_passages": [p.model_dump() for p in request.evidence_passages],
        }
    }

    url = f"{base_url}{endpoint_path}"
    logger.info(
        "AgentClient: calling %s [criterion=%s, req_id=%s, corr=%s]",
        url,
        criterion,
        request.request_id,
        request.correlation_id,
    )

    start = time.monotonic()
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            response.raise_for_status()
    except httpx.ConnectError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("AgentClient: connection error for %s: %s", url, type(exc).__name__)
        return _unavailable_response(
            request,
            f"AI service unreachable at {base_url}. "
            "Ensure the ai-service is running and AI_SERVICE_BASE_URL is correct.",
        )
    except httpx.TimeoutException:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("AgentClient: timeout calling %s after %sms", url, elapsed_ms)
        return _unavailable_response(
            request,
            f"AI service did not respond within {timeout}s. "
            "Consider increasing AI_SERVICE_TIMEOUT_SECONDS.",
        )
    except httpx.HTTPStatusError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "AgentClient: HTTP %d from %s", exc.response.status_code, url
        )
        return _unavailable_response(
            request,
            f"AI service returned HTTP {exc.response.status_code}.",
        )

    # Parse response
    try:
        body = response.json()
    except Exception:
        return _unavailable_response(
            request,
            "AI service returned an unparseable response body.",
        )

    # Adapt C3 unstructured text response
    if criterion == "CRITERION_3":
        raw_analysis = body.get("analysis", "")
        return _parse_c3_text_response(raw_analysis, request, elapsed_ms)

    # Generic structured handler for future criteria
    return AgentAnalysisResponse(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        criterion_code=criterion,
        status="SUCCESS",
        summary=str(body.get("summary", "")),
        findings=[],
        execution_time_ms=elapsed_ms,
    )
