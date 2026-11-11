"""
AI-NBA Readiness System — Backend
app/services/criterion3_service.py

Criterion 3 (Outcome-Based Assessment) pipeline, following the project brief:

    Question papers + question->CO mapping + student marks
        -> CO attainment (direct: CIE + SEE, indirect: course exit survey)
        -> PO / PSO attainment (CO-PO/PSO matrix, Tables 3.8.1 - 3.8.3)
        -> rubric scores for 3.1 - 3.8 (NBA Tier-I 2026 Annexure VII)
        -> deterministic evaluations, weak-CO gaps, missing-evidence gaps

Every number is computed here in Python. Nothing comes from an LLM and the
computed rubric components are never accepted from the browser.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.business_rules.criterion3_rules import C3_RUBRIC, REQUIREMENT_TO_RUBRIC
from app.business_rules.readiness_rules import evaluate_requirement, load_all_rules
from app.models.academic import Subject
from app.models.criterion3 import (
    AssessmentCOMap,
    AttainmentConfig,
    AttainmentSnapshot,
    C3RubricScore,
    COIndirectAttainment,
    POIndirectAttainment,
)
from app.models.curriculum import (
    AssessmentScheme,
    COPOMapping,
    COPSOMapping,
    CourseOutcome,
    ProgramOutcome,
    ProgramSpecificOutcome,
    Student,
    StudentAssessmentMark,
    SubjectEnrolment,
)
from app.models.phase4 import (
    Document,
    EvaluationMode,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementEvidence,
)
from app.models.phase5 import Gap, GapSeverity, GapStatus

load_all_rules()

C3_CODE = "CRITERION_3"

# NBA Tier-I 2026 manual, GAPC v4.0 (PO1 - PO11)
OFFICIAL_POS: Dict[str, str] = {
    "PO1": "Engineering Knowledge: Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization to develop solutions of complex engineering problems.",
    "PO2": "Problem Analysis: Identify, formulate, review research literature and analyze complex engineering problems reaching substantiated conclusions with consideration for sustainable development.",
    "PO3": "Design/Development of Solutions: Design creative solutions for complex engineering problems and design/develop systems, components or processes to meet identified needs.",
    "PO4": "Conduct Investigations of Complex Problems: Conduct investigations using research-based knowledge including design of experiments, modelling, analysis and interpretation of data.",
    "PO5": "Engineering Tool Usage: Create, select and apply appropriate techniques, resources and modern engineering & IT tools recognizing their limitations.",
    "PO6": "The Engineer and The World: Analyze and evaluate societal and environmental aspects while solving complex engineering problems for their impact on sustainability.",
    "PO7": "Ethics: Apply ethical principles and commit to professional ethics, human values, diversity and inclusion; adhere to national & international laws.",
    "PO8": "Individual and Collaborative Team work: Function effectively as an individual, and as a member or leader in diverse/multi-disciplinary teams.",
    "PO9": "Communication: Communicate effectively and inclusively within the engineering community and society at large.",
    "PO10": "Project Management and Finance: Apply engineering management principles and economic decision-making to one's own work and to manage projects.",
    "PO11": "Life-Long Learning: Recognize the need for, and have the preparation and ability for independent and life-long learning and adaptability to emerging technologies.",
}


class C3Error(ValueError):
    """Validation error with a list of row-level problems."""

    def __init__(self, message: str, problems: Optional[List[str]] = None):
        super().__init__(message)
        self.problems = problems or []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _status_str(s: Any) -> str:
    return getattr(s, "value", s)


def _outcome_sort_key(code: str) -> Tuple[int, int]:
    m = re.match(r"^(PSO|PO|CO)(\d+)$", code.upper())
    if not m:
        return (9, 0)
    return ({"CO": 0, "PO": 1, "PSO": 2}[m.group(1)], int(m.group(2)))


# ---------------------------------------------------------------------------
# Program outcomes
# ---------------------------------------------------------------------------

def ensure_program_outcomes(db: Session, department: str, academic_year_id: uuid.UUID) -> None:
    """Create the 11 official POs for the department if missing."""
    existing = {p.code for p in db.query(ProgramOutcome).filter(ProgramOutcome.department == department)}
    for code, desc in OFFICIAL_POS.items():
        if code not in existing:
            db.add(ProgramOutcome(code=code, description=desc, department=department,
                                  academic_year_id=academic_year_id))
    db.flush()


def _get_outcome(db: Session, code: str, department: str, academic_year_id: uuid.UUID):
    code = code.upper().strip()
    if code.startswith("PSO"):
        pso = (db.query(ProgramSpecificOutcome)
               .filter(ProgramSpecificOutcome.code == code, ProgramSpecificOutcome.department == department)
               .first())
        if not pso:
            pso = ProgramSpecificOutcome(code=code, department=department, academic_year_id=academic_year_id,
                                         description=f"{code}: program specific outcome (edit the description for your program).")
            db.add(pso)
            db.flush()
        return "PSO", pso
    po = (db.query(ProgramOutcome)
          .filter(ProgramOutcome.code == code, ProgramOutcome.department == department).first())
    if not po:
        po = ProgramOutcome(code=code, department=department, academic_year_id=academic_year_id,
                            description=OFFICIAL_POS.get(code, f"{code}: program outcome."))
        db.add(po)
        db.flush()
    return "PO", po


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _read_csv(raw: bytes) -> List[List[str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
    return [r for r in rows if any(c for c in r)]


# ---------------------------------------------------------------------------
# CO-PO / PSO matrix upload
# ---------------------------------------------------------------------------

def import_co_po_matrix(db: Session, subject: Subject, raw: bytes) -> Dict[str, Any]:
    """
    CSV format (one row per CO):
        CO,Description,PO1,PO2,...,PO11,PSO1,PSO2
        CO1,Apply ensemble learning ...,3,2,,,...
    Cells: 1/2/3 = correlation level, blank / 0 / '-' = not mapped.
    Existing mappings of the listed COs are replaced.
    """
    rows = _read_csv(raw)
    if len(rows) < 2:
        raise C3Error("CSV needs a header row and at least one CO row.")
    header = [h.upper() for h in rows[0]]
    if not header or header[0] != "CO":
        raise C3Error("First column header must be 'CO'.")
    has_desc = len(header) > 1 and header[1] in ("DESCRIPTION", "CO DESCRIPTION", "STATEMENT")
    outcome_cols = header[2:] if has_desc else header[1:]
    bad = [h for h in outcome_cols if not re.match(r"^(PO|PSO)\d+$", h)]
    if bad:
        raise C3Error(f"Unrecognised outcome columns: {', '.join(bad)}. Use PO1..PO11 and PSO1..")

    ensure_program_outcomes(db, subject.department, subject.academic_year_id)
    outcomes = {code: _get_outcome(db, code, subject.department, subject.academic_year_id) for code in outcome_cols}

    problems: List[str] = []
    cos_done, maps_done = 0, 0
    for i, row in enumerate(rows[1:], start=2):
        co_code = (row[0] if row else "").upper()
        if not re.match(r"^CO\d+$", co_code):
            problems.append(f"Row {i}: '{row[0] if row else ''}' is not a CO code like CO1.")
            continue
        desc = row[1] if has_desc and len(row) > 1 and row[1] else None
        co = (db.query(CourseOutcome)
              .filter(CourseOutcome.subject_id == subject.id, CourseOutcome.code == co_code).first())
        if not co:
            co = CourseOutcome(code=co_code, subject_id=subject.id,
                               description=desc or f"{subject.name}: {co_code}")
            db.add(co)
            db.flush()
        elif desc:
            co.description = desc
        cos_done += 1
        db.query(COPOMapping).filter(COPOMapping.course_outcome_id == co.id).delete()
        db.query(COPSOMapping).filter(COPSOMapping.course_outcome_id == co.id).delete()
        values = row[2:] if has_desc else row[1:]
        for code, cell in zip(outcome_cols, values):
            cell = (cell or "").strip()
            if cell in ("", "0", "-"):
                continue
            if cell not in ("1", "2", "3"):
                problems.append(f"Row {i} {co_code}/{code}: '{cell}' must be 1, 2, 3 or blank.")
                continue
            kind, obj = outcomes[code]
            if kind == "PO":
                db.add(COPOMapping(course_outcome_id=co.id, program_outcome_id=obj.id, correlation_level=int(cell)))
            else:
                db.add(COPSOMapping(course_outcome_id=co.id, program_specific_outcome_id=obj.id,
                                    correlation_level=int(cell)))
            maps_done += 1
    if problems:
        db.rollback()
        raise C3Error("CO-PO matrix has errors; nothing was saved.", problems)
    db.commit()
    return {"course_outcomes": cos_done, "mappings": maps_done, "outcomes": outcome_cols}


# ---------------------------------------------------------------------------
# Marks upload
# ---------------------------------------------------------------------------

_COMPONENT_RE = re.compile(r"^(?P<name>[^|]+)\|(?P<co>CO\d+)\|(?P<max>\d+(\.\d+)?)(\|(?P<type>CIE|SEE))?$", re.I)


def _component_type(name: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit.upper()
    return "SEE" if name.strip().upper().startswith(("SEE", "ESE", "END SEM", "ENDSEM")) else "CIE"


def marks_template(db: Session, subject: Subject) -> str:
    cos = sorted((c.code for c in db.query(CourseOutcome).filter(CourseOutcome.subject_id == subject.id)),
                 key=_outcome_sort_key) or ["CO1", "CO2", "CO3", "CO4"]
    cols = ["USN", "Name"]
    for co in cos:
        cols.append(f"CIE-I Q{co[2:]}|{co}|10|CIE")
    for co in cos:
        cols.append(f"SEE Q{co[2:]}|{co}|20|SEE")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols)
    w.writerow(["22AIML001", "Student One"] + ["" for _ in cols[2:]])
    return out.getvalue()


def import_marks(db: Session, subject: Subject, raw: bytes) -> Dict[str, Any]:
    """
    CSV format (one row per student):
        USN,Name,CIE-I Q1|CO1|10,CIE-I Q2|CO2|10,...,SEE Q1|CO1|20|SEE,...
    Component header = "<name>|<CO>|<max marks>[|CIE or SEE]".
    Names starting with SEE/ESE are treated as SEE, everything else as CIE.
    Cells: number (0..max), 'AB' / 'A' = absent, blank = absent.
    The upload is all-or-nothing: any invalid cell rejects the whole file.
    """
    rows = _read_csv(raw)
    if len(rows) < 2:
        raise C3Error("CSV needs a header row and at least one student row.")
    header = rows[0]
    if not header or header[0].strip().upper() not in ("USN", "ROLL NO", "ROLL_NO", "ROLLNO", "PRN"):
        raise C3Error("First column must be USN (or Roll No / PRN).")
    name_col = len(header) > 1 and header[1].strip().upper() in ("NAME", "STUDENT NAME", "FULL NAME")
    comp_start = 2 if name_col else 1

    components: List[Dict[str, Any]] = []
    problems: List[str] = []
    for j, h in enumerate(header[comp_start:], start=comp_start):
        m = _COMPONENT_RE.match(h.replace(" |", "|").replace("| ", "|"))
        if not m:
            problems.append(f"Column {j + 1} header '{h}' must look like 'CIE-I Q1|CO1|10' (name|CO|max[|CIE/SEE]).")
            continue
        components.append({
            "col": j, "name": m.group("name").strip()[:50], "co": m.group("co").upper(),
            "max": float(m.group("max")), "type": _component_type(m.group("name"), m.group("type")),
        })
    if not components and not problems:
        problems.append("No assessment component columns found.")
    names = [c["name"] for c in components]
    dups = {n for n in names if names.count(n) > 1}
    if dups:
        problems.append(f"Duplicate component names: {', '.join(sorted(dups))}.")
    if any(c["max"] <= 0 for c in components):
        problems.append("Max marks must be greater than zero.")

    parsed: List[Tuple[str, str, List[Optional[float]]]] = []
    seen_usn: set = set()
    for i, row in enumerate(rows[1:], start=2):
        usn = (row[0] if row else "").strip().upper()
        if not usn:
            problems.append(f"Row {i}: USN is empty.")
            continue
        if usn in seen_usn:
            problems.append(f"Row {i}: USN {usn} appears twice.")
            continue
        seen_usn.add(usn)
        sname = row[1].strip() if name_col and len(row) > 1 and row[1].strip() else usn
        vals: List[Optional[float]] = []
        for c in components:
            cell = row[c["col"]].strip() if c["col"] < len(row) else ""
            if cell.upper() in ("", "AB", "A", "ABSENT", "-"):
                vals.append(None)
                continue
            try:
                v = float(cell)
            except ValueError:
                problems.append(f"Row {i} ({usn}) '{c['name']}': '{cell}' is not a number.")
                vals.append(None)
                continue
            if v < 0 or v > c["max"]:
                problems.append(f"Row {i} ({usn}) '{c['name']}': {v} is outside 0-{c['max']:g}.")
            vals.append(v)
        parsed.append((usn, sname, vals))

    if problems:
        raise C3Error("Marks file has errors; nothing was saved.", problems[:50])

    # --- write -------------------------------------------------------------
    created_cos: List[str] = []
    co_by_code = {c.code: c for c in db.query(CourseOutcome).filter(CourseOutcome.subject_id == subject.id)}
    schemes: List[AssessmentScheme] = []
    for c in components:
        co = co_by_code.get(c["co"])
        if not co:
            co = CourseOutcome(code=c["co"], subject_id=subject.id,
                               description=f"{subject.name}: {c['co']} (add the CO statement via the CO-PO matrix upload)")
            db.add(co)
            db.flush()
            co_by_code[c["co"]] = co
            created_cos.append(c["co"])
        sch = (db.query(AssessmentScheme)
               .filter(AssessmentScheme.subject_id == subject.id, AssessmentScheme.name == c["name"]).first())
        if not sch:
            sch = AssessmentScheme(subject_id=subject.id, name=c["name"], assessment_type=c["type"],
                                   max_marks=c["max"], weightage=None)
            db.add(sch)
            db.flush()
        else:
            sch.assessment_type = c["type"]
            sch.max_marks = c["max"]
        cmap = db.query(AssessmentCOMap).filter(AssessmentCOMap.assessment_scheme_id == sch.id).first()
        if cmap:
            cmap.course_outcome_id = co.id
        else:
            db.add(AssessmentCOMap(assessment_scheme_id=sch.id, course_outcome_id=co.id))
        schemes.append(sch)
    db.flush()

    new_students = 0
    marks_written = 0
    for usn, sname, vals in parsed:
        st = db.query(Student).filter(Student.usn == usn).first()
        if not st:
            st = Student(usn=usn, full_name=sname[:150], department=subject.department,
                         current_semester=subject.semester, academic_year_id=subject.academic_year_id)
            db.add(st)
            db.flush()
            new_students += 1
        enrol = (db.query(SubjectEnrolment)
                 .filter(SubjectEnrolment.student_id == st.id, SubjectEnrolment.subject_id == subject.id).first())
        if not enrol:
            db.add(SubjectEnrolment(student_id=st.id, subject_id=subject.id,
                                    academic_year_id=subject.academic_year_id))
        for sch, v in zip(schemes, vals):
            mk = (db.query(StudentAssessmentMark)
                  .filter(StudentAssessmentMark.student_id == st.id,
                          StudentAssessmentMark.assessment_scheme_id == sch.id).first())
            if not mk:
                mk = StudentAssessmentMark(student_id=st.id, subject_id=subject.id,
                                           assessment_scheme_id=sch.id, max_marks=sch.max_marks)
                db.add(mk)
            mk.max_marks = sch.max_marks
            mk.is_absent = v is None
            mk.marks_obtained = 0.0 if v is None else v
            marks_written += 1
    db.commit()
    return {
        "students": len(parsed),
        "new_students": new_students,
        "components": len(components),
        "marks_written": marks_written,
        "created_course_outcomes": created_cos,
        "cie_components": sum(1 for c in components if c["type"] == "CIE"),
        "see_components": sum(1 for c in components if c["type"] == "SEE"),
    }


# ---------------------------------------------------------------------------
# Configuration, indirect inputs, rubric scores
# ---------------------------------------------------------------------------

def get_config(db: Session, department: str, academic_year_id: uuid.UUID) -> AttainmentConfig:
    cfg = (db.query(AttainmentConfig)
           .filter(AttainmentConfig.department == department,
                   AttainmentConfig.academic_year_id == academic_year_id).first())
    if not cfg:
        cfg = AttainmentConfig(department=department, academic_year_id=academic_year_id, is_approved=False)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def config_dict(cfg: AttainmentConfig) -> Dict[str, Any]:
    keys = ["student_threshold_pct", "level3_pct", "level2_pct", "level1_pct", "cie_weight", "see_weight",
            "direct_weight", "indirect_weight", "co_target_level", "po_target_level", "is_approved"]
    d = {k: getattr(cfg, k) for k in keys}
    d["approved_at"] = cfg.approved_at.isoformat() if cfg.approved_at else None
    return d


def validate_config(data: Dict[str, Any]) -> List[str]:
    errs = []
    for k in ("student_threshold_pct", "level3_pct", "level2_pct", "level1_pct"):
        if not 0 <= float(data[k]) <= 100:
            errs.append(f"{k} must be between 0 and 100.")
    if not (float(data["level3_pct"]) > float(data["level2_pct"]) > float(data["level1_pct"])):
        errs.append("Level thresholds must satisfy Level 3 > Level 2 > Level 1.")
    if abs(float(data["cie_weight"]) + float(data["see_weight"]) - 100) > 0.01:
        errs.append("CIE weight + SEE weight must equal 100.")
    if abs(float(data["direct_weight"]) + float(data["indirect_weight"]) - 100) > 0.01:
        errs.append("Direct weight + indirect weight must equal 100.")
    for k in ("co_target_level", "po_target_level"):
        if not 0 < float(data[k]) <= 3:
            errs.append(f"{k} must be between 0 and 3.")
    return errs


def rubric_scores(db: Session, department: str, academic_year_id: uuid.UUID) -> Dict[str, Dict[str, Dict[str, Any]]]:
    out: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for r in (db.query(C3RubricScore)
              .filter(C3RubricScore.department == department,
                      C3RubricScore.academic_year_id == academic_year_id)):
        out[r.rubric_code][r.component_key] = {
            "score": r.score, "note": r.note, "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    return dict(out)


def save_rubric_scores(db: Session, department: str, academic_year_id: uuid.UUID, rubric_code: str,
                       scores: Dict[str, Dict[str, Any]], user_id: uuid.UUID) -> None:
    rubric = C3_RUBRIC.get(rubric_code)
    if not rubric:
        raise C3Error(f"Unknown sub-criterion {rubric_code}.")
    comps = {c["key"]: c for c in rubric["components"]}
    problems = []
    for key, val in scores.items():
        comp = comps.get(key)
        if not comp:
            problems.append(f"{rubric_code} has no component {key}.")
        elif comp["kind"] != "reviewer":
            problems.append(f"{rubric_code}-{key} is computed from data and cannot be entered manually.")
        elif val.get("score") is not None and not 0 <= float(val["score"]) <= comp["max"]:
            problems.append(f"{rubric_code}-{key} must be between 0 and {comp['max']:g}.")
    if problems:
        raise C3Error("Invalid rubric scores.", problems)
    for key, val in scores.items():
        row = (db.query(C3RubricScore)
               .filter(C3RubricScore.department == department, C3RubricScore.academic_year_id == academic_year_id,
                       C3RubricScore.rubric_code == rubric_code, C3RubricScore.component_key == key).first())
        if val.get("score") is None:
            if row:
                db.delete(row)
            continue
        if not row:
            row = C3RubricScore(department=department, academic_year_id=academic_year_id,
                                rubric_code=rubric_code, component_key=key, score=0)
            db.add(row)
        row.score = float(val["score"])
        row.note = (val.get("note") or None)
        row.updated_by_user_id = user_id
    db.commit()


# ---------------------------------------------------------------------------
# Attainment computation
# ---------------------------------------------------------------------------

def _level(pct: Optional[float], cfg: AttainmentConfig) -> Optional[int]:
    if pct is None:
        return None
    if pct >= cfg.level3_pct:
        return 3
    if pct >= cfg.level2_pct:
        return 2
    if pct >= cfg.level1_pct:
        return 1
    return 0


def _r(x: Optional[float], n: int = 2) -> Optional[float]:
    return None if x is None else round(x, n)


def compute_attainment(db: Session, department: str, academic_year_id: uuid.UUID) -> Dict[str, Any]:
    """Deterministic CO and PO/PSO attainment for every course with marks."""
    cfg = get_config(db, department, academic_year_id)
    limitations: List[str] = []
    subjects = (db.query(Subject)
                .filter(Subject.department == department, Subject.academic_year_id == academic_year_id)
                .order_by(Subject.semester, Subject.code).all())

    courses: List[Dict[str, Any]] = []
    all_co_rows: List[Dict[str, Any]] = []
    po_course_values: Dict[str, List[float]] = defaultdict(list)
    cie_cos_assessed, cos_in_marked_courses = 0, 0
    indirect_missing_courses: List[str] = []

    for s in subjects:
        cos = sorted(db.query(CourseOutcome).filter(CourseOutcome.subject_id == s.id).all(),
                     key=lambda c: _outcome_sort_key(c.code))
        schemes = db.query(AssessmentScheme).filter(AssessmentScheme.subject_id == s.id).all()
        maps = {m.assessment_scheme_id: m.course_outcome_id
                for m in db.query(AssessmentCOMap).filter(
                    AssessmentCOMap.assessment_scheme_id.in_([x.id for x in schemes] or [uuid.uuid4()]))}
        marks = (db.query(StudentAssessmentMark)
                 .filter(StudentAssessmentMark.subject_id == s.id).all())
        n_students = len({m.student_id for m in marks})
        course: Dict[str, Any] = {
            "subject_id": str(s.id), "code": s.code, "name": s.name, "semester": s.semester,
            "students": n_students, "components": len(schemes), "has_marks": bool(marks),
            "cos": [], "po_values": {}, "status": "NO_MARKS" if not marks else "OK",
        }
        if not cos:
            course["status"] = "NO_COS"
        if not marks or not cos:
            courses.append(course)
            continue

        cos_in_marked_courses += len(cos)
        scheme_by_id = {x.id: x for x in schemes}
        # per (student, co, type): [obtained, max]
        acc: Dict[Tuple[uuid.UUID, uuid.UUID, str], List[float]] = defaultdict(lambda: [0.0, 0.0])
        for m in marks:
            co_id = maps.get(m.assessment_scheme_id)
            sch = scheme_by_id.get(m.assessment_scheme_id)
            if not co_id or not sch or m.is_absent:
                continue
            t = "SEE" if (sch.assessment_type or "").upper() == "SEE" else "CIE"
            a = acc[(m.student_id, co_id, t)]
            a[0] += m.marks_obtained
            a[1] += m.max_marks
        indirect = {i.course_outcome_id: i.survey_pct for i in db.query(COIndirectAttainment).filter(
            COIndirectAttainment.course_outcome_id.in_([c.id for c in cos]))}
        if len(indirect) < len(cos):
            indirect_missing_courses.append(s.code)

        co_final: Dict[uuid.UUID, float] = {}
        for co in cos:
            row: Dict[str, Any] = {"code": co.code, "description": co.description}
            for t in ("CIE", "SEE"):
                pcts = [ob / mx * 100 for (st, cid, tt), (ob, mx) in acc.items() if cid == co.id and tt == t and mx > 0]
                if pcts:
                    attained = sum(1 for p in pcts if p >= cfg.student_threshold_pct)
                    pct_students = attained / len(pcts) * 100
                    row[f"{t.lower()}_students"] = len(pcts)
                    row[f"{t.lower()}_attained_pct"] = _r(pct_students)
                    row[f"{t.lower()}_level"] = _level(pct_students, cfg)
                else:
                    row[f"{t.lower()}_students"] = 0
                    row[f"{t.lower()}_attained_pct"] = None
                    row[f"{t.lower()}_level"] = None
            if row["cie_level"] is not None:
                cie_cos_assessed += 1
            cl, sl = row["cie_level"], row["see_level"]
            if cl is not None and sl is not None:
                direct = (cfg.cie_weight * cl + cfg.see_weight * sl) / 100
            else:
                direct = cl if cl is not None else sl
            row["direct"] = _r(direct)
            ind_pct = indirect.get(co.id)
            row["indirect_pct"] = _r(ind_pct)
            row["indirect"] = _level(ind_pct, cfg)
            if direct is None:
                final = None
            elif row["indirect"] is not None:
                final = (cfg.direct_weight * direct + cfg.indirect_weight * row["indirect"]) / 100
            else:
                final = direct
            row["final"] = _r(final)
            row["target"] = cfg.co_target_level
            row["met"] = final is not None and final >= cfg.co_target_level
            row["assessed"] = final is not None
            if final is not None:
                co_final[co.id] = final
            course["cos"].append(row)
            all_co_rows.append({**row, "course": s.code, "course_name": s.name, "subject_id": str(s.id)})

        # Course -> PO/PSO value = sum(corr x CO level) / sum(corr)   (Table 3.8.1 row)
        pv: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        for co in cos:
            if co.id not in co_final:
                continue
            for mp in co.po_mappings:
                pv[mp.program_outcome.code].append((mp.correlation_level, co_final[co.id]))
            for mp in co.pso_mappings:
                pv[mp.program_specific_outcome.code].append((mp.correlation_level, co_final[co.id]))
        for code, pairs in pv.items():
            val = sum(c * v for c, v in pairs) / sum(c for c, _ in pairs)
            course["po_values"][code] = _r(val)
            po_course_values[code].append(val)
        if not pv:
            limitations.append(f"{s.code}: COs are not mapped to any PO/PSO (upload the CO-PO matrix).")
        courses.append(course)

    # Direct PO attainment = average across courses addressing the PO (manual note under Table 3.8.1)
    codes = sorted(po_course_values.keys(), key=_outcome_sort_key)
    direct = {c: _r(sum(v) / len(v)) for c, v in po_course_values.items()}
    surveys: Dict[str, Dict[str, float]] = defaultdict(dict)
    for p in db.query(POIndirectAttainment).filter(POIndirectAttainment.department == department,
                                                   POIndirectAttainment.academic_year_id == academic_year_id):
        surveys[p.survey_name][p.outcome_code] = p.level
    indirect_po: Dict[str, Optional[float]] = {}
    for c in codes:
        vals = [sv[c] for sv in surveys.values() if c in sv]
        indirect_po[c] = _r(sum(vals) / len(vals)) if vals else None
    overall: Dict[str, Optional[float]] = {}
    for c in codes:
        d, i = direct.get(c), indirect_po.get(c)
        overall[c] = _r((cfg.direct_weight * d + cfg.indirect_weight * i) / 100) if (d is not None and i is not None) else d
    if codes and not surveys:
        limitations.append("No PO/PSO indirect survey entered (Table 3.8.2); overall PO attainment uses direct attainment only.")
    if indirect_missing_courses:
        limitations.append("Course exit survey (indirect CO attainment) missing for: "
                           + ", ".join(indirect_missing_courses) + ". Final CO attainment uses direct attainment for those COs.")

    assessed = [r for r in all_co_rows if r["assessed"]]
    met = [r for r in assessed if r["met"]]
    weak = sorted([r for r in assessed if not r["met"]], key=lambda r: r["final"])
    overall_vals = [v for v in overall.values() if v is not None]
    if not assessed:
        limitations.insert(0, "No marks uploaded yet: CO/PO attainment cannot be computed.")

    return {
        "computed_at": _now().isoformat(),
        "config": config_dict(cfg),
        "courses": courses,
        "po": {
            "codes": codes, "direct": direct, "indirect": indirect_po, "overall": overall,
            "surveys": {k: v for k, v in surveys.items()},
            "target": cfg.po_target_level,
            "met": {c: (overall[c] is not None and overall[c] >= cfg.po_target_level) for c in codes},
        },
        "summary": {
            "courses_total": len(subjects),
            "courses_with_marks": sum(1 for c in courses if c["has_marks"]),
            "cos_assessed": len(assessed),
            "cos_met": len(met),
            "cos_met_pct": _r(len(met) / len(assessed) * 100) if assessed else None,
            "avg_co_level": _r(sum(r["final"] for r in assessed) / len(assessed)) if assessed else None,
            "avg_po_level": _r(sum(overall_vals) / len(overall_vals)) if overall_vals else None,
            "pos_met": sum(1 for c in codes if overall[c] is not None and overall[c] >= cfg.po_target_level),
            "pos_total": len(codes),
            "cie_cos_assessed": cie_cos_assessed,
            "cos_in_marked_courses": cos_in_marked_courses,
            "weak_cos": [{"course": r["course"], "subject_id": r["subject_id"], "code": r["code"],
                          "final": r["final"], "target": r["target"]} for r in weak],
        },
        "limitations": limitations,
    }


def latest_snapshot(db: Session, department: str, academic_year_id: uuid.UUID) -> Optional[AttainmentSnapshot]:
    return (db.query(AttainmentSnapshot)
            .filter(AttainmentSnapshot.department == department,
                    AttainmentSnapshot.academic_year_id == academic_year_id)
            .order_by(AttainmentSnapshot.computed_at.desc()).first())


# ---------------------------------------------------------------------------
# Full Criterion 3 run
# ---------------------------------------------------------------------------

def _c3_requirements(db: Session) -> Tuple[NBACriterion, List[NBARequirement]]:
    crit = db.query(NBACriterion).filter(NBACriterion.code == C3_CODE).first()
    if not crit:
        raise C3Error("Criterion 3 is not seeded. Run `python -m app.db.seed`.")
    reqs = (db.query(NBARequirement)
            .filter(NBARequirement.criterion_id == crit.id, NBARequirement.is_active.is_(True),
                    NBARequirement.code.in_(list(REQUIREMENT_TO_RUBRIC.keys())))
            .order_by(NBARequirement.display_order).all())
    return crit, reqs


def _open_gap(db: Session, req: NBARequirement, crit: NBACriterion, department: str, ay: uuid.UUID,
              title: str) -> Optional[Gap]:
    return (db.query(Gap)
            .filter(Gap.requirement_id == req.id, Gap.academic_year_id == ay, Gap.department == department,
                    Gap.title == title,
                    Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value])).first())


def run_criterion3(db: Session, department: str, academic_year_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
    """
    Compute attainment, evaluate 3.1-3.8 with the NBA rubric, persist evaluations,
    open gaps for weak COs / non-passing sub-criteria / missing evidence and
    close gaps whose cause has been fixed.
    """
    crit, reqs = _c3_requirements(db)
    att = compute_attainment(db, department, academic_year_id)
    snap = AttainmentSnapshot(department=department, academic_year_id=academic_year_id,
                              payload=att, computed_by_user_id=user_id)
    db.add(snap)
    db.flush()

    cfg = att["config"]
    summ = att["summary"]
    reviewer = rubric_scores(db, department, academic_year_id)

    computed: Dict[str, Dict[str, Optional[float]]] = {"3.1": {}, "3.7": {}, "3.8": {}}
    supporting: Dict[str, Dict[str, Any]] = defaultdict(dict)
    if summ["cos_in_marked_courses"]:
        computed["3.1"]["C"] = round(3.0 * summ["cie_cos_assessed"] / summ["cos_in_marked_courses"], 2)
    supporting["3.1"] = {"cos_assessed_in_cie": summ["cie_cos_assessed"],
                         "cos_in_courses_with_marks": summ["cos_in_marked_courses"]}
    if summ["cos_assessed"]:
        computed["3.7"]["C"] = round(20.0 * summ["cos_met"] / summ["cos_assessed"], 2)
    supporting["3.7"] = {"cos_assessed": summ["cos_assessed"], "cos_met_target": summ["cos_met"],
                         "co_target_level": cfg["co_target_level"], "avg_co_level": summ["avg_co_level"],
                         "weak_cos": [f"{w['course']} {w['code']} ({w['final']})" for w in summ["weak_cos"]]}
    if summ["avg_po_level"] is not None:
        computed["3.8"]["B"] = round(15.0 * summ["avg_po_level"] / 3.0, 2)
    supporting["3.8"] = {"avg_overall_po_pso_level": summ["avg_po_level"], "pos_met_target": summ["pos_met"],
                         "pos_total": summ["pos_total"], "po_target_level": cfg["po_target_level"]}

    results = []
    now = _now()
    for req in reqs:
        code = REQUIREMENT_TO_RUBRIC[req.code]
        rubric = C3_RUBRIC[code]
        comps: Dict[str, Optional[float]] = {}
        lim: List[str] = []
        for comp in rubric["components"]:
            if comp["kind"] == "computed":
                v = computed.get(code, {}).get(comp["key"])
                comps[comp["key"]] = v
                if v is None:
                    lim.append(f"{code}-{comp['key']} needs uploaded marks / CO-PO mapping to be computed.")
            else:
                sc = reviewer.get(code, {}).get(comp["key"])
                comps[comp["key"]] = sc["score"] if sc else None
        evidence = (db.query(func.count(RequirementEvidence.id))
                    .join(Document, RequirementEvidence.document_id == Document.id)
                    .filter(RequirementEvidence.requirement_id == req.id, Document.is_deleted.is_(False))
                    .scalar() or 0)
        if evidence == 0:
            lim.append("No evidence document linked to this sub-criterion.")
        ctx = {
            "components": comps,
            "attainment_formula_configured": bool(cfg["is_approved"]),
            "supporting_metrics": {**supporting.get(code, {}), "evidence_documents": evidence},
            "limitations": lim,
        }
        res = evaluate_requirement(req.evaluation_rule_key, ctx)
        ev = RequirementEvaluation(
            requirement_id=req.id, academic_year_id=academic_year_id, department=department,
            status=_status_str(res.status), score_attained=res.score_attained, max_score=res.max_score,
            mode=EvaluationMode.DETERMINISTIC.value, deterministic_metrics=res.deterministic_metrics,
            limitations=res.limitations, evaluated_by_user_id=user_id,
            notes="Criterion 3 run (rubric + attainment)",
        )
        db.add(ev)
        db.flush()
        results.append({"requirement": req, "code": code, "eval": ev, "evidence": evidence})

    # ---- gaps -------------------------------------------------------------
    created, closed = 0, 0
    req_by_code = {r["code"]: r for r in results}

    def open_or_create(r, title, desc, severity, reason, action):
        nonlocal created
        if _open_gap(db, r["requirement"], crit, department, academic_year_id, title):
            return
        db.add(Gap(requirement_id=r["requirement"].id, criterion_id=crit.id, academic_year_id=academic_year_id,
                   department=department, title=title[:255], description=desc, severity=severity,
                   status=GapStatus.IDENTIFIED.value, identified_from_evaluation_id=r["eval"].id,
                   responsible_evidence_or_data=f"Evidence documents linked: {r['evidence']}",
                   reason=reason, recommended_action=action, created_by_user_id=user_id))
        created += 1

    def close_if_open(r, title, note):
        nonlocal closed
        g = _open_gap(db, r["requirement"], crit, department, academic_year_id, title)
        if g:
            g.status = GapStatus.COMPLETED.value
            g.resolved_at = now
            g.reason = (g.reason or "") + f" | Auto-closed {now.date().isoformat()}: {note}"
            closed += 1

    # Weak COs -> gaps under 3.7 ; fixed COs -> auto-close
    if "3.7" in req_by_code and cfg["is_approved"]:
        r37 = req_by_code["3.7"]
        weak_keys = set()
        for w in summ["weak_cos"]:
            title = f"Weak CO: {w['course']} {w['code']} below target"
            weak_keys.add(title)
            open_or_create(r37, title,
                           f"{w['course']} {w['code']} final attainment {w['final']} is below the target level {w['target']}.",
                           GapSeverity.HIGH.value if (w["final"] or 0) < 1 else GapSeverity.MEDIUM.value,
                           "CO attainment computed from uploaded CIE/SEE marks and the course exit survey.",
                           "Conduct remedial teaching / additional practice for this CO, re-assess, upload the new marks and re-run Criterion 3.")
        for g in (db.query(Gap).filter(Gap.requirement_id == r37["requirement"].id, Gap.department == department,
                                       Gap.academic_year_id == academic_year_id, Gap.title.like("Weak CO:%"),
                                       Gap.status.in_([GapStatus.IDENTIFIED.value, GapStatus.IN_PROGRESS.value]))):
            if g.title not in weak_keys:
                g.status = GapStatus.COMPLETED.value
                g.resolved_at = now
                g.reason = (g.reason or "") + f" | Auto-closed {now.date().isoformat()}: CO now meets the target after re-assessment."
                closed += 1

    for r in results:
        ev = r["eval"]
        status = ev.status
        title = f"{r['code']} {C3_RUBRIC[r['code']]['title']}: {status}"
        for st in ("FAIL", "WARNING", "NEEDS_RULE_CLARIFICATION"):
            other = f"{r['code']} {C3_RUBRIC[r['code']]['title']}: {st}"
            if st != status:
                close_if_open(r, other, f"status is now {status}")
        if status in ("FAIL", "WARNING", "NEEDS_RULE_CLARIFICATION"):
            open_or_create(
                r, title,
                f"Criterion {r['code']} scored {ev.score_attained:g}/{ev.max_score:g} ({status}).",
                GapSeverity.HIGH.value if status == "FAIL" else GapSeverity.MEDIUM.value,
                "; ".join(ev.limitations or [])[:1000] or None,
                "Score the remaining rubric components with evidence, or approve the attainment configuration, then re-run Criterion 3."
                if status != "FAIL" else "Address the low-scoring rubric components, attach evidence and re-run Criterion 3.",
            )
        ev_title = f"{r['code']} evidence missing"
        if r["evidence"] == 0:
            open_or_create(r, ev_title, f"No evidence document is linked to {r['code']}.", GapSeverity.LOW.value,
                           "NBA evaluators verify every rubric item against documents in the course files.",
                           "Upload the course-file evidence for this sub-criterion and link it in the Evidence tab.")
        else:
            close_if_open(r, ev_title, "evidence linked")

    db.commit()
    total = sum(r["eval"].score_attained for r in results)
    passed = sum(1 for r in results if r["eval"].status == "PASS")
    return {
        "snapshot_id": str(snap.id),
        "evaluated": len(results),
        "passed": passed,
        "total_score": round(total, 2),
        "max_score": sum(r["eval"].max_score for r in results),
        "readiness_percentage": round(passed / len(results) * 100, 2) if results else None,
        "gaps_created": created,
        "gaps_closed": closed,
        "statuses": {r["code"]: r["eval"].status for r in results},
        "attainment_summary": summ,
        "limitations": att["limitations"],
    }


def courses_overview(db: Session, department: str, academic_year_id: uuid.UUID) -> List[Dict[str, Any]]:
    out = []
    for s in (db.query(Subject).filter(Subject.department == department, Subject.academic_year_id == academic_year_id)
              .order_by(Subject.semester, Subject.code)):
        cos = db.query(CourseOutcome).filter(CourseOutcome.subject_id == s.id).all()
        schemes = db.query(AssessmentScheme).filter(AssessmentScheme.subject_id == s.id).all()
        n_maps = sum(len(c.po_mappings) + len(c.pso_mappings) for c in cos)
        students = (db.query(func.count(func.distinct(StudentAssessmentMark.student_id)))
                    .filter(StudentAssessmentMark.subject_id == s.id).scalar() or 0)
        ind = (db.query(func.count(COIndirectAttainment.id))
               .filter(COIndirectAttainment.course_outcome_id.in_([c.id for c in cos] or [uuid.uuid4()])).scalar() or 0)
        out.append({
            "id": str(s.id), "code": s.code, "name": s.name, "semester": s.semester, "credits": s.credits,
            "course_outcomes": [{"id": str(c.id), "code": c.code, "description": c.description,
                                 "po_map": {m.program_outcome.code: m.correlation_level for m in c.po_mappings},
                                 "pso_map": {m.program_specific_outcome.code: m.correlation_level for m in c.pso_mappings}}
                                for c in sorted(cos, key=lambda c: _outcome_sort_key(c.code))],
            "co_count": len(cos), "mapping_count": n_maps,
            "components": [{"name": x.name, "type": x.assessment_type, "max": x.max_marks} for x in schemes],
            "students_with_marks": students, "indirect_entries": ind,
        })
    return out
