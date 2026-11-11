"""
AI-NBA Readiness System — Backend
app/api/v1/backups.py

Endpoints for System Backup creation, archive validation, and safe restore simulation.
Strictly restricted to System Administrators (ADMIN role).
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRoleName
from app.schemas.phase5 import (
    BackupCreateRequest,
    BackupRecordOut,
    BackupValidationResponse,
    RestoreRequest,
    RestoreResponse,
)
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backups", tags=["Backup & Restore"])


@router.post(
    "",
    response_model=BackupRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create System Backup Archive",
)
def create_backup(
    body: BackupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
):
    """
    Creates a full backup archive (.zip) bundling database state and uploaded evidence files.
    Generates SHA-256 checksum and audit record. Restricted to ADMIN.
    """
    service = BackupService(db)
    record = service.create_backup(
        current_user=current_user,
        backup_type=body.backup_type,
        notes=body.notes,
    )
    return BackupRecordOut.model_validate(record)


@router.get(
    "",
    response_model=List[BackupRecordOut],
    summary="List System Backup Archives",
)
def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
):
    """
    List all created system backup records. Restricted to ADMIN.
    """
    service = BackupService(db)
    records = service.list_backups(current_user=current_user)
    return [BackupRecordOut.model_validate(r) for r in records]


@router.post(
    "/{backup_identifier}/validate",
    response_model=BackupValidationResponse,
    summary="Validate Backup Archive Integrity",
)
def validate_backup(
    backup_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
):
    """
    Validates backup file presence, SHA-256 checksum, manifest structure, and
    executes directory traversal security checks against archive members. Restricted to ADMIN.
    """
    service = BackupService(db)
    return service.validate_backup(
        backup_identifier=backup_identifier,
        current_user=current_user,
    )


@router.post(
    "/{backup_identifier}/restore",
    response_model=RestoreResponse,
    summary="Restore System Backup (Dry-run or Explicit)",
)
def restore_backup(
    backup_identifier: str,
    body: RestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRoleName.ADMIN.value)),
):
    """
    Perform a dry-run validation or explicit restoration from an authenticated archive.
    Requires explicit confirm_destructive_acknowledged=True and dry_run=False to unpack.
    Restricted to ADMIN.
    """
    service = BackupService(db)
    return service.restore_backup(
        backup_identifier=backup_identifier,
        current_user=current_user,
        dry_run=body.dry_run,
        confirm_destructive_acknowledged=body.confirm_destructive_acknowledged,
    )
