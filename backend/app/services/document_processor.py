"""
AI-NBA Readiness System — Backend
app/services/document_processor.py

Document text extraction and OCR service.

Capabilities
------------
* Page-by-page text extraction from digital PDFs using pypdf.
* OCR fallback via pytesseract when Tesseract executable is detected.
* Image-file text extraction (PNG, JPEG) via OCR.
* Graceful degradation: if Tesseract is not installed, native PDF text
  is preserved and the document is marked PROCESSED_PARTIAL.

External dependencies
---------------------
* pypdf          — pure-Python PDF parser (Python 3.14 compatible)
* pytesseract    — Tesseract wrapper (requires system ``tesseract`` binary)
* Pillow         — image handling for OCR

Never crash the API when optional native executables are absent.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tesseract availability detection (checked once at module load)
# ---------------------------------------------------------------------------

def _tesseract_available() -> bool:
    """Return True if the tesseract executable is found on PATH."""
    return shutil.which("tesseract") is not None


TESSERACT_AVAILABLE = _tesseract_available()

if TESSERACT_AVAILABLE:
    logger.info("Tesseract executable found — OCR is available.")
else:
    logger.warning(
        "Tesseract executable NOT found. OCR will be unavailable. "
        "Install tesseract-ocr and ensure it is on the system PATH."
    )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageExtraction:
    """Text content extracted from a single page."""
    page_number: int         # 1-indexed
    text: str
    extraction_method: str   # "native" | "ocr" | "empty"
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


@dataclass
class ExtractionResult:
    """Result of processing one document file."""
    pages: list[PageExtraction] = field(default_factory=list)
    total_pages: int = 0
    ocr_pages: int = 0
    native_pages: int = 0
    empty_pages: int = 0
    ocr_available: bool = TESSERACT_AVAILABLE
    ocr_required_but_unavailable: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def processing_status(self) -> str:
        """
        Return the appropriate DocumentProcessingStatus value string.
        Matches values in app.models.phase4.DocumentProcessingStatus.
        """
        if self.errors and not self.pages:
            return "FAILED"
        if self.ocr_required_but_unavailable:
            return "PROCESSED_PARTIAL"
        return "PROCESSED"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_OCR_WORD_THRESHOLD = 20  # pages with fewer words trigger OCR


def _extract_with_ocr(image) -> str:
    """Run pytesseract on a PIL image; returns extracted text."""
    try:
        import pytesseract  # type: ignore
        return pytesseract.image_to_string(image)
    except Exception as exc:
        logger.warning("OCR extraction error: %s", exc)
        return ""


def _page_to_image(page):
    """Convert a pypdf page to a PIL Image for OCR."""
    try:
        from PIL import Image  # type: ignore
        import io
        images = list(page.images)
        if images:
            return Image.open(io.BytesIO(images[0].data))
        # Render page using pypdf''s page rendering (text-based only fallback)
        return None
    except Exception as exc:
        logger.debug("Could not convert page to image: %s", exc)
        return None


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf(file_path: Path) -> ExtractionResult:
    """
    Extract text from a PDF file page by page.

    For each page:
      1. Attempt native text extraction via pypdf.
      2. If word count < threshold AND Tesseract is available, apply OCR.
      3. If word count < threshold AND Tesseract is unavailable, mark page
         as requiring OCR and set the result flag.
    """
    result = ExtractionResult()

    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        result.errors.append("pypdf is not installed. Cannot extract PDF text.")
        return result

    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        result.errors.append(f"Cannot open PDF: {exc}")
        return result

    result.total_pages = len(reader.pages)

    for i, page in enumerate(reader.pages):
        page_number = i + 1
        try:
            native_text = page.extract_text() or ""
        except Exception as exc:
            native_text = ""
            result.errors.append(f"Page {page_number} native extraction error: {exc}")

        word_count = len(native_text.split())

        if word_count >= _OCR_WORD_THRESHOLD:
            result.pages.append(PageExtraction(
                page_number=page_number,
                text=native_text.strip(),
                extraction_method="native",
            ))
            result.native_pages += 1
        else:
            # Attempt OCR
            if TESSERACT_AVAILABLE:
                img = _page_to_image(page)
                if img:
                    ocr_text = _extract_with_ocr(img)
                    text = ocr_text.strip() if ocr_text.strip() else native_text.strip()
                    method = "ocr"
                    result.ocr_pages += 1
                else:
                    text = native_text.strip()
                    method = "native"
                    result.native_pages += 1
            else:
                # Tesseract not available — use what native extraction found
                text = native_text.strip()
                method = "native"
                result.native_pages += 1
                if word_count < _OCR_WORD_THRESHOLD:
                    result.ocr_required_but_unavailable = True

            if text:
                result.pages.append(PageExtraction(
                    page_number=page_number,
                    text=text,
                    extraction_method=method,
                ))
            else:
                result.pages.append(PageExtraction(
                    page_number=page_number,
                    text="",
                    extraction_method="empty",
                ))
                result.empty_pages += 1

    return result


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def extract_image(file_path: Path) -> ExtractionResult:
    """
    Extract text from a supported image file (PNG, JPEG) via OCR.
    """
    result = ExtractionResult()
    result.total_pages = 1

    if not TESSERACT_AVAILABLE:
        result.ocr_required_but_unavailable = True
        result.errors.append(
            "Tesseract is not installed. Cannot extract text from image files."
        )
        result.pages.append(PageExtraction(
            page_number=1, text="", extraction_method="empty"
        ))
        result.empty_pages = 1
        return result

    try:
        from PIL import Image  # type: ignore
        img = Image.open(str(file_path))
    except Exception as exc:
        result.errors.append(f"Cannot open image: {exc}")
        return result

    text = _extract_with_ocr(img)
    result.ocr_pages = 1
    result.pages.append(PageExtraction(
        page_number=1,
        text=text.strip(),
        extraction_method="ocr",
    ))
    return result


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def process_document(file_path: Path, mime_type: str) -> ExtractionResult:
    """
    Process a document file and return an ExtractionResult.

    Dispatches to:
      - extract_pdf   for application/pdf
      - extract_image for image/png and image/jpeg
    """
    if mime_type == "application/pdf":
        return extract_pdf(file_path)
    elif mime_type in ("image/png", "image/jpeg"):
        return extract_image(file_path)
    else:
        result = ExtractionResult()
        result.errors.append(f"Unsupported MIME type for extraction: {mime_type}")
        return result
