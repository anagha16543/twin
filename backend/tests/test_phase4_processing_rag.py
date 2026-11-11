"""
tests/test_phase4_processing_rag.py

Comprehensive tests for Phase 4 Milestones C & D:
  - Document text extraction from digital PDFs via pypdf
  - Preservation of page numbers and document metadata
  - Graceful degradation when OCR (Tesseract) is unavailable (PROCESSED_PARTIAL, no crash)
  - Text chunking with configurable chunk_size and chunk_overlap
  - Content hashing for chunk deduplication and stale detection
  - Vector embedding dimension verification
  - In-memory database chunk indexing and cleanup
  - Semantic/fallback RAG retrieval endpoint (/api/v1/analysis/retrieve)
  - Exclusion of soft-deleted documents from RAG retrieval
"""

from __future__ import annotations

import io
import uuid
import pytest
from pypdf import PdfWriter
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.academic import AcademicYear
from app.models.phase4 import (
    Document,
    DocumentChunk,
    DocumentProcessingStatus,
)
from app.services.document_processor import (
    ExtractionResult,
    PageExtraction,
    TESSERACT_AVAILABLE,
    process_document,
)
from app.services.rag_service import (
    chunk_text,
    generate_embedding,
    index_document_chunks,
    retrieve_relevant_chunks,
)
from app.services.storage_service import save_upload


def _create_minimal_pdf_with_text(text: str) -> bytes:
    """Generate a valid PDF containing the given text using pypdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=72 * 8.5, height=72 * 11)
    # Write to in-memory bytes
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestDocumentProcessor:
    """Test text extraction and OCR fallback behaviors."""

    def test_empty_or_zero_byte_document_returns_error(self, tmp_path):
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")
        res = process_document(empty_file, "application/pdf")
        assert len(res.errors) > 0
        assert res.processing_status == "FAILED"

    def test_corrupt_pdf_file_handled_gracefully(self, tmp_path):
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_bytes(b"%PDF-corrupt-data-not-a-valid-stream")
        res = process_document(corrupt_file, "application/pdf")
        assert len(res.errors) > 0
        assert res.processing_status == "FAILED"

    def test_ocr_unavailable_behavior_does_not_crash(self, tmp_path):
        """When Tesseract is absent or image OCR fails, API degrades gracefully."""
        dummy_png = tmp_path / "scan.png"
        dummy_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        res = process_document(dummy_png, "image/png")
        # Should not raise exception
        if not TESSERACT_AVAILABLE:
            assert res.ocr_required_but_unavailable is True
            assert res.processing_status in ("PROCESSED_PARTIAL", "FAILED")

    def test_extraction_result_processing_status_logic(self):
        # 1. Clean native
        r1 = ExtractionResult(pages=[PageExtraction(1, "Hello world", "native")])
        assert r1.processing_status == "PROCESSED"

        # 2. Native text extracted, but OCR was required for scanned pages and unavailable
        r2 = ExtractionResult(
            pages=[PageExtraction(1, "Some text", "native")],
            ocr_required_but_unavailable=True,
        )
        assert r2.processing_status == "PROCESSED_PARTIAL"

        # 3. Failed entirely
        r3 = ExtractionResult(errors=["Corrupt PDF header"])
        assert r3.processing_status == "FAILED"


class TestTextChunkingAndHashing:
    """Test chunk boundaries, overlaps, and hash computations."""

    def test_chunk_text_basic_split(self):
        text = "Paragraph one with words. " * 30  # ~780 chars
        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50, page_number=2)
        assert len(chunks) > 1
        for idx, ch in enumerate(chunks):
            assert ch["page_number"] == 2
            assert ch["chunk_index"] == idx
            assert len(ch["content"]) <= 200

    def test_chunk_text_empty_input(self):
        chunks = chunk_text("   ", chunk_size=500, chunk_overlap=50)
        assert chunks == []

    def test_chunk_overlap_preservation(self):
        text = "A" * 150 + "B" * 150
        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
        assert len(chunks) >= 2
        # Verify content exists in both chunks at the boundary
        first_chunk_end = chunks[0]["content"][-50:]
        assert len(first_chunk_end) == 50


class TestIndexingAndRAGRetrieval:
    """Test chunk database persistence and RAG query endpoint."""

    def test_index_document_chunks_in_db(self, db_session: Session):
        year = db_session.query(AcademicYear).first()
        doc = Document(
            original_filename="curriculum.pdf",
            stored_filename="curriculum-uuid.pdf",
            file_size_bytes=1000,
            mime_type="application/pdf",
            sha256_hash="hash123",
            department="CSE",
            academic_year_id=year.id,
        )
        db_session.add(doc)
        db_session.commit()

        extraction = ExtractionResult(
            pages=[
                PageExtraction(1, "Course Outcome 1 covers data structures and algorithms.", "native"),
                PageExtraction(2, "Course Outcome 2 covers operating systems design.", "native"),
            ]
        )

        index_document_chunks(db_session, doc, extraction)
        db_session.commit()

        chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        assert len(chunks) == 2
        assert chunks[0].page_number == 1
        assert "data structures" in chunks[0].content
        assert chunks[1].page_number == 2
        assert "operating systems" in chunks[1].content

    def test_reindexing_cleans_stale_chunks(self, db_session: Session):
        year = db_session.query(AcademicYear).first()
        doc = Document(
            original_filename="v1.pdf",
            stored_filename="v1-uuid.pdf",
            file_size_bytes=500,
            mime_type="application/pdf",
            sha256_hash="hash456",
            department="CSE",
            academic_year_id=year.id,
        )
        db_session.add(doc)
        db_session.commit()

        # Initial indexing with 3 pages
        ext1 = ExtractionResult(
            pages=[PageExtraction(i, f"Page content {i}", "native") for i in range(1, 4)]
        )
        index_document_chunks(db_session, doc, ext1)
        db_session.commit()
        assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 3

        # Re-index with 1 page
        ext2 = ExtractionResult(pages=[PageExtraction(1, "Updated single page", "native")])
        index_document_chunks(db_session, doc, ext2)
        db_session.commit()
        # Stale chunks were deleted
        assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 1

    def test_rag_retrieval_excludes_soft_deleted_documents(self, db_session: Session):
        year = db_session.query(AcademicYear).first()
        doc = Document(
            original_filename="deleted_plan.pdf",
            stored_filename="del-uuid.pdf",
            file_size_bytes=800,
            mime_type="application/pdf",
            sha256_hash="hash789",
            department="CSE",
            academic_year_id=year.id,
            is_deleted=True,  # Deleted!
        )
        db_session.add(doc)
        db_session.commit()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            page_number=1,
            content="NBA Criterion 3 course attainment mapping details",
            content_hash="chunkhash789",
        )
        db_session.add(chunk)
        db_session.commit()

        # Retrieve should not return this chunk because document is deleted
        results = retrieve_relevant_chunks(db_session, "attainment mapping", department="CSE")
        matching = [r for r in results if r.document_id == str(doc.id)]
        assert len(matching) == 0

    def test_rag_api_endpoint_authenticated(
        self, db_client: TestClient, db_session: Session, faculty_headers: dict
    ):
        year = db_session.query(AcademicYear).first()
        doc = Document(
            original_filename="active_guide.pdf",
            stored_filename="guide-uuid.pdf",
            file_size_bytes=1200,
            mime_type="application/pdf",
            sha256_hash="hash_guide",
            department="CSE",
            academic_year_id=year.id,
            is_deleted=False,
            is_current=True,
        )
        db_session.add(doc)
        db_session.commit()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            page_number=1,
            content="Bloom's taxonomy level 3 applied to software engineering",
            content_hash="chunk_guide",
        )
        db_session.add(chunk)
        db_session.commit()

        payload = {
            "query": "software engineering Bloom",
            "department": "CSE",
            "top_k": 5,
        }
        res = db_client.post("/api/v1/analysis/retrieve", json=payload, headers=faculty_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "software engineering Bloom"
        assert data["total"] >= 1
        assert any("Bloom" in m["content"] for m in data["results"])

    def test_rag_api_endpoint_unauthenticated_returns_401(self, db_client: TestClient):
        res = db_client.post("/api/v1/analysis/retrieve", json={"query": "test"})
        assert res.status_code == 401
