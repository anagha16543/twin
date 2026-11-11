"""
AI-NBA Readiness System — Backend
app/api/v1/gaps.py

Endpoints for Gap Analysis, Corrective Action lifecycle, assignment, and overdue tracking.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.academic import AcademicYear
from app.models.phase5 import CorrectiveAction
from app.models.user import User, UserRoleName
from app.schemas.phase5 import (
    CorrectiveActionCreateRequest,
    CorrectiveActionOut,
    CorrectiveActionUpdateRequest,
    GapCreateRequest,
    GapGenerateRequest,
    GapGenerateResponse,
    GapOut,
    GapUpdateRequest,
)
from app.services.gap_service import GapService

router = APIRouter(prefix="/gaps", tags=["Gap Analysis"])


@router.post(
    "/generate",
    response_model=GapGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or Refresh Gap Analysis",
)
def generate_gaps(
    body: GapGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    """
    Scans requirement evaluations and evidence. Automatically creates readiness gaps
    for FAIL / WARNING statuses and missing evidence without duplicating open gaps.
    Restricted to HOD and Admin.
    """
    service = GapService(db)
    return service.generate_gaps_for_academic_year(
        academic_year_id=body.academic_year_id,
        department=body.department,
        current_user=current_user,
        criterion_id=body.criterion_id,
    )


@router.get(
    "",
    response_model=List[GapOut],
    summary="List Gaps",
)
def list_gaps(
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    department: Optional[str] = Query(default=None),
    criterion_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity_filter: Optional[str] = Query(default=None, alias="severity"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = GapService(db)
    items, _ = service.list_gaps(
        academic_year_id=academic_year_id,
        department=department,
        criterion_id=criterion_id,
        status_filter=status_filter,
        severity_filter=severity_filter,
        offset=offset,
        limit=limit,
    )
    return [GapService.to_gap_out(g) for g in items]


@router.post(
    "",
    response_model=GapOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Gap",
)
def create_gap(
    body: GapCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    service = GapService(db)
    gap = service.create_gap(body, current_user)
    return GapService.to_gap_out(gap)


@router.get(
    "/actions/overdue",
    response_model=List[CorrectiveActionOut],
    summary="List Overdue Corrective Actions",
)
def get_overdue_actions(
    department: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = GapService(db)
    actions = service.get_overdue_actions(department=department)
    out = []
    for a in actions:
        out.append(
            CorrectiveActionOut(
                id=a.id,
                gap_id=a.gap_id,
                title=a.title,
                description=a.description,
                assigned_to_user_id=a.assigned_to_user_id,
                assigned_to_email=a.assigned_to.email if a.assigned_to else None,
                status=a.status,
                priority=a.priority,
                due_date=a.due_date,
                is_overdue=True,
                completion_notes=a.completion_notes,
                completed_at=a.completed_at,
                created_by_user_id=a.created_by_user_id,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
        )
    return out


@router.get(
    "/{gap_id}",
    response_model=GapOut,
    summary="Get Gap by ID",
)
def get_gap(
    gap_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = GapService(db)
    gap = service.get_gap_by_id(gap_id)
    return GapService.to_gap_out(gap)


@router.patch(
    "/{gap_id}",
    response_model=GapOut,
    summary="Update Gap",
)
def update_gap(
    gap_id: uuid.UUID,
    body: GapUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    service = GapService(db)
    gap = service.update_gap(gap_id, body, current_user)
    return GapService.to_gap_out(gap)


@router.post(
    "/{gap_id}/actions",
    response_model=CorrectiveActionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Corrective Action for Gap",
)
def create_action(
    gap_id: uuid.UUID,
    body: CorrectiveActionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a corrective action. HOD and ADMIN can create and assign to any faculty.
    Faculty can create action items on gaps assigned to them or their department.
    """
    service = GapService(db)
    action = service.create_corrective_action(gap_id, body, current_user)
    return CorrectiveActionOut(
        id=action.id,
        gap_id=action.gap_id,
        title=action.title,
        description=action.description,
        assigned_to_user_id=action.assigned_to_user_id,
        assigned_to_email=action.assigned_to.email if action.assigned_to else None,
        status=action.status,
        priority=action.priority,
        due_date=action.due_date,
        is_overdue=False,
        completion_notes=action.completion_notes,
        completed_at=action.completed_at,
        created_by_user_id=action.created_by_user_id,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


@router.patch(
    "/actions/{action_id}",
    response_model=CorrectiveActionOut,
    summary="Update Corrective Action",
)
def update_action(
    action_id: uuid.UUID,
    body: CorrectiveActionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update corrective action. Enforces RBAC:
      - Faculty assignee may update status, description, and completion notes.
      - HOD/ADMIN can update all fields including reassignment.
    """
    service = GapService(db)
    action = service.update_corrective_action(action_id, body, current_user)
    return CorrectiveActionOut(
        id=action.id,
        gap_id=action.gap_id,
        title=action.title,
        description=action.description,
        assigned_to_user_id=action.assigned_to_user_id,
        assigned_to_email=action.assigned_to.email if action.assigned_to else None,
        status=action.status,
        priority=action.priority,
        due_date=action.due_date,
        is_overdue=False,
        completion_notes=action.completion_notes,
        completed_at=action.completed_at,
        created_by_user_id=action.created_by_user_id,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )
