"""
AI-NBA Readiness System — Backend
app/services/gap_service.py

Milestone D: Gap Analysis and Corrective Action Tracking Service.
Handles gap generation, duplicate prevention, corrective action lifecycle, and RBAC checks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, FacultySubjectAssignment, Subject
from app.models.phase4 import (
    Document,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementEvidence,
    RequirementStatus,
)
from app.models.phase5 import (
    ActionPriority,
    ActionStatus,
    CorrectiveAction,
    Gap,
    GapSeverity,
    GapStatus,
)
from app.models.user import User, UserRoleName
from app.schemas.phase5 import (
    CorrectiveActionCreateRequest,
    CorrectiveActionOut,
    CorrectiveActionUpdateRequest,
    GapCreateRequest,
    GapGenerateResponse,
    GapOut,
    GapUpdateRequest,
)


class GapService:
    """
    Manages Gap Analysis and Corrective Action tracking with role-based access control.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_gaps_for_academic_year(
        self,
        academic_year_id: uuid.UUID,
        department: str,
        current_user: User,
        criterion_id: Optional[uuid.UUID] = None,
    ) -> GapGenerateResponse:
        """
        Scan latest evaluations for FAIL or WARNING statuses, and requirements with missing mandatory evidence.
        Creates gaps deterministically without generating duplicates for open items.
        """
        req_query = self.db.query(NBARequirement).filter(NBARequirement.is_active.is_(True))
        if criterion_id:
            req_query = req_query.filter(NBARequirement.criterion_id == criterion_id)
        requirements = req_query.all()

        created_count = 0
        existing_count = 0
        details: List[str] = []

        now = datetime.now(timezone.utc)

        for req in requirements:
            # Check latest evaluation for this academic year & department
            latest_eval = (
                self.db.query(RequirementEvaluation)
                .filter(
                    RequirementEvaluation.requirement_id == req.id,
                    RequirementEvaluation.academic_year_id == academic_year_id,
                    RequirementEvaluation.department == department,
                )
                .order_by(RequirementEvaluation.evaluated_at.desc())
                .first()
            )

            # Check evidence count
            evidence_count = (
                self.db.query(func.count(RequirementEvidence.id))
                .join(Document, RequirementEvidence.document_id == Document.id)
                .filter(
                    RequirementEvidence.requirement_id == req.id,
                    Document.is_deleted.is_(False),
                )
                .scalar()
                or 0
            )

            should_create_gap = False
            title = ""
            desc = ""
            severity = GapSeverity.MEDIUM.value
            reason = ""
            recommended = ""
            eval_id = None

            if latest_eval:
                eval_id = latest_eval.id
                if latest_eval.status == RequirementStatus.FAIL.value:
                    should_create_gap = True
                    severity = GapSeverity.HIGH.value
                    title = f"Requirement {req.code} Failed Compliance"
                    desc = f"Deterministic evaluation failed for {req.code}: {req.title}."
                    reason = f"Calculated score: {latest_eval.score_attained}/{latest_eval.max_score}."
                    if latest_eval.limitations:
                        reason += " Limitations: " + "; ".join(latest_eval.limitations)
                    recommended = "Review underlying faculty/student/curriculum metrics and rectify deficits."
                elif latest_eval.status == RequirementStatus.WARNING.value:
                    should_create_gap = True
                    severity = GapSeverity.MEDIUM.value
                    title = f"Requirement {req.code} Warning / Incomplete Data"
                    desc = f"Deterministic evaluation reported warning for {req.code}: {req.title}."
                    reason = "Limitations: " + "; ".join(latest_eval.limitations or ["Metric fell below target or data missing."])
                    recommended = "Validate source records, address missing data, and re-run evaluation."
            elif evidence_count == 0:
                # Unevaluated and missing evidence
                should_create_gap = True
                severity = GapSeverity.LOW.value
                title = f"Requirement {req.code} Unevaluated with No Evidence"
                desc = f"No evaluations performed and no evidence documents uploaded for {req.code}."
                reason = "Requirement is pending documentation and baseline evaluation."
                recommended = "Upload required verification documents and trigger deterministic evaluation."

            if should_create_gap:
                # Check for existing open gap for this requirement, year, and department
                existing_open_gap = (
                    self.db.query(Gap)
                    .filter(
                        Gap.requirement_id == req.id,
                        Gap.academic_year_id == academic_year_id,
                        Gap.department == department,
                        Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]),
                    )
                    .first()
                )

                if existing_open_gap:
                    existing_count += 1
                    # Update evaluation linkage if newer
                    if eval_id and existing_open_gap.identified_from_evaluation_id != eval_id:
                        existing_open_gap.identified_from_evaluation_id = eval_id
                        existing_open_gap.updated_at = now
                else:
                    new_gap = Gap(
                        requirement_id=req.id,
                        criterion_id=req.criterion_id,
                        academic_year_id=academic_year_id,
                        department=department,
                        title=title,
                        description=desc,
                        severity=severity,
                        status=GapStatus.IDENTIFIED.value,
                        identified_from_evaluation_id=eval_id,
                        responsible_evidence_or_data=f"Evaluations / Evidence count: {evidence_count}",
                        reason=reason,
                        recommended_action=recommended,
                        created_by_user_id=current_user.id,
                    )
                    self.db.add(new_gap)
                    created_count += 1
                    details.append(f"Created gap for requirement {req.code}")
            else:
                # If latest evaluation is PASS, check if an open gap exists and auto-resolve it
                if latest_eval and latest_eval.status == RequirementStatus.PASS.value:
                    open_gap = (
                        self.db.query(Gap)
                        .filter(
                            Gap.requirement_id == req.id,
                            Gap.academic_year_id == academic_year_id,
                            Gap.department == department,
                            Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]),
                        )
                        .first()
                    )
                    if open_gap:
                        open_gap.status = GapStatus.COMPLETED.value
                        open_gap.resolved_at = now
                        open_gap.updated_at = now
                        open_gap.reason = (open_gap.reason or "") + " [Auto-resolved: requirement reevaluated as PASS]"
                        details.append(f"Auto-resolved gap for requirement {req.code} after successful PASS evaluation.")

        self.db.commit()

        total_open = (
            self.db.query(func.count(Gap.id))
            .filter(
                Gap.academic_year_id == academic_year_id,
                Gap.department == department,
                Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]),
            )
            .scalar()
            or 0
        )

        return GapGenerateResponse(
            academic_year_id=academic_year_id,
            department=department,
            gaps_created=created_count,
            gaps_existing=existing_count,
            total_open_gaps=total_open,
            details=details,
        )

    def list_gaps(
        self,
        academic_year_id: Optional[uuid.UUID] = None,
        department: Optional[str] = None,
        criterion_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Gap], int]:
        """
        List gaps with safe pagination and filtering.
        """
        q = self.db.query(Gap)

        if academic_year_id:
            q = q.filter(Gap.academic_year_id == academic_year_id)
        if department:
            q = q.filter(Gap.department == department)
        if criterion_id:
            q = q.filter(Gap.criterion_id == criterion_id)
        if status_filter:
            q = q.filter(Gap.status == status_filter.upper())
        if severity_filter:
            q = q.filter(Gap.severity == severity_filter.upper())

        total = q.count()
        items = q.order_by(Gap.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def get_gap_by_id(self, gap_id: uuid.UUID) -> Gap:
        gap = self.db.query(Gap).filter(Gap.id == gap_id).first()
        if not gap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap not found.")
        return gap

    def create_gap(self, req: GapCreateRequest, current_user: User) -> Gap:
        """Manually create a readiness gap (HOD or ADMIN)."""
        now = datetime.now(timezone.utc)
        gap = Gap(
            requirement_id=req.requirement_id,
            criterion_id=req.criterion_id,
            academic_year_id=req.academic_year_id,
            department=req.department,
            title=req.title,
            description=req.description,
            severity=req.severity,
            status=GapStatus.IDENTIFIED.value,
            responsible_evidence_or_data=req.responsible_evidence_or_data,
            reason=req.reason,
            recommended_action=req.recommended_action,
            created_by_user_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(gap)
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def update_gap(self, gap_id: uuid.UUID, update_data: GapUpdateRequest, current_user: User) -> Gap:
        gap = self.get_gap_by_id(gap_id)
        now = datetime.now(timezone.utc)

        if update_data.title is not None:
            gap.title = update_data.title
        if update_data.description is not None:
            gap.description = update_data.description
        if update_data.severity is not None:
            gap.severity = update_data.severity
        if update_data.responsible_evidence_or_data is not None:
            gap.responsible_evidence_or_data = update_data.responsible_evidence_or_data
        if update_data.reason is not None:
            gap.reason = update_data.reason
        if update_data.recommended_action is not None:
            gap.recommended_action = update_data.recommended_action
        if update_data.status is not None:
            gap.status = update_data.status
            if update_data.status == GapStatus.COMPLETED.value:
                gap.resolved_at = now
            elif update_data.status in (GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value):
                gap.resolved_at = None

        gap.updated_at = now
        self.db.commit()
        self.db.refresh(gap)
        return gap

    def create_corrective_action(
        self,
        gap_id: uuid.UUID,
        req: CorrectiveActionCreateRequest,
        current_user: User,
    ) -> CorrectiveAction:
        """Create a corrective action attached to a gap."""
        gap = self.get_gap_by_id(gap_id)
        now = datetime.now(timezone.utc)

        action = CorrectiveAction(
            gap_id=gap.id,
            title=req.title,
            description=req.description,
            assigned_to_user_id=req.assigned_to_user_id,
            status=ActionStatus.IDENTIFIED.value,
            priority=req.priority,
            due_date=req.due_date,
            created_by_user_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(action)

        # Transition gap to IN_PROGRESS if currently IDENTIFIED
        if gap.status == GapStatus.IDENTIFIED.value:
            gap.status = GapStatus.IN_PROGRESS.value
            gap.updated_at = now

        self.db.commit()
        self.db.refresh(action)
        return action

    def update_corrective_action(
        self,
        action_id: uuid.UUID,
        req: CorrectiveActionUpdateRequest,
        current_user: User,
    ) -> CorrectiveAction:
        """
        Update corrective action status, assignment, due date, notes.
        Enforces RBAC: Faculty may update actions assigned to them.
        HOD and ADMIN have broader oversight.
        """
        action = self.db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
        if not action:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corrective action not found.")

        # RBAC Check
        is_admin = current_user.has_role(UserRoleName.ADMIN.value)
        is_hod = current_user.has_role(UserRoleName.HOD.value)
        is_assignee = action.assigned_to_user_id == current_user.id

        if not (is_admin or is_hod or is_assignee):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this corrective action.",
            )

        now = datetime.now(timezone.utc)

        # Faculty assignees can update status, completion_notes, and description
        # Only HOD/ADMIN can reassign owners
        if req.assigned_to_user_id is not None:
            if not (is_admin or is_hod):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only HOD or Admin can reassign corrective actions.",
                )
            action.assigned_to_user_id = req.assigned_to_user_id

        if req.title is not None:
            action.title = req.title
        if req.description is not None:
            action.description = req.description
        if req.priority is not None:
            action.priority = req.priority
        if req.due_date is not None:
            action.due_date = req.due_date
        if req.completion_notes is not None:
            action.completion_notes = req.completion_notes

        if req.status is not None:
            action.status = req.status
            if req.status == ActionStatus.COMPLETED.value:
                action.completed_at = now
            elif req.status in (ActionStatus.IDENTIFIED.value, ActionStatus.IN_PROGRESS.value):
                action.completed_at = None

        action.updated_at = now
        self.db.commit()
        self.db.refresh(action)
        return action

    def get_overdue_actions(self, department: Optional[str] = None) -> List[CorrectiveAction]:
        now = datetime.now(timezone.utc)
        q = (
            self.db.query(CorrectiveAction)
            .join(Gap, CorrectiveAction.gap_id == Gap.id)
            .filter(
                CorrectiveAction.status.in_([ActionStatus.IDENTIFIED.value, ActionStatus.IN_PROGRESS.value]),
                CorrectiveAction.due_date.isnot(None),
                CorrectiveAction.due_date < now,
            )
        )
        if department:
            q = q.filter(Gap.department == department)
        return q.order_by(CorrectiveAction.due_date.asc()).all()

    @staticmethod
    def to_gap_out(gap: Gap) -> GapOut:
        now = datetime.now(timezone.utc)
        actions_out: List[CorrectiveActionOut] = []
        for a in gap.actions:
            is_overdue = False
            if a.due_date and a.status in (ActionStatus.IDENTIFIED.value, ActionStatus.IN_PROGRESS.value):
                # Ensure timezone-aware comparison
                dd = a.due_date if a.due_date.tzinfo else a.due_date.replace(tzinfo=timezone.utc)
                if dd < now:
                    is_overdue = True

            actions_out.append(
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
                    is_overdue=is_overdue,
                    completion_notes=a.completion_notes,
                    completed_at=a.completed_at,
                    created_by_user_id=a.created_by_user_id,
                    created_at=a.created_at,
                    updated_at=a.updated_at,
                )
            )

        return GapOut(
            id=gap.id,
            requirement_id=gap.requirement_id,
            requirement_code=gap.requirement.code if gap.requirement else None,
            criterion_id=gap.criterion_id,
            criterion_code=gap.criterion.code if gap.criterion else None,
            academic_year_id=gap.academic_year_id,
            academic_year_name=gap.academic_year.name if gap.academic_year else None,
            department=gap.department,
            title=gap.title,
            description=gap.description,
            severity=gap.severity,
            status=gap.status,
            responsible_evidence_or_data=gap.responsible_evidence_or_data,
            reason=gap.reason,
            recommended_action=gap.recommended_action,
            created_by_user_id=gap.created_by_user_id,
            created_at=gap.created_at,
            updated_at=gap.updated_at,
            resolved_at=gap.resolved_at,
            actions=actions_out,
        )
