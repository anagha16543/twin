"""
AI-NBA Readiness System — Backend
app/services/report_service.py

Milestone E: PDF and Excel Report Generation.
Extracts real database state, sanitizes spreadsheet cells to prevent formula injection,
and produces bounded PDF/Excel streams.
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear, Subject
from app.models.curriculum import COPOMapping, CourseOutcome, StudentAssessmentMark
from app.models.faculty import FacultyProfile
from app.models.faculty_data import FacultyContribution, FacultyQualification
from app.models.phase4 import Document, NBACriterion, NBARequirement, RequirementEvidence
from app.models.phase5 import CorrectiveAction, Gap
from app.services.digital_twin_service import DigitalTwinService


def sanitize_excel_cell(value: Any) -> Any:
    """
    Sanitize cell value to protect against Excel Formula Injection (CSV/XLSX Injection).
    If a string starts with '=', '+', '-', '@', '\\t', or '\\r', prepend a single quote.
    """
    if isinstance(value, str):
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{value}"
    return value


class ReportService:
    """
    Generates PDF and Excel reports for NBA readiness, criteria, evidence, faculty, and gaps.
    """

    def __init__(self, db: Session):
        self.db = db
        self.twin_service = DigitalTwinService(db)

    # -----------------------------------------------------------------------
    # Excel Report Generation
    # -----------------------------------------------------------------------

    def generate_excel_readiness_report(
        self,
        academic_year_id: uuid.UUID,
        department: str,
    ) -> io.BytesIO:
        """
        Generate comprehensive multi-sheet Excel report containing:
          1. Summary & Readiness Indicators
          2. Criterion & Requirement Breakdown
          3. Evidence Inventory
          4. Gap Analysis & Corrective Actions
        """
        snapshot = self.twin_service.get_digital_twin_snapshot(academic_year_id, department)

        wb = openpyxl.Workbook()

        # Sheet 1: Readiness Summary
        ws_summary = wb.active
        ws_summary.title = "Readiness Summary"

        header_font = Font(name="Calibri", size=14, bold=True, color="1B365D")
        sub_font = Font(name="Calibri", size=11, bold=True)
        notice_font = Font(name="Calibri", size=9, italic=True, color="7F8C8D")

        ws_summary.append([sanitize_excel_cell("NBA ACCREDITATION READINESS SUMMARY REPORT")])
        ws_summary["A1"].font = header_font
        ws_summary.append([sanitize_excel_cell(f"Department: {department} | Academic Year: {snapshot.academic_year}")])
        ws_summary["A2"].font = sub_font
        ws_summary.append([sanitize_excel_cell(f"Generated at: {snapshot.generated_at.isoformat()} (UTC)")])
        ws_summary.append([])

        ws_summary.append([sanitize_excel_cell("METRIC"), sanitize_excel_cell("VALUE")])
        ws_summary.append([sanitize_excel_cell("Total Requirements"), snapshot.overall.total_requirements])
        ws_summary.append([sanitize_excel_cell("Passed Requirements"), snapshot.overall.passed_requirements])
        ws_summary.append([sanitize_excel_cell("Warning Requirements"), snapshot.overall.warning_requirements])
        ws_summary.append([sanitize_excel_cell("Failed Requirements"), snapshot.overall.failed_requirements])
        ws_summary.append([sanitize_excel_cell("Not Applicable"), snapshot.overall.not_applicable_requirements])
        ws_summary.append([sanitize_excel_cell("Unevaluated Requirements"), snapshot.overall.unevaluated_requirements])
        ws_summary.append([
            sanitize_excel_cell("Internal Readiness Percentage"),
            f"{snapshot.overall.readiness_percentage}%" if snapshot.overall.readiness_percentage is not None else "N/A",
        ])
        ws_summary.append([sanitize_excel_cell("Open Gaps"), snapshot.open_gaps])
        ws_summary.append([sanitize_excel_cell("Overdue Actions"), snapshot.overdue_actions])
        ws_summary.append([])
        ws_summary.append([sanitize_excel_cell("CRITICAL COMPLIANCE NOTICE:")])
        ws_summary.append([sanitize_excel_cell(snapshot.overall.readiness_explanation)])
        ws_summary.append([sanitize_excel_cell(f"Calculation Formula: {snapshot.overall.readiness_formula}")])

        # Sheet 2: Criterion Breakdown
        ws_criteria = wb.create_sheet(title="Criteria & Requirements")
        ws_criteria.append([
            sanitize_excel_cell("Criterion Code"),
            sanitize_excel_cell("Requirement Code"),
            sanitize_excel_cell("Requirement Title"),
            sanitize_excel_cell("Max Score"),
            sanitize_excel_cell("Status"),
            sanitize_excel_cell("Score Attained"),
            sanitize_excel_cell("Evidence Count"),
            sanitize_excel_cell("Limitations"),
        ])

        for c in snapshot.criteria:
            for r in c.requirements:
                ws_criteria.append([
                    sanitize_excel_cell(c.criterion_code),
                    sanitize_excel_cell(r.requirement_code),
                    sanitize_excel_cell(r.title),
                    r.max_score,
                    sanitize_excel_cell(r.status),
                    r.score_attained if r.score_attained is not None else "N/A",
                    r.evidence_count,
                    sanitize_excel_cell("; ".join(r.limitations)),
                ])

        # Sheet 3: Gaps and Actions
        ws_gaps = wb.create_sheet(title="Gaps & Corrective Actions")
        ws_gaps.append([
            sanitize_excel_cell("Gap ID"),
            sanitize_excel_cell("Requirement"),
            sanitize_excel_cell("Severity"),
            sanitize_excel_cell("Status"),
            sanitize_excel_cell("Title"),
            sanitize_excel_cell("Description"),
            sanitize_excel_cell("Recommended Action"),
            sanitize_excel_cell("Action Count"),
        ])

        gaps = (
            self.db.query(Gap)
            .filter(Gap.academic_year_id == academic_year_id, Gap.department == department)
            .order_by(Gap.created_at.desc())
            .all()
        )
        for g in gaps:
            ws_gaps.append([
                sanitize_excel_cell(str(g.id)),
                sanitize_excel_cell(g.requirement.code if g.requirement else ""),
                sanitize_excel_cell(g.severity),
                sanitize_excel_cell(g.status),
                sanitize_excel_cell(g.title),
                sanitize_excel_cell(g.description),
                sanitize_excel_cell(g.recommended_action or ""),
                len(g.actions),
            ])

        # Sheet 4: Evidence Inventory
        ws_evidence = wb.create_sheet(title="Evidence Inventory")
        ws_evidence.append([
            sanitize_excel_cell("Document ID"),
            sanitize_excel_cell("Filename"),
            sanitize_excel_cell("MIME Type"),
            sanitize_excel_cell("Processing Status"),
            sanitize_excel_cell("Validation Status"),
            sanitize_excel_cell("Linked Requirements"),
        ])

        docs = (
            self.db.query(Document)
            .filter(
                Document.department == department,
                Document.is_deleted.is_(False),
                (Document.academic_year_id == academic_year_id) | (Document.academic_year_id.is_(None)),
            )
            .all()
        )
        for d in docs:
            linked_reqs = ", ".join([
                el.requirement.code for el in d.evidence_links if el.requirement and el.requirement.code
            ])
            ws_evidence.append([
                sanitize_excel_cell(str(d.id)),
                sanitize_excel_cell(d.original_filename),
                sanitize_excel_cell(d.mime_type),
                sanitize_excel_cell(d.processing_status),
                sanitize_excel_cell(d.validation_status),
                sanitize_excel_cell(linked_reqs),
            ])


        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out

    # -----------------------------------------------------------------------
    # PDF Report Generation
    # -----------------------------------------------------------------------

    def generate_pdf_readiness_report(
        self,
        academic_year_id: uuid.UUID,
        department: str,
    ) -> io.BytesIO:
        """
        Generate bounded PDF report summarizing Digital Twin NBA readiness state.
        """
        snapshot = self.twin_service.get_digital_twin_snapshot(academic_year_id, department)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1B365D"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=12,
        )
        heading2_style = ParagraphStyle(
            "ReportH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1B365D"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )
        disclaimer_style = ParagraphStyle(
            "ReportDisclaimer",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#718096"),
            spaceBefore=10,
        )

        story = []

        # Header
        story.append(Paragraph("AI-NBA Accreditation Readiness System", title_style))
        story.append(Paragraph(
            f"Department: <b>{department}</b> | Academic Year: <b>{snapshot.academic_year}</b><br/>"
            f"Generated: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            subtitle_style,
        ))
        story.append(Spacer(1, 8))

        # Overall Metrics Table
        story.append(Paragraph("1. Overall Readiness Summary", heading2_style))
        pct_display = (
            f"{snapshot.overall.readiness_percentage}%"
            if snapshot.overall.readiness_percentage is not None
            else "N/A (Unevaluated)"
        )
        summary_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Total Requirements", str(snapshot.overall.total_requirements), "Passed Requirements", str(snapshot.overall.passed_requirements)],
            ["Warning Requirements", str(snapshot.overall.warning_requirements), "Failed Requirements", str(snapshot.overall.failed_requirements)],
            ["Not Applicable", str(snapshot.overall.not_applicable_requirements), "Unevaluated", str(snapshot.overall.unevaluated_requirements)],
            ["Internal Readiness Indicator", pct_display, "Open Compliance Gaps", str(snapshot.open_gaps)],
        ]
        t_summary = Table(summary_data, colWidths=[140, 110, 140, 110])
        t_summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A202C")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 10))

        # Criterion Breakdown Table
        story.append(Paragraph("2. Criterion-Wise Readiness Breakdown", heading2_style))
        crit_data = [
            ["Code", "Criterion Name", "Total", "Pass", "Warn", "Fail", "N/A", "Readiness %", "Open Gaps"]
        ]
        for c in snapshot.criteria:
            c_pct = f"{c.readiness_percentage}%" if c.readiness_percentage is not None else "N/A"
            crit_data.append([
                c.criterion_code,
                Paragraph(c.criterion_name[:35], body_style),
                str(c.total_requirements),
                str(c.passed_requirements),
                str(c.warning_requirements),
                str(c.failed_requirements),
                str(c.not_applicable_requirements),
                c_pct,
                str(c.open_gaps),
            ])
        t_crit = Table(crit_data, colWidths=[40, 160, 35, 35, 35, 35, 35, 65, 60])
        t_crit.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(t_crit)
        story.append(Spacer(1, 10))

        # Data Completeness Summary
        story.append(Paragraph("3. Department Data Completeness", heading2_style))
        comp = snapshot.data_completeness
        comp_data = [
            ["Data Dimension", "Count", "Data Dimension", "Count"],
            ["Faculty Profiles", str(comp.faculty_profiles_count), "Faculty Qualifications", str(comp.faculty_qualifications_count)],
            ["Curriculum Subjects", str(comp.subjects_count), "Active Assignments", str(comp.active_subject_assignments_count)],
            ["Students Enrolled", str(comp.students_count), "Course Outcomes (COs)", str(comp.course_outcomes_count)],
            ["CO-PO Mappings", str(comp.co_po_mappings_count), "Assessment Marks Records", str(comp.assessment_marks_count)],
            ["Uploaded Documents", str(comp.uploaded_documents_count), "Validated Documents", str(comp.validated_documents_count)],
        ]
        t_comp = Table(comp_data, colWidths=[140, 110, 140, 110])
        t_comp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(t_comp)
        story.append(Spacer(1, 14))

        # Disclaimer
        story.append(Paragraph(
            "<b>Disclaimer & Methodology:</b> "
            "This report is generated directly from current database entities by the AI-NBA Readiness System. "
            "The readiness indicator reflects deterministic verification against configured criteria rules. "
            "It does NOT constitute an official NBA accreditation score, which is solely determined by an official NBA evaluation team.",
            disclaimer_style,
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
