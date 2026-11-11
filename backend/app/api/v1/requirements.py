"""
AI-NBA Readiness System — Backend
app/api/v1/requirements.py

API endpoints for NBA Criteria, Requirements, and Deterministic Evaluations.

Authorization:
    - Listing criteria/requirements: any authenticated user.
    - Triggering evaluations:        HOD or ADMIN.
    - Evaluation history:            any authenticated user.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.business_rules.readiness_rules import evaluate_requirement, load_all_rules
from app.db.session import get_db
from app.models.phase4 import (
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementStatus,
    EvaluationMode,
)
from app.models.user import UserRoleName
from app.schemas.phase4 import (
    NBACriterionOut,
    NBARequirementOut,
    RequirementEvaluationOut,
    EvaluationTriggerRequest,
)

router = APIRouter(prefix="/nba", tags=["NBA Requirements"])


# ---------------------------------------------------------------------------
# Load rules once at import time
# ---------------------------------------------------------------------------
load_all_rules()


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------

@router.get(
    "/criteria",
    response_model=List[NBACriterionOut],
    summary="List NBA Criteria",
)
def list_criteria(
    is_active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """Return all NBA criteria, optionally filtered by active status."""
    q = db.query(NBACriterion)
    if is_active is not None:
        q = q.filter(NBACriterion.is_active == is_active)
    return q.order_by(NBACriterion.display_order).all()


@router.get(
    "/criteria/{criterion_id}",
    response_model=NBACriterionOut,
    summary="Get NBA Criterion by ID",
)
def get_criterion(
    criterion_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    criterion = db.query(NBACriterion).filter(NBACriterion.id == criterion_id).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found.")
    return criterion


@router.get(
    "/criteria/code/CRITERION_3/context",
    summary="Aggregated database context for Criterion 3 rule evaluation",
)
def get_criterion3_context(
    department: str = Query(..., min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """
    Return the C3 context dict built from live DB records (subjects, COs,
    CO-PO mappings) by criteria_context_service.get_c3_context. The frontend
    uses it to pre-fill the 3.1 continuous-assessment evaluation.
    Data retrieval only — no compliance decision is made here.
    """
    from app.services.criteria_context_service import get_c3_context
    return get_c3_context(db, department=department, academic_year_id=academic_year_id)


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------

@router.get(
    "/criteria/{criterion_id}/requirements",
    response_model=List[NBARequirementOut],
    summary="List requirements for a criterion",
)
def list_requirements(
    criterion_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    criterion = db.query(NBACriterion).filter(NBACriterion.id == criterion_id).first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found.")
    return (
        db.query(NBARequirement)
        .filter(NBARequirement.criterion_id == criterion_id)
        .order_by(NBARequirement.display_order)
        .all()
    )


@router.get(
    "/requirements/{requirement_id}",
    response_model=NBARequirementOut,
    summary="Get requirement by ID",
)
def get_requirement(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    req = db.query(NBARequirement).filter(NBARequirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found.")
    return req


# ---------------------------------------------------------------------------
# Deterministic Evaluation
# ---------------------------------------------------------------------------

@router.post(
    "/requirements/{requirement_id}/evaluate",
    response_model=RequirementEvaluationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger deterministic evaluation for a requirement",
)
def evaluate_requirement_endpoint(
    requirement_id: uuid.UUID,
    body: EvaluationTriggerRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    """
    Run the deterministic rule for the given requirement and persist the result.

    SECURITY: status is computed by backend rule logic — it is NOT accepted
    from the request body and NOT delegated to an LLM.

    Historical evaluations are always preserved (new row inserted).
    """
    req = db.query(NBARequirement).filter(NBARequirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found.")

    # Verify academic year exists
    from app.models.academic import AcademicYear
    year = db.query(AcademicYear).filter(AcademicYear.id == body.academic_year_id).first()
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found.")

    # Run deterministic rule
    result = evaluate_requirement(req.evaluation_rule_key, body.context)

    evaluation = RequirementEvaluation(
        requirement_id=requirement_id,
        academic_year_id=body.academic_year_id,
        department=body.department,
        status=result.status,
        score_attained=result.score_attained,
        max_score=result.max_score,
        mode=EvaluationMode.DETERMINISTIC.value,
        deterministic_metrics=result.deterministic_metrics,
        limitations=result.limitations,
        evaluated_by_user_id=current_user.id,
        notes=body.notes,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


# ---------------------------------------------------------------------------
# Evaluation History
# ---------------------------------------------------------------------------

@router.get(
    "/requirements/{requirement_id}/evaluations",
    response_model=List[RequirementEvaluationOut],
    summary="List evaluation history for a requirement",
)
def list_evaluations(
    requirement_id: uuid.UUID,
    department: Optional[str] = Query(default=None),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(RequirementEvaluation).filter(
        RequirementEvaluation.requirement_id == requirement_id
    )
    if department:
        q = q.filter(RequirementEvaluation.department == department)
    if academic_year_id:
        q = q.filter(RequirementEvaluation.academic_year_id == academic_year_id)
    return q.order_by(RequirementEvaluation.evaluated_at.desc()).limit(limit).all()
