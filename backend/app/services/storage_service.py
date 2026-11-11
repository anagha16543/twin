"""
AI-NBA Readiness System — Backend
app/services/storage_service.py

Safe local file storage for uploaded evidence documents.

Security guarantees
-------------------
* Client-supplied filenames are sanitized; path traversal is blocked.
* MIME type is detected from file content (magic bytes), never from the
  client Content-Type header or filename extension alone.
* SHA-256 hash is computed from the stored bytes for deduplication.
* File bytes are written to disk only after sanitization; if the DB
  transaction that follows fails, the written file is removed.
* Storage root is configurable via DOCUMENT_STORAGE_ROOT in settings;
  defaults to <project_root>/documents/uploads.
* Stored filenames are UUIDs, never the original filename.
* Internal stored paths are never returned in API responses.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

from fastapi import UploadFile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Allowed MIME types and magic-byte signatures
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}

# Magic byte signatures for each allowed type
_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB default


def detect_mime_from_bytes(header: bytes) -> Optional[str]:
    """Return the MIME type detected from the first bytes, or None."""
    for signature, mime in _MAGIC_BYTES:
        if header[: len(signature)] == signature:
            return mime
    return None


# ---------------------------------------------------------------------------
# Sanitize filename (path traversal protection)
# ---------------------------------------------------------------------------

def sanitize_original_filename(name: str) -> str:
    """
    Strip directory components and null bytes from an uploaded filename.
    Returns only the basename, replacing any problematic characters.
    """
    name = name.replace("\x00", "")
    name = Path(name).name  # take only basename — blocks ../../../etc
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name or "unnamed_file"


# ---------------------------------------------------------------------------
# Compute SHA-256 hash of a byte stream
# ---------------------------------------------------------------------------

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Derive the storage root from settings
# ---------------------------------------------------------------------------

def get_storage_root() -> Path:
    """Return the configured document storage root directory."""
    from app.core.config import get_settings
    settings = get_settings()
    root_str = getattr(settings, "DOCUMENT_STORAGE_ROOT", None)
    if root_str:
        root = Path(root_str)
    else:
        # Default: <repo_root>/documents/uploads
        root = Path(__file__).resolve().parents[3] / "documents" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------------------------------------------------------------------------
# Main save function — returns metadata dict
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when a file fails upload validation."""


class FileSizeError(ValidationError):
    """Raised when the file exceeds the size limit."""


class MimeTypeError(ValidationError):
    """Raised when the file type is not permitted."""


def save_upload(
    file: UploadFile,
    department: str,
    academic_year_name: str,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
) -> dict:
    """
    Validate and persist an uploaded file to local storage.

    Returns a dict with:
        stored_filename : str  — relative path under storage root (never expose)
        original_filename: str — sanitized original name
        file_size_bytes : int
        mime_type       : str  — detected from content
        sha256_hash     : str

    Raises:
        FileSizeError  if content exceeds max_size_bytes
        MimeTypeError  if content is not an allowed type
        ValidationError on other issues
    """
    safe_name = sanitize_original_filename(file.filename or "")
    ext = Path(safe_name).suffix.lower()

    # Read entire content to memory for hashing + magic-byte detection
    # (safe for =25 MB; adjust to streaming if limit is raised significantly)
    data = file.file.read()
    file.file.seek(0)

    if len(data) > max_size_bytes:
        raise FileSizeError(
            f"File '{safe_name}' exceeds maximum size "
            f"({len(data)} bytes > {max_size_bytes} bytes)."
        )

    if len(data) == 0:
        raise ValidationError("Uploaded file is empty.")

    # Detect MIME from magic bytes
    detected_mime = detect_mime_from_bytes(data[:16])
    if detected_mime is None or detected_mime not in ALLOWED_MIME_TYPES:
        raise MimeTypeError(
            f"File type not permitted. Detected MIME: {detected_mime!r}. "
            f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
        )

    sha256 = compute_sha256(data)

    # Build storage sub-path: department/academic_year/
    safe_dept = department.strip().lower().replace(" ", "_").replace("/", "_")[:50]
    safe_year = academic_year_name.strip().replace("/", "-").replace(" ", "_")[:20]
    stored_filename = f"{safe_dept}/{safe_year}/{uuid.uuid4()}{ext}"

    storage_root = get_storage_root()
    dest_path = storage_root / stored_filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        dest_path.write_bytes(data)
    except OSError as exc:
        raise ValidationError(f"Could not write file to storage: {exc}") from exc

    return {
        "stored_filename": stored_filename,
        "original_filename": safe_name,
        "file_size_bytes": len(data),
        "mime_type": detected_mime,
        "sha256_hash": sha256,
    }


def delete_stored_file(stored_filename: str) -> None:
    """
    Remove a stored file from disk (used for cleanup on DB transaction failure).
    Silently ignores missing files.
    """
    try:
        storage_root = get_storage_root()
        path = storage_root / stored_filename
        if path.exists():
            path.unlink()
            logger.debug("Deleted stored file: %s", stored_filename)
    except OSError as exc:
        logger.warning("Could not delete stored file %s: %s", stored_filename, exc)


def get_stored_file_path(stored_filename: str) -> Path:
    """
    Resolve the absolute path for a stored file.
    Used only by authorized download endpoints — never expose the path string.
    """
    storage_root = get_storage_root()
    path = (storage_root / stored_filename).resolve()
    # Guard: ensure the resolved path is still under the storage root
    if not str(path).startswith(str(storage_root.resolve())):
        raise ValidationError("Resolved path escapes storage root.")
    return path
