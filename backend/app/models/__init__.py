"""
AI-NBA Readiness System — Backend
app/models/__init__.py

Export all SQLAlchemy ORM models (Phases 1–4).
"""

from app.db.session import Base
from app.models.academic import AcademicYear, FacultySubjectAssignment, Subject
from app.models.curriculum import (
    AssessmentScheme,
    AttendanceRecord,
    COPOMapping,
    COPSOMapping,
    CourseOutcome,
    FeedbackSurvey,
    MicroProject,
    ProgramOutcome,
    ProgramSpecificOutcome,
    Student,
    StudentAssessmentMark,
    SubjectEnrolment,
)
from app.models.faculty import FacultyProfile
from app.models.faculty_data import (
    FacultyCertificate,
    FacultyConsultancy,
    FacultyContribution,
    FacultyExperience,
    FacultyPatent,
    FacultyProject,
    FacultyPublication,
    FacultyQualification,
    FacultyTraining,
)
from app.models.user import (
    Role,
    User,
    UserAccountStatus,
    UserRoleName,
    user_roles,
)
# Phase 4
from app.models.phase4 import (
    DocumentChunk,
    DocumentProcessingStatus,
    DocumentValidationStatus,
    EvaluationMode,
    Document,
    NBACriterion,
    NBARequirement,
    RequirementEvaluation,
    RequirementEvidence,
    RequirementStatus,
)
# Phase 5
from app.models.phase5 import (
    ActionPriority,
    ActionStatus,
    BackupRecord,
    BackupStatus,
    CorrectiveAction,
    Gap,
    GapSeverity,
    GapStatus,
    Notification,
    NotificationType,
)

from app.models.criterion3 import (
    AssessmentCOMap,
    AttainmentConfig,
    AttainmentSnapshot,
    C3RubricScore,
    COIndirectAttainment,
    POIndirectAttainment,
)

__all__ = [
    "Base",
    "User",
    "Role",
    "UserAccountStatus",
    "UserRoleName",
    "user_roles",
    "FacultyProfile",
    "AcademicYear",
    "Subject",
    "FacultySubjectAssignment",
    # Faculty data
    "FacultyQualification",
    "FacultyExperience",
    "FacultyCertificate",
    "FacultyPublication",
    "FacultyPatent",
    "FacultyTraining",
    "FacultyProject",
    "FacultyConsultancy",
    "FacultyContribution",
    # Curriculum, outcomes, assessments, students
    "Student",
    "SubjectEnrolment",
    "ProgramOutcome",
    "ProgramSpecificOutcome",
    "CourseOutcome",
    "COPOMapping",
    "COPSOMapping",
    "AssessmentScheme",
    "StudentAssessmentMark",
    "AttendanceRecord",
    "MicroProject",
    "FeedbackSurvey",
    # Phase 4 — Requirements engine, documents, RAG
    "NBACriterion",
    "NBARequirement",
    "RequirementEvaluation",
    "RequirementStatus",
    "EvaluationMode",
    "Document",
    "DocumentProcessingStatus",
    "DocumentValidationStatus",
    "RequirementEvidence",
    "DocumentChunk",
    # Phase 5 — Digital Twin, Gaps, Actions, Notifications, Backup
    "Gap",
    "GapStatus",
    "GapSeverity",
    "CorrectiveAction",
    "ActionStatus",
    "ActionPriority",
    "Notification",
    "NotificationType",
    "BackupRecord",
    "BackupStatus",
    # Criterion 3 — attainment & rubric
    "AssessmentCOMap",
    "AttainmentConfig",
    "AttainmentSnapshot",
    "C3RubricScore",
    "COIndirectAttainment",
    "POIndirectAttainment",
]

