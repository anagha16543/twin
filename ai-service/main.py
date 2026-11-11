# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

import copy

from app.agents.assessment_agent import analyze_assessment, get_assessment_data
from data.criterion3_data import criterion3_data
from app.agents.student_agent import analyze_student_performance
from app.agents.coordinator_agent import coordinate_criterion3
from app.agents.faculty_agent import analyze_faculty_information, analyze_faculty_contributions
from app.agents.compliance_agent import analyze_compliance_gaps
from app.agents.inspection_agent import run_virtual_inspection_audit
from app.agents.report_agent import generate_inspection_report
from app.agents.document_agent import answer_document_query, extract_structured_entities_from_document


# ============================================================
# 1. CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Service for NBA Accreditation Readiness",
    description="AI service for NBA Criteria 3, 4, 5, and 6 analysis",
    version="2.0.0"
)


# ============================================================
# 2. REQUEST MODELS
# ============================================================

class CriterionRequest(BaseModel):
    """
    Generic request model for criterion analysis.

    The data field carries verified, backend-aggregated structured data.
    It is forwarded to the relevant agent functions.
    """
    data: Dict[str, Any] = Field(default_factory=dict)


class DocumentQueryRequest(BaseModel):
    """Request model for RAG-grounded document queries."""
    query: str
    passages: List[Dict[str, Any]] = Field(default_factory=list)
    criterion_filter: Optional[str] = None
    top_k: int = 4


class EntityExtractionRequest(BaseModel):
    """Request model for structured entity extraction."""
    document_text: str
    target_criterion: str = "Criterion 3"


# ============================================================
# 3. HEALTH CHECK
# ============================================================

@app.get("/")
def home():
    """Simple health-check endpoint."""
    return {
        "message": "AI Service for NBA Accreditation Readiness is running",
        "status": "ok",
        "version": "2.0.0"
    }


# ============================================================
# 4. CRITERION 3 ANALYSIS ENDPOINT
# ============================================================

@app.post("/criterion3/analyze")
def analyze_criterion3(request: CriterionRequest):
    """
    Run the complete Criterion 3 AI analysis.

    Flow:
        Verified Criterion 3 Data (from request.data)
                    ↓
            Assessment Agent
                    ↓
             Student Agent
                    ↓
           Coordinator Agent
                    ↓
            Final Analysis
    """
    try:
        data = request.data or {}

        # Backend envelope adapter: the backend's agent_client sends
        # {criterion_code, requirement_code, structured_data, evidence_passages, ...}
        # rather than a full C3 course dataset. Merge it onto the verified
        # course dataset so the agents receive every key they expect, and pass
        # the backend's deterministic evaluation through as read-only context.
        backend_eval = None
        if data and "course" not in data and (
            "structured_data" in data or "criterion_code" in data
        ):
            backend_eval = {
                "requirement_code": data.get("requirement_code"),
                "academic_year": data.get("academic_year"),
                "department": data.get("department"),
                "analysis_task": data.get("analysis_task"),
                "deterministic_evaluation": data.get("structured_data") or {},
                "evidence_passages": data.get("evidence_passages") or [],
            }
            merged = copy.deepcopy(criterion3_data)
            merged["backend_evaluation"] = backend_eval
            data = merged

        # STEP 1: RUN ASSESSMENT AGENT
        if backend_eval is not None:
            assessment_input = get_assessment_data()
            assessment_input["backend_evaluation"] = backend_eval
            assessment_result = analyze_assessment(data=assessment_input)
        else:
            assessment_result = analyze_assessment(data=data if data else None)

        # STEP 2: RUN STUDENT AGENT
        student_result = analyze_student_performance(data=data if data else None)

        # STEP 3: RUN COORDINATOR AGENT
        final_result = coordinate_criterion3(
            assessment_analysis=assessment_result,
            student_analysis=student_result,
            data=data if data else None
        )

        return {
            "criterion": "Criterion 3",
            "analysis": final_result
        }

    except KeyError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required Criterion 3 data field: {str(error)}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(error)}"
        )


# ============================================================
# 5. CRITERION 4 ANALYSIS ENDPOINT
# ============================================================

@app.post("/criterion4/analyze")
def analyze_criterion4(request: CriterionRequest):
    """
    Run Criterion 4 (Students' Performance) AI analysis.

    The backend computes all deterministic scores.
    This endpoint uses the faculty agent's student analysis
    capabilities to explain results and identify evidence gaps.
    """
    try:
        data = request.data or {}
        result = analyze_student_performance(data=data if data else None)
        return {
            "criterion": "Criterion 4",
            "analysis": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Criterion 4 AI analysis failed: {str(error)}"
        )


# ============================================================
# 6. CRITERION 5 ANALYSIS ENDPOINT
# ============================================================

@app.post("/criterion5/analyze")
def analyze_criterion5(request: CriterionRequest):
    """
    Run Criterion 5 (Faculty Information) AI analysis.

    The backend computes all deterministic scores (SFR, FQI, Cadre).
    This endpoint explains findings and identifies evidence gaps.
    """
    try:
        data = request.data or {}
        result = analyze_faculty_information(data=data if data else None)
        return {
            "criterion": "Criterion 5",
            "analysis": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Criterion 5 AI analysis failed: {str(error)}"
        )


# ============================================================
# 7. CRITERION 6 ANALYSIS ENDPOINT
# ============================================================

@app.post("/criterion6/analyze")
def analyze_criterion6(request: CriterionRequest):
    """
    Run Criterion 6 (Faculty Contributions) AI analysis.

    The backend computes all deterministic scores.
    This endpoint explains findings and identifies evidence gaps.
    """
    try:
        data = request.data or {}
        result = analyze_faculty_contributions(data=data if data else None)
        return {
            "criterion": "Criterion 6",
            "analysis": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Criterion 6 AI analysis failed: {str(error)}"
        )


# ============================================================
# 8. COMPLIANCE ANALYSIS ENDPOINT
# ============================================================

@app.post("/compliance/analyze")
def analyze_compliance_endpoint(request: CriterionRequest):
    """
    Run overall compliance analysis across all criteria.
    """
    try:
        data = request.data or {}
        result = analyze_compliance_gaps(data=data if data else None)
        return {
            "analysis_type": "compliance",
            "analysis": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance analysis failed: {str(error)}"
        )


# ============================================================
# 9. INSPECTION READINESS ENDPOINT
# ============================================================

@app.post("/inspection/analyze")
def analyze_inspection_endpoint(request: CriterionRequest):
    """
    Run inspection readiness analysis.
    """
    try:
        data = request.data or {}
        result = run_virtual_inspection_audit(data=data if data else None)
        return {
            "analysis_type": "inspection_readiness",
            "analysis": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Inspection readiness analysis failed: {str(error)}"
        )


# ============================================================
# 10. REPORT GENERATION ENDPOINT
# ============================================================

@app.post("/report/generate")
def generate_report_endpoint(request: CriterionRequest):
    """
    Generate an accreditation readiness report.
    """
    try:
        data = request.data or {}
        result = generate_inspection_report(data=data if data else None)
        return {
            "analysis_type": "report",
            "report": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(error)}"
        )


# ============================================================
# 11. DOCUMENT QUERY ENDPOINT
# ============================================================

@app.post("/document/query")
def document_query_endpoint(request: DocumentQueryRequest):
    """
    Answer a grounded question using passages retrieved from the backend RAG.

    The backend PostgreSQL/pgvector RAG retrieves the passages.
    This endpoint uses the Document Agent to reason over them.
    """
    try:
        result = answer_document_query(
            query=request.query,
            passages=request.passages,
            criterion_filter=request.criterion_filter,
            top_k=request.top_k
        )
        return result
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document query failed: {str(error)}"
        )


# ============================================================
# 12. ENTITY EXTRACTION ENDPOINT
# ============================================================

@app.post("/document/extract")
def entity_extraction_endpoint(request: EntityExtractionRequest):
    """
    Extract structured entities from document text.
    """
    try:
        result = extract_structured_entities_from_document(
            document_text=request.document_text,
            target_criterion=request.target_criterion
        )
        return {
            "target_criterion": request.target_criterion,
            "extracted_entities": result
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Entity extraction failed: {str(error)}"
        )
