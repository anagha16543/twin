"""
AI-NBA Readiness System — Backend
app/api/v1/documents.py

Document upload, download, metadata, versioning, and evidence association.

Authorization model:
    - Upload/create:      any ACTIVE authenticated user for their own department
    - Download/metadata:  uploader, HOD, or ADMIN
    - Soft-delete:        HOD or ADMIN
    - Validate:           HOD or ADMIN
    - Evidence linking:   HOD or ADMIN

Security:
    - MIME type detected from file bytes, not client header.
    - stored_filename is NEVER returned in any API response.
    - Downloads stream file bytes from the storage root; paths are resolved
      and checked against the storage root to prevent traversal.
    - File is deleted from disk if the DB transaction fails.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.academic import AcademicYear
from app.models.phase4 import (
    Document,
    DocumentProcessingStatus,
    DocumentValidationStatus,
    NBARequirement,
    RequirementEvidence,
)
from app.models.user import User, UserRoleName
from app.schemas.phase4 import (
    DocumentOut,
    DocumentSoftDeleteOut,
    DocumentUploadResponse,
    RequirementEvidenceLinkIn,
    RequirementEvidenceOut,
)
from app.services import storage_service
from app.services.storage_service import (
    FileSizeError,
    MimeTypeError,
    ValidationError,
    delete_stored_file,
    get_stored_file_path,
    save_upload,
)

router = APIRouter(prefix="/documents", tags=["Documents & Evidence"])


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------

def _is_hod_or_admin(user: User) -> bool:
    return user.has_role(UserRoleName.HOD.value) or user.has_role(UserRoleName.ADMIN.value)


def _assert_document_access(doc: Document, user: User) -> None:
    """
    Allow access if: user is HOD/ADMIN, or is the document uploader.
    Raises HTTP 403 otherwise.
    """
    if _is_hod_or_admin(user):
        return
    if doc.uploaded_by_user_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not authorized to access this document.",
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an evidence document",
)
def upload_document(
    file: UploadFile = File(...),
    academic_year_id: uuid.UUID = Query(...),
    department: str = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an evidence document.

    Allowed types: PDF, PNG, JPEG. Max size: 25 MB (configurable).
    MIME type is detected from file bytes; the client-supplied type is ignored.
    File is stored only after all validation passes.
    Metadata is written to DB in a single transaction.
    If the DB commit fails, the stored file is cleaned up.
    """
    # Verify academic year
    year = db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found.")

    # Validate and persist file
    try:
        stored = save_upload(
            file=file,
            department=department,
            academic_year_name=year.name,
        )
    except FileSizeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
    except MimeTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Duplicate detection (same hash, active, same dept/year)
    duplicate = (
        db.query(Document)
        .filter(
            Document.sha256_hash == stored["sha256_hash"],
            Document.department == department,
            Document.academic_year_id == academic_year_id,
            Document.is_deleted.is_(False),
            Document.is_current.is_(True),
        )
        .first()
    )
    is_duplicate = duplicate is not None

    doc = Document(
        original_filename=stored["original_filename"],
        stored_filename=stored["stored_filename"],
        file_size_bytes=stored["file_size_bytes"],
        mime_type=stored["mime_type"],
        sha256_hash=stored["sha256_hash"],
        department=department,
        academic_year_id=academic_year_id,
        uploaded_by_user_id=current_user.id,
    )
    db.add(doc)
    try:
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        delete_stored_file(stored["stored_filename"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document metadata could not be saved. Storage file has been removed.",
        )

    # Schedule background processing
    background_tasks.add_task(_process_document_bg, str(doc.id), doc.stored_filename, doc.mime_type)

    return DocumentUploadResponse(
        document_id=doc.id,
        original_filename=stored["original_filename"],
        file_size_bytes=stored["file_size_bytes"],
        mime_type=stored["mime_type"],
        sha256_hash=stored["sha256_hash"],
        is_duplicate=is_duplicate,
        processing_status=doc.processing_status,
        message="Document uploaded successfully. Processing queued.",
    )


# ---------------------------------------------------------------------------
# Background processing task
# ---------------------------------------------------------------------------

def _process_document_bg(document_id: str, stored_filename: str, mime_type: str) -> None:
    """
    Background task: extract text, chunk, and index the document.
    Runs after HTTP response is sent.
    """
    from app.db.session import SessionLocal
    from app.services.document_processor import process_document
    from app.services.rag_service import index_document_chunks
    from app.services.storage_service import get_stored_file_path

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if not doc:
            return

        doc.processing_status = DocumentProcessingStatus.PROCESSING.value
        db.commit()

        file_path = get_stored_file_path(stored_filename)
        extraction = process_document(file_path, mime_type)

        doc.processing_status = extraction.processing_status
        db.commit()

        if extraction.pages:
            index_document_chunks(db, doc, extraction)
            db.commit()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Background processing failed for document %s: %s", document_id, exc
        )
        try:
            doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
            if doc:
                doc.processing_status = DocumentProcessingStatus.FAILED.value
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# List documents
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=List[DocumentOut],
    summary="List documents (active, non-deleted)",
)
def list_documents(
    department: Optional[str] = Query(default=None),
    academic_year_id: Optional[uuid.UUID] = Query(default=None),
    processing_status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Document).filter(
        Document.is_deleted.is_(False),
        Document.is_current.is_(True),
    )

    # Non-HOD/Admin: restrict to own uploads
    if not _is_hod_or_admin(current_user):
        q = q.filter(Document.uploaded_by_user_id == current_user.id)

    if department:
        q = q.filter(Document.department == department)
    if academic_year_id:
        q = q.filter(Document.academic_year_id == academic_year_id)
    if processing_status:
        q = q.filter(Document.processing_status == processing_status)

    return q.order_by(Document.created_at.desc()).limit(limit).all()


# ---------------------------------------------------------------------------
# Get metadata
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Get document metadata",
)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    _assert_document_access(doc, current_user)
    return doc


# ---------------------------------------------------------------------------
# Authorized download (stream bytes)
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}/download",
    summary="Download document file",
)
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream document file bytes. The stored filesystem path is never exposed.
    The path is resolved and checked to remain within the storage root.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    _assert_document_access(doc, current_user)

    try:
        file_path = get_stored_file_path(doc.stored_filename)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Document storage path error.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on storage.")

    def _stream():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        _stream(),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
        },
    )


# ---------------------------------------------------------------------------
# Soft deletion
# ---------------------------------------------------------------------------

@router.delete(
    "/{document_id}",
    response_model=DocumentSoftDeleteOut,
    summary="Soft-delete a document",
)
def soft_delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.is_deleted:
        raise HTTPException(status_code=409, detail="Document is already deleted.")

    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)
    doc.deleted_by_user_id = current_user.id
    db.commit()

    return DocumentSoftDeleteOut(
        document_id=document_id,
        is_deleted=True,
        message="Document soft-deleted. Historical metadata is preserved.",
    )


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}/history",
    response_model=List[DocumentOut],
    summary="Get version history for a document lineage",
)
def get_document_history(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all versions in the document lineage (oldest first)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    _assert_document_access(doc, current_user)

    # Walk to root
    root_id = document_id
    current = doc
    while current.parent_document_id:
        parent = db.query(Document).filter(Document.id == current.parent_document_id).first()
        if not parent:
            break
        root_id = parent.id
        current = parent

    # Collect entire lineage
    lineage = []
    next_id: Optional[uuid.UUID] = root_id
    visited = set()
    while next_id and next_id not in visited:
        visited.add(next_id)
        node = db.query(Document).filter(Document.id == next_id).first()
        if not node:
            break
        lineage.append(node)
        # Find child
        child = (
            db.query(Document)
            .filter(Document.parent_document_id == next_id)
            .first()
        )
        next_id = child.id if child else None

    return lineage


# ---------------------------------------------------------------------------
# Create new version
# ---------------------------------------------------------------------------

@router.post(
    "/{document_id}/replace",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new version of an existing document",
)
def replace_document(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    old_doc = db.query(Document).filter(Document.id == document_id).first()
    if not old_doc or old_doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    _assert_document_access(old_doc, current_user)

    year = db.query(AcademicYear).filter(AcademicYear.id == old_doc.academic_year_id).first()

    try:
        stored = save_upload(
            file=file,
            department=old_doc.department,
            academic_year_name=year.name if year else "unknown",
        )
    except FileSizeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except MimeTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Mark old version as no longer current
    old_doc.is_current = False

    new_doc = Document(
        original_filename=stored["original_filename"],
        stored_filename=stored["stored_filename"],
        file_size_bytes=stored["file_size_bytes"],
        mime_type=stored["mime_type"],
        sha256_hash=stored["sha256_hash"],
        department=old_doc.department,
        academic_year_id=old_doc.academic_year_id,
        uploaded_by_user_id=current_user.id,
        version=old_doc.version + 1,
        is_current=True,
        parent_document_id=old_doc.id,
    )
    db.add(new_doc)
    try:
        db.commit()
        db.refresh(new_doc)
    except Exception:
        db.rollback()
        delete_stored_file(stored["stored_filename"])
        raise HTTPException(status_code=500, detail="Could not save new document version.")

    background_tasks.add_task(
        _process_document_bg, str(new_doc.id), new_doc.stored_filename, new_doc.mime_type
    )

    return DocumentUploadResponse(
        document_id=new_doc.id,
        original_filename=stored["original_filename"],
        file_size_bytes=stored["file_size_bytes"],
        mime_type=stored["mime_type"],
        sha256_hash=stored["sha256_hash"],
        is_duplicate=False,
        processing_status=new_doc.processing_status,
        message=f"New version {new_doc.version} uploaded successfully.",
    )


# ---------------------------------------------------------------------------
# Evidence Association
# ---------------------------------------------------------------------------

@router.post(
    "/requirements/{requirement_id}/evidence",
    response_model=RequirementEvidenceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Link a document to a requirement as evidence",
)
def link_evidence(
    requirement_id: uuid.UUID,
    body: RequirementEvidenceLinkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    """
    Associate an uploaded document with an NBA requirement.
    This does NOT change the requirement evaluation status.
    """
    req = db.query(NBARequirement).filter(NBARequirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found.")

    doc = db.query(Document).filter(
        Document.id == body.document_id,
        Document.is_deleted.is_(False),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or deleted.")

    existing = (
        db.query(RequirementEvidence)
        .filter(
            RequirementEvidence.requirement_id == requirement_id,
            RequirementEvidence.document_id == body.document_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Document is already linked to this requirement.")

    link = RequirementEvidence(
        requirement_id=requirement_id,
        document_id=body.document_id,
        is_primary=body.is_primary,
        relevance_note=body.relevance_note,
        linked_by_user_id=current_user.id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get(
    "/requirements/{requirement_id}/evidence",
    response_model=List[RequirementEvidenceOut],
    summary="List evidence documents linked to a requirement",
)
def list_requirement_evidence(
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return (
        db.query(RequirementEvidence)
        .filter(RequirementEvidence.requirement_id == requirement_id)
        .all()
    )


# ---------------------------------------------------------------------------
# HOD verification of evidence (frontend integration)
# ---------------------------------------------------------------------------

from pydantic import BaseModel as _BaseModel, Field as _Field  # noqa: E402


class DocumentValidationUpdateIn(_BaseModel):
    validation_status: str = _Field(pattern="^(PENDING_REVIEW|VALIDATED|REJECTED)$")


@router.patch(
    "/{document_id}/validation",
    response_model=DocumentOut,
    summary="HOD/Admin: set the verification status of an evidence document",
)
def update_document_validation(
    document_id: uuid.UUID,
    body: DocumentValidationUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.HOD.value, UserRoleName.ADMIN.value)),
):
    """
    Mark an uploaded evidence document as VALIDATED, REJECTED or PENDING_REVIEW.
    This never changes a requirement's evaluation status — evaluation remains
    deterministic. It only feeds the 'verified evidence' readiness indicator.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.is_deleted.is_(False),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or deleted.")
    doc.validation_status = body.validation_status
    if body.validation_status == "PENDING_REVIEW":
        doc.validated_by_user_id = None
        doc.validated_at = None
    else:
        doc.validated_by_user_id = current_user.id
        doc.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return doc
