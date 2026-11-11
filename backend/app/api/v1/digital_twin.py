"""
AI-NBA Readiness System — Backend
app/api/v1/digital_twin.py

Endpoints for Digital Twin state, department readiness snapshot, and data completeness.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.academic import AcademicYear
from app.models.user import User
from app.schemas.phase5 import (
    CriterionReadinessAnalytics,
    DataCompletenessSummary,
    DigitalTwinSnapshotResponse,
)
from app.services.digital_twin_service import DigitalTwinService

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])


def _resolve_academic_year(db: Session, academic_year_id: Optional[uuid.UUID] = None) -> AcademicYear:
    if academic_year_id:
        ay = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if not ay:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found.")
        return ay
    current = db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()
    if not current:
        current = db.query(AcademicYear).order_by(AcademicYear.created_at.desc()).first()
    if not current:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No academic year found. Please configure an academic year first.",
        )
    return current


@router.get(
    "/snapshot",
    response_model=DigitalTwinSnapshotResponse,
    summary="Get Digital Twin Department Readiness Snapshot",
)
def get_snapshot(
    department: str = Query(default="Computer Science and Engineering", min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    criterion_code: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Returns aggregated real-time Digital Twin snapshot representing department readiness.
    Readiness percentage is calculated deterministically from active database records.
    """
    ay = _resolve_academic_year(db, academic_year_id)
    service = DigitalTwinService(db)
    return service.get_digital_twin_snapshot(
        academic_year_id=ay.id,
        department=department,
        criterion_code=criterion_code,
    )


@router.get(
    "/completeness",
    response_model=DataCompletenessSummary,
    summary="Get Department Data Completeness Metrics",
)
def get_data_completeness(
    department: str = Query(default="Computer Science and Engineering", min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Returns count and availability of supporting records (faculty, curriculum, marks, documents).
    """
    ay = _resolve_academic_year(db, academic_year_id)
    service = DigitalTwinService(db)
    return service.get_data_completeness(academic_year_id=ay.id, department=department)


@router.get(
    "/criteria/{criterion_code}",
    response_model=CriterionReadinessAnalytics,
    summary="Get Criterion-Specific Readiness Analytics",
)
def get_criterion_analytics(
    criterion_code: str,
    department: str = Query(default="Computer Science and Engineering", min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ay = _resolve_academic_year(db, academic_year_id)
    service = DigitalTwinService(db)
    snapshot = service.get_digital_twin_snapshot(
        academic_year_id=ay.id,
        department=department,
        criterion_code=criterion_code,
    )
    if not snapshot.criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criterion '{criterion_code}' not found.",
        )
    return snapshot.criteria[0]
