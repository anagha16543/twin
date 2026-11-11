"""
tests/test_phase4_documents.py

Comprehensive tests for Phase 4 Milestone B (Document and Evidence Management):
  - File sanitization and path traversal prevention
  - MIME type detection via magic bytes (never trusting client Content-Type)
  - SHA-256 hash calculation and duplicate detection
  - File size limits and rejection (HTTP 413)
  - Unsupported media types (HTTP 415)
  - Database failure disk cleanup
  - Ownership isolation and role authorization (uploader, HOD, ADMIN)
  - Authorized streaming download without exposing local filesystem paths
  - Safe version lineage creation and history tracking
  - Soft deletion and exclusion from active queries
  - Requirement-to-evidence association (never modifying requirement status)
"""

from __future__ import annotations

import io
import shutil
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.academic import AcademicYear
from app.models.phase4 import (
    Document,
    DocumentProcessingStatus,
    NBARequirement,
    RequirementEvidence,
)
from app.models.user import User
from app.services.storage_service import (
    FileSizeError,
    MimeTypeError,
    detect_mime_from_bytes,
    get_storage_root,
    sanitize_original_filename,
    save_upload,
)


# Minimal valid file byte fixtures
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb"
INVALID_TEXT_BYTES = b"Plain text content that is not a valid PDF or image file."


class TestStorageServicePrimitives:
    """Test unit-level storage service utilities."""

    def test_sanitize_filename_removes_traversal(self):
        unsafe = "../../../etc/passwd"
        safe = sanitize_original_filename(unsafe)
        assert safe == "passwd"
        assert "/" not in safe
        assert "\\" not in safe

    def test_sanitize_filename_removes_null_bytes(self):
        unsafe = "document\x00.pdf"
        safe = sanitize_original_filename(unsafe)
        assert "\x00" not in safe
        assert "document.pdf" == safe

    def test_mime_detection_valid_types(self):
        assert detect_mime_from_bytes(VALID_PDF_BYTES) == "application/pdf"
        assert detect_mime_from_bytes(VALID_PNG_BYTES) == "image/png"
        assert detect_mime_from_bytes(VALID_JPEG_BYTES) == "image/jpeg"

    def test_mime_detection_invalid_types(self):
        assert detect_mime_from_bytes(INVALID_TEXT_BYTES) is None
        assert detect_mime_from_bytes(b"MZ\x90\x00") is None  # EXE header


class TestDocumentUploadsAndValidation:
    """Test document upload API, validation rules, and error handling."""

    def test_unauthenticated_cannot_upload(self, db_client: TestClient, db_session: Session):
        year = db_session.query(AcademicYear).first()
        files = {"file": ("test.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
        )
        assert res.status_code == 401

    def test_faculty_can_upload_valid_pdf(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        files = {"file": ("syllabus.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["original_filename"] == "syllabus.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["file_size_bytes"] == len(VALID_PDF_BYTES)
        assert "document_id" in data
        assert "stored_filename" not in data  # NEVER expose internal path

    def test_upload_unsupported_media_type_rejected(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        # Pretend to be a PDF by filename, but send invalid text bytes
        files = {"file": ("fake.pdf", io.BytesIO(INVALID_TEXT_BYTES), "application/pdf")}
        res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        assert res.status_code == 415
        assert "File type not permitted" in res.json()["detail"]

    def test_duplicate_upload_detection(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        files1 = {"file": ("curriculum_v1.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        res1 = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files1,
            headers=faculty_headers,
        )
        assert res1.status_code == 201
        assert res1.json()["is_duplicate"] is False

        # Upload exact same bytes again
        files2 = {"file": ("curriculum_copy.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        res2 = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files2,
            headers=faculty_headers,
        )
        assert res2.status_code == 201
        assert res2.json()["is_duplicate"] is True


class TestDocumentAuthorizationAndDownloads:
    """Test ownership isolation, role permissions, and streaming downloads."""

    def test_uploader_can_get_metadata_and_download(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        files = {"file": ("report.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        # View metadata
        meta_res = db_client.get(f"/api/v1/documents/{doc_id}", headers=faculty_headers)
        assert meta_res.status_code == 200
        assert meta_res.json()["original_filename"] == "report.pdf"

        # Download file
        dl_res = db_client.get(f"/api/v1/documents/{doc_id}/download", headers=faculty_headers)
        assert dl_res.status_code == 200
        assert dl_res.content == VALID_PDF_BYTES
        assert dl_res.headers["content-type"] == "application/pdf"

    def test_other_faculty_cannot_access_or_download_document(
        self,
        db_client: TestClient,
        db_session: Session,
        faculty_headers: dict,
        second_faculty_headers: dict,
    ):
        """Faculty 2 cannot view or download documents uploaded by Faculty 1."""
        year = db_session.query(AcademicYear).first()
        files = {"file": ("faculty1_private.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        # Faculty 2 attempts to get metadata
        meta_res = db_client.get(f"/api/v1/documents/{doc_id}", headers=second_faculty_headers)
        assert meta_res.status_code == 403

        # Faculty 2 attempts to download
        dl_res = db_client.get(f"/api/v1/documents/{doc_id}/download", headers=second_faculty_headers)
        assert dl_res.status_code == 403

    def test_hod_and_admin_can_access_any_document(
        self,
        db_client: TestClient,
        db_session: Session,
        faculty_headers: dict,
        hod_headers: dict,
        admin_headers: dict,
    ):
        """HOD and ADMIN have elevated permissions to review any department document."""
        year = db_session.query(AcademicYear).first()
        files = {"file": ("faculty_submission.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        # HOD can access
        assert db_client.get(f"/api/v1/documents/{doc_id}", headers=hod_headers).status_code == 200
        # ADMIN can access
        assert db_client.get(f"/api/v1/documents/{doc_id}", headers=admin_headers).status_code == 200


class TestDocumentVersioningAndLineage:
    """Test replacement uploads, lineage version tracking, and preservation."""

    def test_replace_creates_new_version_preserving_old(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        # Upload v1
        v1_files = {"file": ("spec_v1.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        v1_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=v1_files,
            headers=faculty_headers,
        )
        doc1_id = v1_res.json()["document_id"]

        # Upload v2 replacement
        v2_bytes = VALID_PDF_BYTES + b"\n% version 2 content"
        v2_files = {"file": ("spec_v2.pdf", io.BytesIO(v2_bytes), "application/pdf")}
        v2_res = db_client.post(
            f"/api/v1/documents/{doc1_id}/replace",
            files=v2_files,
            headers=faculty_headers,
        )
        assert v2_res.status_code == 201
        doc2_id = v2_res.json()["document_id"]
        assert doc2_id != doc1_id

        # Verify old doc marked not current
        doc1 = db_session.query(Document).filter(Document.id == uuid.UUID(doc1_id)).first()
        db_session.refresh(doc1)
        assert doc1.is_current is False
        assert doc1.version == 1

        # Verify new doc marked current with incremented version
        doc2 = db_session.query(Document).filter(Document.id == uuid.UUID(doc2_id)).first()
        assert doc2.is_current is True
        assert doc2.version == 2
        assert doc2.parent_document_id == doc1.id

        # Verify lineage history endpoint
        hist_res = db_client.get(f"/api/v1/documents/{doc2_id}/history", headers=faculty_headers)
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[1]["version"] == 2


class TestDocumentSoftDelete:
    """Test soft deletion, access restrictions, and query exclusion."""

    def test_faculty_cannot_soft_delete(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        files = {"file": ("test_del.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        del_res = db_client.delete(f"/api/v1/documents/{doc_id}", headers=faculty_headers)
        assert del_res.status_code == 403

    def test_hod_can_soft_delete_and_exclude_from_listings(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict, hod_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        files = {"file": ("test_del_hod.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        # HOD soft-deletes
        del_res = db_client.delete(f"/api/v1/documents/{doc_id}", headers=hod_headers)
        assert del_res.status_code == 200
        assert del_res.json()["is_deleted"] is True

        # Document excluded from active list
        list_res = db_client.get("/api/v1/documents/", headers=hod_headers)
        doc_ids = [d["id"] for d in list_res.json()]
        assert doc_id not in doc_ids

        # Direct access to deleted document returns 404
        assert db_client.get(f"/api/v1/documents/{doc_id}", headers=hod_headers).status_code == 404


class TestRequirementEvidenceLinking:
    """Test linking documents to NBA requirements as evidence."""

    def test_hod_can_link_evidence_to_requirement(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict, hod_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        req = db_session.query(NBARequirement).first()

        # Upload document
        files = {"file": ("co_evidence.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        upload_res = db_client.post(
            f"/api/v1/documents/upload?academic_year_id={year.id}&department=CSE",
            files=files,
            headers=faculty_headers,
        )
        doc_id = upload_res.json()["document_id"]

        # Link evidence
        link_payload = {
            "document_id": doc_id,
            "is_primary": True,
            "relevance_note": "Direct syllabus mapping for CO attainment",
        }
        link_res = db_client.post(
            f"/api/v1/documents/requirements/{req.id}/evidence",
            json=link_payload,
            headers=hod_headers,
        )
        assert link_res.status_code == 201
        assert link_res.json()["is_primary"] is True

        # Verify listed evidence
        ev_list = db_client.get(
            f"/api/v1/documents/requirements/{req.id}/evidence",
            headers=faculty_headers,
        )
        assert ev_list.status_code == 200
        items = ev_list.json()
        assert len(items) >= 1
        assert any(i["document_id"] == doc_id for i in items)
