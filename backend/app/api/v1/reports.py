"""
AI-NBA Readiness System — Backend
app/api/v1/reports.py

Endpoints for exporting PDF and Excel reports.
Enforces formula injection protection, bounded streaming, and proper HTTP content headers.
"""

from __future__ import annotations

import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.academic import AcademicYear
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])


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
            detail="No academic year found.",
        )
    return current


@router.get(
    "/excel",
    summary="Download NBA Readiness Excel Report (.xlsx)",
    response_class=Response,
)
def download_excel_report(
    department: str = Query(default="Computer Science and Engineering", min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Generate and stream an Excel workbook (.xlsx) containing:
      - Readiness Summary
      - Criteria & Requirements Matrix
      - Gaps & Corrective Actions
      - Evidence Inventory
    Formula injection protection is applied to all string cells.
    """
    ay = _resolve_academic_year(db, academic_year_id)
    service = ReportService(db)
    excel_stream = service.generate_excel_readiness_report(
        academic_year_id=ay.id,
        department=department,
    )

    clean_dept = department.replace(" ", "_")
    filename = f"NBA_Readiness_{clean_dept}_{ay.name.replace('/', '-')}.xlsx"

    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/pdf",
    summary="Download NBA Readiness Summary PDF Report (.pdf)",
    response_class=Response,
)
def download_pdf_report(
    department: str = Query(default="Computer Science and Engineering", min_length=2),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Generate and stream a formatted PDF report with executive readiness metrics,
    criterion breakdown tables, data completeness audit, and official NBA disclaimers.
    """
    ay = _resolve_academic_year(db, academic_year_id)
    service = ReportService(db)
    pdf_stream = service.generate_pdf_readiness_report(
        academic_year_id=ay.id,
        department=department,
    )

    clean_dept = department.replace(" ", "_")
    filename = f"NBA_Readiness_Summary_{clean_dept}_{ay.name.replace('/', '-')}.pdf"

    return Response(
        content=pdf_stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
