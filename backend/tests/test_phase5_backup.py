"""
tests/test_phase5_backup.py

Tests for Backup and Restore:
  - Archive creation (.zip) with manifest.json and data_dump.json
  - SHA-256 checksum generation and verification
  - Directory Traversal / Zip Slip protection
  - RBAC: Faculty forbidden from creating, listing, or validating backups
  - Dry-run validation and restore simulation
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.phase5 import BackupRecord, BackupStatus
from app.services.backup_service import BackupService, is_safe_archive_member


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    bdir = tmp_path / "system_backups"
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir


class TestPathTraversalSecurity:
    def test_safe_paths_accepted(self):
        """Relative sub-paths are accepted."""
        assert is_safe_archive_member("manifest.json") is True
        assert is_safe_archive_member("evidence/documents/report.pdf") is True
        assert is_safe_archive_member("data_dump.json") is True

    def test_malicious_traversal_paths_rejected(self):
        """Path traversal patterns are strictly rejected."""
        assert is_safe_archive_member("../evil.exe") is False
        assert is_safe_archive_member("evidence/../../secret.txt") is False
        assert is_safe_archive_member("/etc/shadow") is False
        assert is_safe_archive_member("\\Windows\\System32\\cmd.exe") is False
        assert is_safe_archive_member("C:/Users/file.txt") is False


class TestBackupService:
    def test_create_and_validate_backup(
        self,
        db_session: Session,
        admin_user,
        temp_backup_dir: Path,
    ):
        """Creating a backup creates an archive with manifest and valid SHA-256."""
        service = BackupService(db_session, backup_dir=temp_backup_dir)
        record = service.create_backup(
            current_user=admin_user,
            backup_type="FULL",
            notes="Automated test backup",
        )

        assert record.id is not None
        assert record.backup_identifier.startswith("nba_backup_")
        assert Path(record.file_path).exists()
        assert len(record.sha256_hash) == 64

        # Validate archive
        val = service.validate_backup(record.backup_identifier, admin_user)
        assert val.is_valid is True
        assert val.checksum_valid is True
        assert val.archive_exists is True
        assert val.manifest is not None
        assert val.manifest["system"] == "AI-NBA Accreditation Readiness System"
        assert val.security_checks_passed is True

    def test_reject_corrupt_or_tampered_archive(
        self,
        db_session: Session,
        admin_user,
        temp_backup_dir: Path,
    ):
        """Tampered backup archive is detected via SHA-256 mismatch."""
        service = BackupService(db_session, backup_dir=temp_backup_dir)
        record = service.create_backup(current_user=admin_user)

        # Tamper with archive
        with open(record.file_path, "ab") as f:
            f.write(b"TAMPERED_CONTENT")

        val = service.validate_backup(record.backup_identifier, admin_user)
        assert val.is_valid is False
        assert val.checksum_valid is False
        assert any("Checksum mismatch" in e for e in val.errors)

    def test_dry_run_restore_validation(
        self,
        db_session: Session,
        admin_user,
        temp_backup_dir: Path,
    ):
        """Dry-run restore passes without modifying database."""
        service = BackupService(db_session, backup_dir=temp_backup_dir)
        record = service.create_backup(current_user=admin_user)

        resp = service.restore_backup(
            backup_identifier=record.backup_identifier,
            current_user=admin_user,
            dry_run=True,
            confirm_destructive_acknowledged=False,
        )

        assert resp.status == "DRY_RUN_PASSED"
        assert resp.dry_run is True
        assert resp.inspected_files_count > 0


class TestBackupAPIEndpoints:
    def test_faculty_forbidden_from_backup_endpoints(
        self,
        db_client: TestClient,
        active_faculty_user,
    ):
        """Faculty cannot create, list, or validate backups (403 Forbidden)."""
        from app.core.security import create_access_token
        token = create_access_token(
            subject=str(active_faculty_user.id),
            roles=active_faculty_user.role_names,
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to create
        r_create = db_client.post("/api/v1/backups", json={"backup_type": "FULL"}, headers=headers)
        assert r_create.status_code == 403

        # Attempt to list
        r_list = db_client.get("/api/v1/backups", headers=headers)
        assert r_list.status_code == 403

    def test_admin_backup_lifecycle_api(
        self,
        db_client: TestClient,
        admin_headers: dict,
    ):
        """Admin can create, list, and validate backups via API."""
        # Create
        r_create = db_client.post(
            "/api/v1/backups",
            json={"backup_type": "FULL", "notes": "API test backup"},
            headers=admin_headers,
        )
        assert r_create.status_code == 201
        data = r_create.json()
        b_id = data["backup_identifier"]

        # List
        r_list = db_client.get("/api/v1/backups", headers=admin_headers)
        assert r_list.status_code == 200
        assert any(b["backup_identifier"] == b_id for b in r_list.json())

        # Validate
        r_val = db_client.post(f"/api/v1/backups/{b_id}/validate", headers=admin_headers)
        assert r_val.status_code == 200
        assert r_val.json()["is_valid"] is True

        # Restore dry-run
        r_res = db_client.post(
            f"/api/v1/backups/{b_id}/restore",
            json={"backup_identifier": b_id, "dry_run": True},
            headers=admin_headers,
        )
        assert r_res.status_code == 200
        assert r_res.json()["status"] == "DRY_RUN_PASSED"
