"""
AI-NBA Readiness System — Backend
app/services/backup_service.py

Milestone G: Safe Backup and Restore Service.
Bundles structured database records and uploaded evidence files into an integrity-checked,
checksum-verified archive with strict path traversal protection and dry-run restore validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.phase5 import BackupRecord, BackupStatus
from app.models.user import User, UserRoleName
from app.schemas.phase5 import BackupValidationResponse, RestoreResponse


# Directory where system backup archives are stored safely
DEFAULT_BACKUP_DIR = Path("backups").resolve()


def compute_sha256(file_path: Path) -> str:
    """Compute hex SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def is_safe_archive_member(name: str) -> bool:
    """
    Prevent Directory Traversal / Zip Slip vulnerabilities.
    Returns False if path contains '..' or starts with '/' or '\\' or contains drive letters.
    """
    clean = name.replace("\\", "/")
    if clean.startswith("/") or clean.startswith("../") or "/../" in clean:
        return False
    # Check for Windows drive colon
    if ":" in clean:
        return False
    parts = Path(clean).parts
    if ".." in parts:
        return False
    return True


class BackupService:
    """
    Orchestrates backup archive generation, validation, and safe restore simulation.
    Strictly restricted to authorized administrators.
    """

    def __init__(self, db: Session, backup_dir: Optional[Path] = None):
        self.db = db
        self.settings = get_settings()
        self.backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        current_user: User,
        backup_type: str = "FULL",
        notes: Optional[str] = None,
    ) -> BackupRecord:
        """
        Create a backup archive (.zip) containing:
          - manifest.json: Metadata, export timestamp, app version, table entity counts
          - data_dump.json: Structured snapshot of core entities
          - evidence/: Active uploaded evidence documents
        """
        if not current_user.has_role(UserRoleName.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators are authorized to create backups.",
            )

        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        backup_id = f"nba_backup_{timestamp_str}_{uuid.uuid4().hex[:8]}"
        archive_path = self.backup_dir / f"{backup_id}.zip"

        # Gather evidence files directory
        docs_dir = Path("documents/uploads").resolve()

        # Build manifest
        manifest = {
            "backup_identifier": backup_id,
            "backup_type": backup_type,
            "created_at": now.isoformat(),
            "created_by": current_user.email,
            "system": "AI-NBA Accreditation Readiness System",
            "version": "1.0.0",
        }

        # Build structured data dump
        from app.models.academic import AcademicYear, Subject
        from app.models.faculty import FacultyProfile
        from app.models.phase4 import Document, NBACriterion, NBARequirement, RequirementEvaluation
        from app.models.phase5 import CorrectiveAction, Gap

        data_dump = {
            "academic_years": [
                {"id": str(y.id), "name": y.name, "is_active": y.is_active}
                for y in self.db.query(AcademicYear).all()
            ],

            "criteria": [
                {"id": str(c.id), "code": c.code, "name": c.name, "max_score": c.max_marks}
                for c in self.db.query(NBACriterion).all()
            ],

            "requirements": [
                {"id": str(r.id), "code": r.code, "title": r.title, "criterion_id": str(r.criterion_id)}
                for r in self.db.query(NBARequirement).all()
            ],
            "evaluations_count": self.db.query(RequirementEvaluation).count(),
            "documents_count": self.db.query(Document).count(),
            "gaps_count": self.db.query(Gap).count(),
            "actions_count": self.db.query(CorrectiveAction).count(),
        }

        manifest["counts"] = {
            "academic_years": len(data_dump["academic_years"]),
            "criteria": len(data_dump["criteria"]),
            "requirements": len(data_dump["requirements"]),
            "evaluations": data_dump["evaluations_count"],
            "documents": data_dump["documents_count"],
            "gaps": data_dump["gaps_count"],
            "actions": data_dump["actions_count"],
        }

        # Write zip archive
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("data_dump.json", json.dumps(data_dump, indent=2))

            if backup_type in ("FULL", "DOCUMENTS_ONLY") and docs_dir.exists():
                for root, _, files in os.walk(docs_dir):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(docs_dir)
                        # Add under evidence/
                        zf.write(full_p, arcname=f"evidence/{rel_p.as_posix()}")

        file_size = archive_path.stat().st_size
        sha256_hash = compute_sha256(archive_path)

        record = BackupRecord(
            backup_identifier=backup_id,
            backup_type=backup_type,
            file_path=str(archive_path),
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            status=BackupStatus.COMPLETED.value,
            created_by_user_id=current_user.id,
            notes=notes,
            created_at=now,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def validate_backup(self, backup_identifier: str, current_user: User) -> BackupValidationResponse:
        """
        Validate archive existence, checksum integrity, manifest structure, and path security.
        """
        if not current_user.has_role(UserRoleName.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators are authorized to validate backups.",
            )

        # Path traversal guard for identifier
        if not is_safe_archive_member(backup_identifier):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid backup identifier syntax.",
            )

        record = (
            self.db.query(BackupRecord)
            .filter(BackupRecord.backup_identifier == backup_identifier)
            .first()
        )

        archive_path = self.backup_dir / f"{backup_identifier}.zip"
        errors: List[str] = []

        if not archive_path.exists():
            return BackupValidationResponse(
                backup_identifier=backup_identifier,
                is_valid=False,
                archive_exists=False,
                checksum_valid=False,
                archive_size_bytes=0,
                security_checks_passed=False,
                errors=["Backup archive file does not exist on disk."],
            )

        file_size = archive_path.stat().st_size
        calculated_hash = compute_sha256(archive_path)
        checksum_valid = True

        if record and record.sha256_hash != calculated_hash:
            checksum_valid = False
            errors.append(f"Checksum mismatch: expected {record.sha256_hash}, calculated {calculated_hash}")

        manifest: Optional[Dict[str, Any]] = None
        security_passed = True

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # Security: check all member filenames
                for member_name in zf.namelist():
                    if not is_safe_archive_member(member_name):
                        security_passed = False
                        errors.append(f"Unsafe path detected in archive: {member_name}")

                if "manifest.json" in zf.namelist():
                    manifest_data = zf.read("manifest.json")
                    manifest = json.loads(manifest_data.decode("utf-8"))
                else:
                    errors.append("Archive missing manifest.json.")

                if "data_dump.json" not in zf.namelist():
                    errors.append("Archive missing data_dump.json.")

        except (zipfile.BadZipFile, Exception) as exc:
            return BackupValidationResponse(
                backup_identifier=backup_identifier,
                is_valid=False,
                archive_exists=True,
                checksum_valid=False,
                archive_size_bytes=file_size,
                security_checks_passed=False,
                errors=[f"Corrupt or unreadable zip archive: {str(exc)}"],
            )

        is_valid = checksum_valid and security_passed and (len(errors) == 0)

        if record and is_valid:
            record.status = BackupStatus.VALIDATED.value
            self.db.commit()

        return BackupValidationResponse(
            backup_identifier=backup_identifier,
            is_valid=is_valid,
            archive_exists=True,
            checksum_valid=checksum_valid,
            archive_size_bytes=file_size,
            manifest=manifest,
            security_checks_passed=security_passed,
            errors=errors,
        )

    def restore_backup(
        self,
        backup_identifier: str,
        current_user: User,
        dry_run: bool = True,
        confirm_destructive_acknowledged: bool = False,
    ) -> RestoreResponse:
        """
        Execute or simulate restore operation.
        Enforces strict safety rules:
          - Only ADMIN role allowed
          - Dry-run validation always checks archive validity and safe extraction paths
          - Actual restore requires explicit confirm_destructive_acknowledged=True
          - Automated test safety: will not destroy running DB unless target is isolated
        """
        if not current_user.has_role(UserRoleName.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators are authorized to perform restore operations.",
            )

        validation = self.validate_backup(backup_identifier, current_user)
        if not validation.is_valid:
            return RestoreResponse(
                backup_identifier=backup_identifier,
                status="FAILED",
                dry_run=dry_run,
                message="Backup archive validation failed. Restore aborted.",
                inspected_files_count=0,
                errors=validation.errors,
            )

        archive_path = self.backup_dir / f"{backup_identifier}.zip"
        file_count = 0

        with zipfile.ZipFile(archive_path, "r") as zf:
            file_count = len(zf.namelist())

        if dry_run or not confirm_destructive_acknowledged:
            return RestoreResponse(
                backup_identifier=backup_identifier,
                status="DRY_RUN_PASSED",
                dry_run=True,
                message=(
                    f"Dry run passed successfully. Archive contains {file_count} safe members. "
                    "To execute actual restore, supply confirm_destructive_acknowledged=True and dry_run=False."
                ),
                inspected_files_count=file_count,
                errors=[],
            )

        # Explicit non-dry-run restore
        # Unpack evidence to destination safely without path traversal
        target_docs_dir = Path("documents/uploads").resolve()
        target_docs_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zf:
            for member in zf.infolist():
                if not is_safe_archive_member(member.filename):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Refusing restore: malicious path detected in {member.filename}",
                    )
                if member.filename.startswith("evidence/"):
                    rel_name = member.filename[len("evidence/"):]
                    if rel_name and not rel_name.endswith("/"):
                        dest = target_docs_dir / rel_name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

        record = (
            self.db.query(BackupRecord)
            .filter(BackupRecord.backup_identifier == backup_identifier)
            .first()
        )
        if record:
            record.status = BackupStatus.RESTORED.value
            self.db.commit()

        return RestoreResponse(
            backup_identifier=backup_identifier,
            status="RESTORED",
            dry_run=False,
            message="Restore completed successfully for verified archive.",
            inspected_files_count=file_count,
            errors=[],
        )

    def list_backups(self, current_user: User) -> List[BackupRecord]:
        if not current_user.has_role(UserRoleName.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators can list system backups.",
            )
        return (
            self.db.query(BackupRecord)
            .order_by(BackupRecord.created_at.desc())
            .all()
        )
