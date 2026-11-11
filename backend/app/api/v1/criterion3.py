"""
AI-NBA Readiness System — Backend
app/api/v1/criterion3.py

Criterion 3 (Outcome-Based Assessment) workflow endpoints:
courses & COs, CO-PO matrix upload, marks upload, attainment configuration,
indirect surveys, rubric scores, attainment results and the full C3 run.

Authorization:
    read endpoints           any authenticated user
    marks / CO-PO uploads    HOD, ADMIN or FACULTY
    config, rubric, run      HOD or ADMIN
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.business_rules.criterion3_rules import C3_RUBRIC, REQUIREMENT_TO_RUBRIC
from app.db.session import get_db
from app.models.academic import AcademicYear, Subject
from app.models.criterion3 import COIndirectAttainment, POIndirectAttainment
from app.models.curriculum import AssessmentScheme, CourseOutcome, Student, StudentAssessmentMark
from app.models.user import User, UserRoleName
from app.services import criterion3_service as svc

router = APIRouter(prefix="/criterion3", tags=["Criterion 3 — Outcome-Based Assessment"])

HOD_ADMIN = require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)
UPLOADERS = require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value, UserRoleName.FACULTY.value)
MAX_CSV = 5 * 1024 * 1024


def _ay(db: Session, academic_year_id: Optional[uuid.UUID]) -> AcademicYear:
    if academic_year_id:
        ay = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    else:
        ay = (db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()
              or db.query(AcademicYear).order_by(AcademicYear.created_at.desc()).first())
    if not ay:
        raise HTTPException(status_code=404, detail="Academic year not found. Run the seed first.")
    return ay


def _subject(db: Session, subject_id: uuid.UUID) -> Subject:
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Course not found.")
    return s


def _c3_error(e: svc.C3Error) -> HTTPException:
    return HTTPException(status_code=422, detail={"message": str(e), "problems": e.problems})


async def _read_csv_upload(file: UploadFile) -> bytes:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file (Excel: File > Save As > CSV UTF-8).")
    raw = await file.read()
    if len(raw) > MAX_CSV:
        raise HTTPException(status_code=413, detail="CSV larger than 5 MB.")
    return raw


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------

@router.get("/rubric", summary="NBA Tier-I 2026 rubric for Criterion 3 (Annexure VII)")
def get_rubric(_: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"rubric": C3_RUBRIC, "requirement_map": REQUIREMENT_TO_RUBRIC}


@router.get("/rubric-scores", summary="Reviewer rubric scores")
def get_rubric_scores(department: str = Query(..., min_length=2),
                      academic_year_id: Optional[uuid.UUID] = None,
                      db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ay = _ay(db, academic_year_id)
    return svc.rubric_scores(db, department, ay.id)


class RubricScoreIn(BaseModel):
    score: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=1000)


class RubricScoresIn(BaseModel):
    department: str = Field(..., min_length=2)
    academic_year_id: Optional[uuid.UUID] = None
    scores: Dict[str, RubricScoreIn]


@router.put("/rubric-scores/{rubric_code}", summary="Save reviewer scores for one sub-criterion")
def put_rubric_scores(rubric_code: str, body: RubricScoresIn, db: Session = Depends(get_db),
                      user: User = Depends(HOD_ADMIN)):
    ay = _ay(db, body.academic_year_id)
    try:
        svc.save_rubric_scores(db, body.department, ay.id, rubric_code,
                               {k: v.model_dump() for k, v in body.scores.items()}, user.id)
    except svc.C3Error as e:
        raise _c3_error(e)
    return svc.rubric_scores(db, body.department, ay.id).get(rubric_code, {})


# ---------------------------------------------------------------------------
# Attainment configuration
# ---------------------------------------------------------------------------

class ConfigIn(BaseModel):
    department: str = Field(..., min_length=2)
    academic_year_id: Optional[uuid.UUID] = None
    student_threshold_pct: float = 60
    level3_pct: float = 70
    level2_pct: float = 60
    level1_pct: float = 50
    cie_weight: float = 40
    see_weight: float = 60
    direct_weight: float = 80
    indirect_weight: float = 20
    co_target_level: float = 2.0
    po_target_level: float = 2.0
    approve: bool = True


@router.get("/config", summary="Attainment methodology (levels, weights, targets)")
def get_config(department: str = Query(..., min_length=2), academic_year_id: Optional[uuid.UUID] = None,
               db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ay = _ay(db, academic_year_id)
    return svc.config_dict(svc.get_config(db, department, ay.id))


@router.put("/config", summary="Save and approve the attainment methodology")
def put_config(body: ConfigIn, db: Session = Depends(get_db), user: User = Depends(HOD_ADMIN)):
    ay = _ay(db, body.academic_year_id)
    data = body.model_dump()
    errs = svc.validate_config(data)
    if errs:
        raise HTTPException(status_code=422, detail={"message": "Invalid configuration.", "problems": errs})
    cfg = svc.get_config(db, body.department, ay.id)
    for k in ("student_threshold_pct", "level3_pct", "level2_pct", "level1_pct", "cie_weight", "see_weight",
              "direct_weight", "indirect_weight", "co_target_level", "po_target_level"):
        setattr(cfg, k, float(data[k]))
    cfg.is_approved = bool(body.approve)
    cfg.approved_by_user_id = user.id if body.approve else None
    cfg.approved_at = datetime.now(timezone.utc) if body.approve else None
    db.commit()
    db.refresh(cfg)
    return svc.config_dict(cfg)


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@router.get("/courses", summary="Courses with COs, mapping, marks and survey status")
def list_courses(department: str = Query(..., min_length=2), academic_year_id: Optional[uuid.UUID] = None,
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ay = _ay(db, academic_year_id)
    return svc.courses_overview(db, department, ay.id)


class CourseIn(BaseModel):
    department: str = Field(..., min_length=2)
    academic_year_id: Optional[uuid.UUID] = None
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=150)
    semester: int = Field(..., ge=1, le=10)
    credits: float = Field(default=3.0, gt=0)


@router.post("/courses", status_code=status.HTTP_201_CREATED, summary="Create a course")
def create_course(body: CourseIn, db: Session = Depends(get_db), _: User = Depends(HOD_ADMIN)):
    ay = _ay(db, body.academic_year_id)
    code = body.code.strip().upper()
    if db.query(Subject).filter(Subject.code == code, Subject.academic_year_id == ay.id).first():
        raise HTTPException(status_code=409, detail=f"Course {code} already exists for {ay.name}.")
    s = Subject(code=code, name=body.name.strip(), semester=body.semester, academic_year_id=ay.id,
                department=body.department.strip(), credits=body.credits)
    db.add(s)
    db.commit()
    svc.ensure_program_outcomes(db, s.department, ay.id)
    db.commit()
    return {"id": str(s.id), "code": s.code, "name": s.name}


@router.delete("/courses/{subject_id}", summary="Delete a course and its COs, marks and mappings")
def delete_course(subject_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(HOD_ADMIN)):
    from app.models.criterion3 import AssessmentCOMap
    from app.models.curriculum import COPOMapping, COPSOMapping, SubjectEnrolment
    s = _subject(db, subject_id)
    scheme_ids = [x.id for x in db.query(AssessmentScheme).filter(AssessmentScheme.subject_id == s.id)]
    co_ids = [c.id for c in db.query(CourseOutcome).filter(CourseOutcome.subject_id == s.id)]
    db.query(StudentAssessmentMark).filter(StudentAssessmentMark.subject_id == s.id).delete(synchronize_session=False)
    if scheme_ids:
        db.query(AssessmentCOMap).filter(AssessmentCOMap.assessment_scheme_id.in_(scheme_ids)).delete(synchronize_session=False)
        db.query(AssessmentScheme).filter(AssessmentScheme.id.in_(scheme_ids)).delete(synchronize_session=False)
    if co_ids:
        db.query(COIndirectAttainment).filter(COIndirectAttainment.course_outcome_id.in_(co_ids)).delete(synchronize_session=False)
        db.query(COPOMapping).filter(COPOMapping.course_outcome_id.in_(co_ids)).delete(synchronize_session=False)
        db.query(COPSOMapping).filter(COPSOMapping.course_outcome_id.in_(co_ids)).delete(synchronize_session=False)
        db.query(CourseOutcome).filter(CourseOutcome.id.in_(co_ids)).delete(synchronize_session=False)
    db.query(SubjectEnrolment).filter(SubjectEnrolment.subject_id == s.id).delete(synchronize_session=False)
    db.delete(s)
    db.commit()
    return {"deleted": str(subject_id)}


@router.post("/courses/{subject_id}/co-po", summary="Upload the CO-PO/PSO matrix CSV")
async def upload_co_po(subject_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                       _: User = Depends(UPLOADERS)):
    s = _subject(db, subject_id)
    raw = await _read_csv_upload(file)
    try:
        return svc.import_co_po_matrix(db, s, raw)
    except svc.C3Error as e:
        raise _c3_error(e)


@router.get("/courses/{subject_id}/marks-template", summary="Download a marks CSV template")
def marks_template(subject_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    s = _subject(db, subject_id)
    return Response(content=svc.marks_template(db, s), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{s.code}_marks_template.csv"'})


@router.post("/courses/{subject_id}/marks", summary="Upload student marks CSV (question -> CO)")
async def upload_marks(subject_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                       _: User = Depends(UPLOADERS)):
    s = _subject(db, subject_id)
    raw = await _read_csv_upload(file)
    try:
        return svc.import_marks(db, s, raw)
    except svc.C3Error as e:
        raise _c3_error(e)


@router.get("/courses/{subject_id}/marks", summary="Marks sheet for a course")
def get_marks(subject_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    s = _subject(db, subject_id)
    schemes = db.query(AssessmentScheme).filter(AssessmentScheme.subject_id == s.id).order_by(AssessmentScheme.created_at).all()
    from app.models.criterion3 import AssessmentCOMap
    co_of = {m.assessment_scheme_id: m.course_outcome.code
             for m in db.query(AssessmentCOMap).filter(AssessmentCOMap.assessment_scheme_id.in_([x.id for x in schemes] or [uuid.uuid4()]))}
    marks = db.query(StudentAssessmentMark).filter(StudentAssessmentMark.subject_id == s.id).all()
    by_student: Dict[uuid.UUID, Dict[str, Any]] = {}
    for m in marks:
        row = by_student.setdefault(m.student_id, {})
        row[str(m.assessment_scheme_id)] = None if m.is_absent else m.marks_obtained
    students = {st.id: st for st in db.query(Student).filter(Student.id.in_(list(by_student.keys()) or [uuid.uuid4()]))}
    return {
        "components": [{"id": str(x.id), "name": x.name, "type": x.assessment_type, "max": x.max_marks,
                        "co": co_of.get(x.id)} for x in schemes],
        "rows": sorted([{"usn": students[sid].usn, "name": students[sid].full_name, "marks": vals}
                        for sid, vals in by_student.items() if sid in students], key=lambda r: r["usn"]),
    }


class IndirectCOIn(BaseModel):
    values: Dict[str, Optional[float]]  # {"CO1": 78.0}


@router.put("/courses/{subject_id}/indirect", summary="Course exit survey % per CO (indirect)")
def put_indirect(subject_id: uuid.UUID, body: IndirectCOIn, db: Session = Depends(get_db),
                 _: User = Depends(UPLOADERS)):
    s = _subject(db, subject_id)
    cos = {c.code: c for c in db.query(CourseOutcome).filter(CourseOutcome.subject_id == s.id)}
    problems = [f"{k} is not a CO of {s.code}." for k in body.values if k.upper() not in cos]
    problems += [f"{k}: {v} must be 0-100." for k, v in body.values.items() if v is not None and not 0 <= v <= 100]
    if problems:
        raise HTTPException(status_code=422, detail={"message": "Invalid survey values.", "problems": problems})
    for k, v in body.values.items():
        co = cos[k.upper()]
        row = db.query(COIndirectAttainment).filter(COIndirectAttainment.course_outcome_id == co.id).first()
        if v is None:
            if row:
                db.delete(row)
            continue
        if not row:
            row = COIndirectAttainment(course_outcome_id=co.id, survey_pct=v)
            db.add(row)
        row.survey_pct = v
    db.commit()
    saved = {r.course_outcome_id: r.survey_pct for r in db.query(COIndirectAttainment).filter(
        COIndirectAttainment.course_outcome_id.in_([c.id for c in cos.values()] or [uuid.uuid4()]))}
    return {c.code: saved.get(c.id) for c in cos.values()}


# ---------------------------------------------------------------------------
# PO/PSO indirect surveys (Table 3.8.2)
# ---------------------------------------------------------------------------

class POSurveyIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    values: Dict[str, Optional[float]]


class POSurveysIn(BaseModel):
    department: str = Field(..., min_length=2)
    academic_year_id: Optional[uuid.UUID] = None
    surveys: List[POSurveyIn]


@router.get("/po-indirect", summary="PO/PSO indirect survey levels")
def get_po_indirect(department: str = Query(..., min_length=2), academic_year_id: Optional[uuid.UUID] = None,
                    db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ay = _ay(db, academic_year_id)
    out: Dict[str, Dict[str, float]] = {}
    for p in db.query(POIndirectAttainment).filter(POIndirectAttainment.department == department,
                                                   POIndirectAttainment.academic_year_id == ay.id):
        out.setdefault(p.survey_name, {})[p.outcome_code] = p.level
    return [{"name": k, "values": v} for k, v in out.items()]


@router.put("/po-indirect", summary="Replace PO/PSO indirect survey levels (0-3)")
def put_po_indirect(body: POSurveysIn, db: Session = Depends(get_db), _: User = Depends(HOD_ADMIN)):
    ay = _ay(db, body.academic_year_id)
    problems = [f"{s.name}/{k}: {v} must be 0-3." for s in body.surveys for k, v in s.values.items()
                if v is not None and not 0 <= v <= 3]
    if problems:
        raise HTTPException(status_code=422, detail={"message": "Invalid survey levels.", "problems": problems})
    db.query(POIndirectAttainment).filter(POIndirectAttainment.department == body.department,
                                          POIndirectAttainment.academic_year_id == ay.id).delete()
    for s in body.surveys:
        for k, v in s.values.items():
            if v is not None:
                db.add(POIndirectAttainment(department=body.department, academic_year_id=ay.id,
                                            survey_name=s.name.strip(), outcome_code=k.upper(), level=v))
    db.commit()
    return get_po_indirect(body.department, ay.id, db)


# ---------------------------------------------------------------------------
# Attainment results & full run
# ---------------------------------------------------------------------------

@router.get("/attainment", summary="CO and PO/PSO attainment (live computation)")
def get_attainment(department: str = Query(..., min_length=2), academic_year_id: Optional[uuid.UUID] = None,
                   db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ay = _ay(db, academic_year_id)
    live = svc.compute_attainment(db, department, ay.id)
    snap = svc.latest_snapshot(db, department, ay.id)
    live["last_run_at"] = snap.computed_at.isoformat() if snap else None
    return live


class RunIn(BaseModel):
    department: str = Field(..., min_length=2)
    academic_year_id: Optional[uuid.UUID] = None


@router.post("/run", summary="Run Criterion 3: attainment + rubric evaluation of 3.1-3.8 + gaps")
def run(body: RunIn, db: Session = Depends(get_db), user: User = Depends(HOD_ADMIN)):
    ay = _ay(db, body.academic_year_id)
    try:
        return svc.run_criterion3(db, body.department, ay.id, user.id)
    except svc.C3Error as e:
        raise _c3_error(e)
