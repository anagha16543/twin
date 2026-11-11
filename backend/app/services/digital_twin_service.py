"""
AI-NBA Readiness System — Backend
app/services/digital_twin_service.py

Milestone B & C: Digital Twin Service and Readiness Analytics.
Calculates department-wide and criterion-wise NBA readiness directly from active database state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, FacultySubjectAssignment, Subject
from app.models.curriculum import (
    AssessmentScheme,
    AttendanceRecord,
    COPOMapping,
    CourseOutcome,
    Student,
    StudentAssessmentMark,
)
from app.models.faculty import FacultyProfile
from app.models.faculty_data import FacultyPublication, FacultyQualification
from app.models.phase4 import (
    Document,
    DocumentProcessingStatus,
    DocumentValidationStatus,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementEvidence,
    RequirementStatus,
)
from app.models.phase5 import ActionStatus, CorrectiveAction, Gap, GapStatus
from app.schemas.phase5 import (
    CriterionReadinessAnalytics,
    DataCompletenessSummary,
    DigitalTwinSnapshotResponse,
    OverallReadiness,
    RequirementSummary,
)


class DigitalTwinService:
    """
    Computes real-time Digital Twin state and readiness analytics.
    Every metric is queried dynamically from active database entities.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_data_completeness(self, academic_year_id: uuid.UUID, department: str) -> DataCompletenessSummary:
        """
        Aggregate count of relevant persistent entities for data completeness.
        """
        faculty_count = (
            self.db.query(func.count(FacultyProfile.id))
            .filter(FacultyProfile.department == department)
            .scalar()
            or 0
        )

        qualifications_count = (
            self.db.query(func.count(FacultyQualification.id))
            .join(FacultyProfile, FacultyQualification.faculty_profile_id == FacultyProfile.id)
            .filter(FacultyProfile.department == department)
            .scalar()
            or 0
        )

        publications_count = (
            self.db.query(func.count(FacultyPublication.id))
            .join(FacultyProfile, FacultyPublication.faculty_profile_id == FacultyProfile.id)
            .filter(FacultyProfile.department == department)
            .scalar()
            or 0
        )

        subjects_count = (
            self.db.query(func.count(Subject.id))
            .filter(Subject.department == department)
            .scalar()
            or 0
        )

        active_assignments_count = (
            self.db.query(func.count(FacultySubjectAssignment.id))
            .join(Subject, FacultySubjectAssignment.subject_id == Subject.id)
            .filter(
                Subject.department == department,
                Subject.academic_year_id == academic_year_id,
                FacultySubjectAssignment.is_active.is_(True),
            )
            .scalar()
            or 0
        )


        students_count = (
            self.db.query(func.count(Student.id))
            .filter(Student.department == department)
            .scalar()
            or 0
        )

        co_count = (
            self.db.query(func.count(CourseOutcome.id))
            .join(Subject, CourseOutcome.subject_id == Subject.id)
            .filter(Subject.department == department)
            .scalar()
            or 0
        )


        co_po_count = (
            self.db.query(func.count(COPOMapping.id))
            .join(CourseOutcome, COPOMapping.course_outcome_id == CourseOutcome.id)
            .join(Subject, CourseOutcome.subject_id == Subject.id)
            .filter(Subject.department == department)
            .scalar()
            or 0
        )

        marks_count = (
            self.db.query(func.count(StudentAssessmentMark.id))
            .join(Student, StudentAssessmentMark.student_id == Student.id)
            .filter(Student.department == department)
            .scalar()
            or 0
        )

        attendance_count = (
            self.db.query(func.count(AttendanceRecord.id))
            .join(Student, AttendanceRecord.student_id == Student.id)
            .filter(Student.department == department)
            .scalar()
            or 0
        )

        documents_count = (
            self.db.query(func.count(Document.id))
            .filter(
                Document.department == department,
                Document.is_deleted.is_(False),
                (Document.academic_year_id == academic_year_id) | (Document.academic_year_id.is_(None)),
            )
            .scalar()
            or 0
        )

        validated_documents_count = (
            self.db.query(func.count(Document.id))
            .filter(
                Document.department == department,
                Document.is_deleted.is_(False),
                Document.validation_status == DocumentValidationStatus.VALIDATED.value,
                (Document.academic_year_id == academic_year_id) | (Document.academic_year_id.is_(None)),
            )
            .scalar()
            or 0
        )

        return DataCompletenessSummary(
            faculty_profiles_count=faculty_count,
            faculty_qualifications_count=qualifications_count,
            faculty_publications_count=publications_count,
            subjects_count=subjects_count,
            active_subject_assignments_count=active_assignments_count,
            students_count=students_count,
            course_outcomes_count=co_count,
            co_po_mappings_count=co_po_count,
            assessment_marks_count=marks_count,
            attendance_records_count=attendance_count,
            uploaded_documents_count=documents_count,
            validated_documents_count=validated_documents_count,
        )

    def get_digital_twin_snapshot(
        self,
        academic_year_id: uuid.UUID,
        department: str,
        criterion_code: Optional[str] = None,
    ) -> DigitalTwinSnapshotResponse:
        """
        Generate complete Digital Twin snapshot for the specified academic year and department.
        """
        academic_year = (
            self.db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        )
        if not academic_year:
            raise ValueError(f"Academic year not found for id: {academic_year_id}")

        criteria_query = self.db.query(NBACriterion).filter(NBACriterion.is_active.is_(True))
        if criterion_code:
            criteria_query = criteria_query.filter(NBACriterion.code == criterion_code.upper().strip())
        criteria = criteria_query.order_by(NBACriterion.display_order).all()

        criterion_analytics_list: List[CriterionReadinessAnalytics] = []

        total_reqs_all = 0
        passed_reqs_all = 0
        warning_reqs_all = 0
        failed_reqs_all = 0
        na_reqs_all = 0
        unevaluated_reqs_all = 0

        now = datetime.now(timezone.utc)
        system_limitations: List[str] = []

        for crit in criteria:
            reqs = (
                self.db.query(NBARequirement)
                .filter(NBARequirement.criterion_id == crit.id, NBARequirement.is_active.is_(True))
                .order_by(NBARequirement.display_order)
                .all()
            )

            c_total = len(reqs)
            c_passed = 0
            c_warning = 0
            c_failed = 0
            c_na = 0
            c_unevaluated = 0
            c_req_summaries: List[RequirementSummary] = []
            c_evidence_present_count = 0
            c_last_eval_time: Optional[datetime] = None
            c_limitations: List[str] = []

            for r in reqs:
                # Find most recent evaluation for this academic year & department
                latest_eval = (
                    self.db.query(RequirementEvaluation)
                    .filter(
                        RequirementEvaluation.requirement_id == r.id,
                        RequirementEvaluation.academic_year_id == academic_year_id,
                        RequirementEvaluation.department == department,
                    )
                    .order_by(RequirementEvaluation.evaluated_at.desc())
                    .first()
                )

                # Evidence link check
                evidence_count = (
                    self.db.query(func.count(RequirementEvidence.id))
                    .join(Document, RequirementEvidence.document_id == Document.id)
                    .filter(
                        RequirementEvidence.requirement_id == r.id,
                        Document.is_deleted.is_(False),
                    )
                    .scalar()
                    or 0
                )
                has_evidence = evidence_count > 0
                if has_evidence:
                    c_evidence_present_count += 1

                req_status = "UNEVALUATED"
                score_attained = None
                req_limits = []

                if latest_eval:
                    req_status = latest_eval.status
                    score_attained = latest_eval.score_attained
                    req_limits = latest_eval.limitations or []
                    if c_last_eval_time is None or latest_eval.evaluated_at > c_last_eval_time:
                        c_last_eval_time = latest_eval.evaluated_at

                    if req_status == RequirementStatus.PASS.value:
                        c_passed += 1
                    elif req_status == RequirementStatus.WARNING.value:
                        c_warning += 1
                    elif req_status == RequirementStatus.FAIL.value:
                        c_failed += 1
                    elif req_status == RequirementStatus.NOT_APPLICABLE.value:
                        c_na += 1
                    else:
                        c_unevaluated += 1
                else:
                    c_unevaluated += 1
                    req_limits.append("No evaluation has been executed for this academic year.")

                if "[PLACEHOLDER]" in r.title or "[PLACEHOLDER]" in (r.description or ""):
                    req_limits.append("Official NBA threshold contains placeholder parameters awaiting committee confirmation.")

                c_req_summaries.append(
                    RequirementSummary(
                        requirement_id=r.id,
                        requirement_code=r.code,
                        title=r.title,
                        max_score=r.weightage,
                        status=req_status,
                        score_attained=score_attained,
                        has_evidence=has_evidence,
                        evidence_count=evidence_count,
                        last_evaluated_at=latest_eval.evaluated_at if latest_eval else None,
                        limitations=req_limits,
                    )
                )

            # Criterion gaps count
            c_open_gaps = (
                self.db.query(func.count(Gap.id))
                .filter(
                    Gap.criterion_id == crit.id,
                    Gap.academic_year_id == academic_year_id,
                    Gap.department == department,
                    Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]),
                )
                .scalar()
                or 0
            )

            # Criterion readiness percentage calculation
            eligible_denominator = c_total - c_na
            c_readiness: Optional[float] = None
            if eligible_denominator > 0:
                if (c_passed + c_warning + c_failed) > 0:
                    c_readiness = round((c_passed / eligible_denominator) * 100.0, 2)
                else:
                    c_limitations.append("No eligible requirements have been evaluated yet for this criterion.")
            else:
                c_limitations.append("All requirements in this criterion are marked NOT_APPLICABLE.")

            evidence_avail = round((c_evidence_present_count / c_total * 100.0), 2) if c_total > 0 else 0.0

            criterion_analytics_list.append(
                CriterionReadinessAnalytics(
                    criterion_id=crit.id,
                    criterion_code=crit.code,
                    criterion_name=crit.name,
                    max_score=crit.max_marks,
                    total_requirements=c_total,
                    passed_requirements=c_passed,
                    warning_requirements=c_warning,
                    failed_requirements=c_failed,
                    not_applicable_requirements=c_na,
                    unevaluated_requirements=c_unevaluated,
                    readiness_percentage=c_readiness,
                    evidence_availability=evidence_avail,
                    open_gaps=c_open_gaps,
                    last_evaluation_timestamp=c_last_eval_time,
                    limitations=c_limitations,
                    requirements=c_req_summaries,
                )
            )


            total_reqs_all += c_total
            passed_reqs_all += c_passed
            warning_reqs_all += c_warning
            failed_reqs_all += c_failed
            na_reqs_all += c_na
            unevaluated_reqs_all += c_unevaluated

        # Overall readiness
        eligible_overall = total_reqs_all - na_reqs_all
        overall_readiness_pct: Optional[float] = None
        if eligible_overall > 0 and (passed_reqs_all + warning_reqs_all + failed_reqs_all) > 0:
            overall_readiness_pct = round((passed_reqs_all / eligible_overall) * 100.0, 2)
        else:
            system_limitations.append(
                "Overall readiness percentage cannot be calculated because no eligible requirements have been evaluated."
            )

        if unevaluated_reqs_all > 0:
            system_limitations.append(
                f"{unevaluated_reqs_all} requirement(s) are unevaluated and are NOT counted as passed."
            )

        # Department open gaps & overdue actions
        open_gaps_count = (
            self.db.query(func.count(Gap.id))
            .filter(
                Gap.academic_year_id == academic_year_id,
                Gap.department == department,
                Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]),
            )
            .scalar()
            or 0
        )

        overdue_actions_count = (
            self.db.query(func.count(CorrectiveAction.id))
            .join(Gap, CorrectiveAction.gap_id == Gap.id)
            .filter(
                Gap.academic_year_id == academic_year_id,
                Gap.department == department,
                CorrectiveAction.status.in_([ActionStatus.IDENTIFIED.value, ActionStatus.IN_PROGRESS.value]),
                CorrectiveAction.due_date.isnot(None),
                CorrectiveAction.due_date < now,
            )
            .scalar()
            or 0
        )

        data_completeness = self.get_data_completeness(academic_year_id, department)

        return DigitalTwinSnapshotResponse(
            academic_year=academic_year.name,
            academic_year_id=academic_year.id,
            department=department,
            generated_at=now,
            overall=OverallReadiness(
                total_requirements=total_reqs_all,
                passed_requirements=passed_reqs_all,
                warning_requirements=warning_reqs_all,
                failed_requirements=failed_reqs_all,
                not_applicable_requirements=na_reqs_all,
                unevaluated_requirements=unevaluated_reqs_all,
                eligible_requirements=eligible_overall,
                readiness_percentage=overall_readiness_pct,
            ),
            criteria=criterion_analytics_list,
            data_completeness=data_completeness,
            open_gaps=open_gaps_count,
            overdue_actions=overdue_actions_count,
            limitations=system_limitations,
        )
