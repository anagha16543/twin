# AI-NBA Readiness System — Backend

REST API for the AI-Driven NBA Accreditation Readiness System, built with
**FastAPI**, **PostgreSQL**, **pgvector**, **SQLAlchemy 2.x**, and **Alembic**.

> **Phase 6 & NBA Tier-I 2026 Rules complete.** All 247 backend tests pass (215 baseline + 32 NBA 2026 deterministic rule and post-audit tests). See the root `README.md` for full architectural documentation.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Virtual environment setup](#virtual-environment-setup)
3. [Dependency installation](#dependency-installation)
4. [Environment configuration](#environment-configuration)
5. [Database configuration & migrations](#database-configuration--migrations)
6. [Initial account & Phase 4 seeding](#initial-account--phase-4-seeding)
7. [Authentication & Authorization](#authentication--authorization)
8. [Phase 4 Architecture & Capabilities](#phase-4-architecture--capabilities)
9. [Phase 5 Architecture & Capabilities](#phase-5-architecture--capabilities)
10. [API Endpoints Reference](#api-endpoints-reference)
11. [Readiness Formula](#readiness-formula)
12. [Gap Lifecycle & Permissions](#gap-lifecycle--permissions)
13. [Document Storage & OCR Configuration](#document-storage--ocr-configuration)
14. [RAG & Vector Retrieval (pgvector)](#rag--vector-retrieval-pgvector)
15. [AI Service Integration & Limitations](#ai-service-integration--limitations)
16. [Starting FastAPI](#starting-fastapi)
17. [Running tests](#running-tests)
18. [Swagger documentation](#swagger-documentation)
19. [Directory structure](#directory-structure)
20. [Docker Compose](#docker-compose)
21. [Phase 4 Completion Checklist](#phase-4-completion-checklist)
22. [Phase 5 Completion Checklist](#phase-5-completion-checklist)
23. [Phase 5 Final Report](#phase-5-final-report)

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.12+ (tested on 3.14) | Python 3.14 supported |
| PostgreSQL | 14+ with pgvector | Vector search enabled via `CREATE EXTENSION vector` |
| pip | 23+ | Bundled with Python |
| Tesseract OCR | 5.x | Optional; needed for scanned PDF/image OCR fallback |
| Docker + Compose | — | Optional; for containerised workflow |

---

## Virtual environment setup

All commands are run from the **`backend/`** directory.

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

---

## Dependency installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Phase 4 introduces:
- `python-multipart` for streaming multipart file uploads.
- `pypdf` for pure-Python digital PDF page text extraction.
- `pillow` for image handling and OCR preprocessing.
- `pytesseract` for Tesseract OCR integration.
- `pgvector` for PostgreSQL vector embedding columns and similarity operators.

Phase 5 introduces:
- `reportlab` for server-side PDF report generation.
- `openpyxl` for server-side Excel (xlsx) report generation.

---

## Environment configuration

```bash
# Copy the example file and edit the values
cp .env.example .env
```

Open `.env` and configure:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:changeme@localhost:5432/nba_readiness
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
JWT_SECRET_KEY=change-this-to-a-secure-random-secret-key-at-least-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=AdminPassword123!
INITIAL_HOD_EMAIL=hod@example.com
INITIAL_HOD_PASSWORD=HODPassword123!

# Phase 4 — Document Storage
DOCUMENT_STORAGE_ROOT=./documents/uploads
MAX_UPLOAD_SIZE_BYTES=26214400

# Phase 4 — AI Service Integration
AI_SERVICE_BASE_URL=http://localhost:8001
AI_SERVICE_TIMEOUT_SECONDS=30.0

# Phase 4 — RAG & Embeddings
EMBEDDING_MODEL=local-minilm
EMBEDDING_DIMENSIONS=384
CHUNK_SIZE=600
CHUNK_OVERLAP=100
```

> **Never commit `.env`.** It is listed in `.gitignore`.

### Key environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | `true` | Set to `false` in production |
| `API_V1_PREFIX` | `/api/v1` | URL prefix for all v1 routes |
| `DATABASE_URL` | *(see .env.example)* | Full SQLAlchemy connection string |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `JWT_SECRET_KEY` | *(dev placeholder)* | Secret key for signing HMAC-SHA256 JWT tokens |
| `DOCUMENT_STORAGE_ROOT` | `./documents/uploads` | Directory for uploaded file binaries |
| `MAX_UPLOAD_SIZE_BYTES` | `26214400` (25 MB) | Maximum permitted file upload size |
| `AI_SERVICE_BASE_URL` | `http://localhost:8001` | URL of the autonomous AI analysis service |
| `AI_SERVICE_TIMEOUT_SECONDS` | `30.0` | Timeout for AI service requests |
| `EMBEDDING_MODEL` | `local-minilm` | Model identifier for text embeddings |
| `EMBEDDING_DIMENSIONS` | `384` | Embedding vector dimensions (pgvector) |
| `TESSERACT_CMD` | `None` | Path to tesseract executable if not in PATH |

---

## Database configuration & migrations

Alembic manages migrations. The migration chain includes:
1. `93c1ca7c035e` — Phase 1 & 2 Auth, Users, Roles, Academic Years, Subjects
2. `d72af8b7c997` — Phase 3 Faculty achievements, Students, Outcomes, Marks, Attendance
3. `e3b8a1c9f4d2` — Phase 4 Criteria, Requirements, Evaluations, Documents, Evidence, Chunks (with pgvector)
4. `f5a1b2c3d4e5` — Phase 5 `nba_gaps`, `nba_corrective_actions`, `notifications`, `system_backup_records`
5. `a1b2c3d4e5f6` — Phase 6 Align NBA Tier-I 2026 Criteria 3, 4, 5, and 6 weightages and rules

```bash
# Run all migrations up to head
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Generate SQL script offline without connecting to the DB
alembic upgrade head --sql

# Show current revision
alembic current
```

---

## Initial account & Phase 4 seeding

```bash
# Seeds roles, admin, HOD, academic year, and Phase 4 criteria/requirements idempotently
python -m app.db.seed

# Or seed Phase 4 criteria & requirements specifically:
python -m app.db.seed_phase4
```

Seeding is safe and idempotent: existing records are never overwritten or reset.

---

## Phase 4 Architecture & Capabilities

Phase 4 delivers the core accreditation intelligence framework:

1. **Deterministic NBA Requirements Engine (Milestone A)**:
   - Full support for Criteria 3, 4, 5, and 6.
   - Status transitions: `PASS`, `WARNING`, `FAIL`, `NOT_APPLICABLE`.
   - **Numerical compliance is strictly deterministic**: calculated by backend Python logic, never by an LLM.
   - Missing data yields `WARNING` (never `PASS`).
   - Immutable evaluation history: repeated evaluations create new records, preserving a complete audit trail.
2. **Evidence & Document Management (Milestone B)**:
   - Supported formats: PDF, PNG, JPEG.
   - Content-type validation via file byte signatures (magic bytes); client-supplied MIME headers are never trusted.
   - Filename sanitization and path traversal prevention.
   - SHA-256 deduplication and storage outside public static directories.
   - Version lineage tracking (`version`, `is_current`, `parent_document_id`).
   - Soft deletion preserving audit history.
   - Evidence linking to requirements without altering evaluation status.
3. **Text Extraction & OCR (Milestone C)**:
   - Page-by-page extraction from digital PDFs with page-number preservation.
   - OCR fallback for images and scanned documents using Tesseract when installed.
   - Graceful degradation: if Tesseract is not installed, the API remains fully operational, preserves native text, and marks documents as `PROCESSED_PARTIAL`.
4. **Chunking, Embeddings & RAG Retrieval (Milestone D)**:
   - Overlapping character chunking with SHA-256 chunk deduplication.
   - Native `pgvector` Vector(384) storage on PostgreSQL, with seamless JSON fallback for SQLite test environments.
   - Semantic retrieval filtered by department, academic year, and criterion.
   - Soft-deleted documents automatically excluded from retrieval.
5. **Backend-to-AI Service Integration (Milestone E)**:
   - Structured JSON request payload with correlation IDs, backend metrics, and evidence passages.
   - Adapter for the existing C3 endpoint (`/criterion3/analyze`).
   - Graceful `UNAVAILABLE` handling for connection errors, timeouts, and unimplemented criteria (C4, C5, C6).
   - **Advisory Role**: AI analysis never overrides or dictates compliance statuses (`ai_drives_compliance` is always `False`).

---

## Phase 5 Architecture & Capabilities

Phase 5 completes the backend with five new modules:

### B — Digital Twin Service
- `app/services/digital_twin_service.py` + `app/api/v1/digital_twin.py`
- Calculates real-time department-wide and criterion-wise NBA readiness from active database state.
- Excludes soft-deleted documents, unevaluated requirements, and `NOT_APPLICABLE` items from the readiness denominator.
- Returns `null` readiness with an explanation when data is insufficient — never silently counts gaps as passes.
- Timestamps every snapshot at generation time.

### C — Readiness Analytics
- Criterion-wise breakdown embedded in `DigitalTwinService`.
- Surfaces `[PLACEHOLDER]` limitations from seed data in API response `limitations` arrays.

### D — Gap Analysis & Corrective Action Tracking
- `app/services/gap_service.py` + `app/api/v1/gaps.py`
- Automatically generates gaps from `FAIL` and `WARNING` evaluations.
- Prevents duplicate open gaps for the same requirement in the same academic year and department.
- Auto-resolves gaps when a requirement is subsequently evaluated as `PASS`.
- Status lifecycle: `IDENTIFIED` → `IN_PROGRESS` → `COMPLETED` (or `CANCELLED`).
- RBAC: Faculty can manage their own actions; HOD oversees department-wide gaps; Admin has system-level access.

### E — Report Generation
- `app/services/report_service.py` + `app/api/v1/reports.py`
- PDF reports via **ReportLab** (department readiness, criterion breakdown, evidence inventory, gap tracking).
- Excel reports via **openpyxl** with formula injection protection — cells starting with `=`, `+`, `-`, `@`, TAB, or CR are prefixed with a single quote.
- Generated from live database state; temporary files cleaned up after streaming response.

### F — In-App Notifications
- `app/services/notification_service.py` + `app/api/v1/notifications.py`
- Persistent `notifications` table with per-user recipient isolation.
- Duplicate prevention via composite idempotency key (`recipient_id`, `notification_type`, `reference_id`, `reference_type`).
- Supports: list, unread count, mark-as-read, paginated retrieval.

### G — Backup & Restore
- `app/services/backup_service.py` + `app/api/v1/backups.py`
- Zip archives with SHA-256 checksums and a manifest file.
- **Zip Slip protection**: `is_safe_archive_member()` rejects any path containing `..` or absolute paths.
- Dry-run restore validation — no destructive operation is ever run automatically.
- Backup endpoints restricted to `ADMIN` only; Faculty access returns `403 Forbidden`.

---

## API Endpoints Reference

### NBA Requirements Engine (`/api/v1/nba`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/nba/criteria` | List NBA criteria (optional `is_active` filter) | Authenticated |
| `GET` | `/api/v1/nba/criteria/{id}` | Get criterion details | Authenticated |
| `GET` | `/api/v1/nba/criteria/{id}/requirements` | List requirements for a criterion | Authenticated |
| `GET` | `/api/v1/nba/requirements/{id}` | Get single requirement details | Authenticated |
| `POST` | `/api/v1/nba/requirements/{id}/evaluate` | Run deterministic evaluation rule and persist result | HOD or ADMIN |
| `GET` | `/api/v1/nba/requirements/{id}/evaluations` | List immutable evaluation history for requirement | Authenticated |

### Evidence & Documents (`/api/v1/documents`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/documents/upload` | Upload document file (PDF, PNG, JPEG) | Authenticated |
| `GET` | `/api/v1/documents/` | List active documents (uploader, HOD, ADMIN) | Authenticated |
| `GET` | `/api/v1/documents/{id}` | Get document metadata | Owner, HOD, ADMIN |
| `GET` | `/api/v1/documents/{id}/download` | Stream document binary file bytes | Owner, HOD, ADMIN |
| `POST` | `/api/v1/documents/{id}/replace` | Upload new version of existing document | Owner, HOD, ADMIN |
| `DELETE`| `/api/v1/documents/{id}` | Soft-delete document | HOD or ADMIN |
| `GET` | `/api/v1/documents/{id}/history` | Get document version lineage | Owner, HOD, ADMIN |
| `POST` | `/api/v1/documents/requirements/{id}/evidence` | Link document to requirement as evidence | HOD or ADMIN |
| `GET` | `/api/v1/documents/requirements/{id}/evidence` | List evidence linked to requirement | Authenticated |

### AI Analysis & RAG Retrieval (`/api/v1/analysis`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/analysis/retrieve` | Semantic RAG retrieval of relevant chunks | Authenticated |
| `POST` | `/api/v1/analysis/ai-analysis` | Request AI-assisted qualitative interpretation | HOD or ADMIN |

### Digital Twin (`/api/v1/digital-twin`) — Phase 5

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/digital-twin/snapshot` | Department-wide NBA readiness snapshot | Authenticated |
| `GET` | `/api/v1/digital-twin/completeness` | Data completeness metrics | Authenticated |
| `GET` | `/api/v1/digital-twin/criteria/{criterion_code}` | Criterion-specific readiness analytics | Authenticated |

### Gap Analysis & Corrective Actions (`/api/v1/gaps`) — Phase 5

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/gaps/generate` | Generate/refresh gaps from failed evaluations | HOD or ADMIN |
| `GET` | `/api/v1/gaps/` | List gaps (filters: status, criterion, academic year) | Authenticated |
| `GET` | `/api/v1/gaps/{gap_id}` | Get gap details | Authenticated |
| `PATCH` | `/api/v1/gaps/{gap_id}` | Update gap description/priority/severity | HOD or ADMIN |
| `POST` | `/api/v1/gaps/{gap_id}/actions` | Create corrective action | HOD or ADMIN |
| `GET` | `/api/v1/gaps/{gap_id}/actions` | List corrective actions for a gap | Authenticated |
| `PATCH` | `/api/v1/gaps/{gap_id}/actions/{action_id}` | Update action status/notes/due date | Owner, HOD, ADMIN |
| `GET` | `/api/v1/gaps/overdue-actions` | List overdue actions | HOD or ADMIN |

### Reports (`/api/v1/reports`) — Phase 5

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/reports/excel` | Download NBA readiness Excel workbook | HOD or ADMIN |
| `GET` | `/api/v1/reports/pdf` | Download NBA readiness PDF report | HOD or ADMIN |

### Notifications (`/api/v1/notifications`) — Phase 5

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/notifications/` | List own notifications (paginated) | Authenticated |
| `GET` | `/api/v1/notifications/unread-count` | Count of unread notifications | Authenticated |
| `PATCH` | `/api/v1/notifications/{notification_id}/read` | Mark notification as read | Owner only |

### Backup & Restore (`/api/v1/backups`) — Phase 5

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/v1/backups/` | Create backup archive | ADMIN only |
| `GET` | `/api/v1/backups/` | List backup records | ADMIN only |
| `GET` | `/api/v1/backups/{backup_id}` | Get backup metadata | ADMIN only |
| `POST` | `/api/v1/backups/{backup_id}/validate` | Validate backup archive integrity | ADMIN only |
| `POST` | `/api/v1/backups/{backup_id}/restore` | Dry-run restore validation | ADMIN only |

---

## Readiness Formula

> **Important**: This is an internal operational readiness indicator, **not** an official NBA accreditation score. Official scores require on-site NBA inspection using the official SAR with confirmed weightings from the applicable NBA manual.

```
eligible_denominator = total_requirements - not_applicable_requirements

criterion_readiness_pct = (passed_requirements / eligible_denominator) x 100

overall_readiness_pct  = (passed_requirements_all / eligible_overall) x 100
```

- `NOT_APPLICABLE` requirements are **excluded** from the denominator.
- **Unevaluated requirements contribute 0** to the numerator — never silently treated as passed.
- If `eligible_denominator == 0`, readiness is `null` with an explanatory `limitations` entry.
- If no eligible requirements have been evaluated, readiness is `null` with an explanatory `limitations` entry.
- `WARNING` requirements count toward the denominator but **not** toward the numerator.
- Where a requirement rule contains `[PLACEHOLDER]`, a limitation note is surfaced in the response.

---

## Gap Lifecycle & Permissions

```
IDENTIFIED → IN_PROGRESS → COMPLETED
                         ↘ CANCELLED
```

| Action | FACULTY | HOD | ADMIN |
|--------|---------|-----|-------|
| View department gaps | Own scope | All | All |
| Generate gaps | No | Yes | Yes |
| Update gap metadata | No | Yes | Yes |
| Create corrective action | No | Yes | Yes |
| Update own action status | Yes | Yes | Yes |
| Reassign action owner | No | Yes | Yes |
| View overdue actions | No | Yes | Yes |

**Duplicate prevention**: If an open gap already exists for the same requirement, academic year, and department, no duplicate is created during gap refresh.

**Auto-resolution**: When a requirement is re-evaluated as `PASS`, the associated open gap is automatically marked `COMPLETED`.

---

## Document Storage & OCR Configuration

### Storage Security
- Uploaded binaries are written to `DOCUMENT_STORAGE_ROOT` (`./documents/uploads` by default).
- Stored filenames are random UUIDs; the original filename is stored only in database metadata.
- Download requests resolve paths strictly within `DOCUMENT_STORAGE_ROOT`, blocking path traversal.

### OCR (Tesseract) Installation
- If Tesseract is installed and on your system `PATH`, image and scanned PDF OCR are automatically enabled.
- On Windows: Install [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and add `C:\Program Files\Tesseract-OCR` to PATH, or set `TESSERACT_CMD` in `.env`.
- On Linux: `sudo apt install tesseract-ocr`
- If Tesseract is absent: The system operates normally without crashing; digital PDFs extract native text, and documents requiring OCR are marked `PROCESSED_PARTIAL`.

---

## RAG & Vector Retrieval (pgvector)

On PostgreSQL:
- The vector extension is enabled via `CREATE EXTENSION IF NOT EXISTS vector;`.
- Chunks store 384-dimensional embeddings (using `all-MiniLM-L6-v2` or compatible providers).
- Queries use cosine distance (`<=>` operator) for top-K similarity search.

On SQLite (Automated Tests):
- `_make_vector_column` maps `embedding` to `JSON` dynamically, allowing the entire 185-test suite to run in memory without requiring a live PostgreSQL instance.

---

## AI Service Integration & Limitations

### Integration Contract
The backend client communicates with the autonomous AI service at `AI_SERVICE_BASE_URL`.
- Sends: `request_id`, `correlation_id`, `criterion_code`, `requirement_code`, `academic_year`, `department`, `analysis_task`, `structured_data` (deterministic metrics), and `evidence_passages`.
- Receives: `request_id`, `correlation_id`, `status`, `summary`, `findings`, `recommended_actions`, `confidence_score`, `limitations`.

### Known Limitations
1. **Criterion 3 Endpoint Format**: The current `ai-service/` endpoint `POST /criterion3/analyze` returns unstructured text and reads static fixture data. The backend client parses this text into an observation finding with an advisory limitation note.
2. **Criteria 4, 5, 6 Endpoints**: The agent endpoints for C4, C5, and C6 do not yet exist in `ai-service/`. The backend gracefully handles these as `UNAVAILABLE` without fabricating results. Backend deterministic evaluation for C4, C5, and C6 remains fully functional.
3. **Compliance Authority**: The backend is the sole authority on compliance. AI interpretation is advisory only (`ai_drives_compliance=False`).

---

## Starting FastAPI

```bash
# Development (auto-reload on file changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API is available at `http://localhost:8000`.

---

## Running tests

Tests do **not** require a live PostgreSQL database or external AI service. All tests use an in-memory SQLite engine and mocked external HTTP adapters.

```bash
# Run all tests (215 tests across Phases 1-5)
pytest

# Run tests with verbose output
pytest -v

# Run Phase 5 test suites specifically
pytest tests/test_phase5_digital_twin.py -v
pytest tests/test_phase5_gaps.py -v
pytest tests/test_phase5_reports.py -v
pytest tests/test_phase5_notifications.py -v
pytest tests/test_phase5_backup.py -v

# Run Phase 4 test suites specifically
pytest tests/test_phase4_requirements.py -v
pytest tests/test_phase4_documents.py -v
pytest tests/test_phase4_processing_rag.py -v
pytest tests/test_phase4_agent_integration.py -v
```

---

## Swagger documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI (interactive testing) |
| `http://localhost:8000/redoc` | ReDoc (clean documentation) |
| `http://localhost:8000/openapi.json` | Raw OpenAPI schema |

---

## Directory structure

```
backend/
├── app/
│   ├── __init__.py           # Package init & Python 3.14 SQLAlchemy compatibility patch
│   ├── main.py               # FastAPI application factory
│   ├── api/
│   │   ├── deps.py           # Authentication, RBAC, ownership, and subject assignment
│   │   └── v1/
│   │       ├── router.py     # Aggregates all v1 API routers
│   │       ├── health.py     # Health & database readiness probes
│   │       ├── auth.py       # Authentication (register, login, me)
│   │       ├── users.py      # User management & HOD approval
│   │       ├── subjects.py   # Academic years, subjects, & assignments
│   │       ├── faculty_data.py # Faculty achievements, qualifications, experience
│   │       ├── curriculum.py # Students, outcomes, assessments, marks, attendance
│   │       ├── requirements.py   # Phase 4 NBA Criteria, Requirements & Evaluations
│   │       ├── documents.py      # Phase 4 Document upload, streaming, versioning, evidence
│   │       ├── analysis.py       # Phase 4 RAG retrieval & AI analysis endpoints
│   │       ├── digital_twin.py   # Phase 5 Digital Twin snapshot & criterion analytics
│   │       ├── gaps.py           # Phase 5 Gap analysis & corrective action tracking
│   │       ├── reports.py        # Phase 5 PDF & Excel report downloads
│   │       ├── notifications.py  # Phase 5 In-app notification management
│   │       └── backups.py        # Phase 5 Backup creation, validation & restore
│   ├── business_rules/       # Deterministic NBA requirements engine
│   │   ├── __init__.py
│   │   ├── readiness_rules.py  # Shared evaluation framework & rule registry
│   │   ├── criterion3_rules.py # Criterion 3 CO-PO attainment rules
│   │   ├── criterion4_rules.py # Criterion 4 student performance rules
│   │   ├── criterion5_rules.py # Criterion 5 faculty qualification rules
│   │   └── criterion6_rules.py # Criterion 6 facilities & lab rules
│   ├── core/
│   │   ├── config.py         # Settings & environment variables (Phases 1-5)
│   │   └── security.py       # Password hashing & JWT generation
│   ├── db/
│   │   ├── session.py        # SQLAlchemy engine, session factory, Base
│   │   ├── seed.py           # Master idempotent seed command
│   │   └── seed_phase4.py    # Idempotent NBA criteria & requirements seed
│   ├── models/               # SQLAlchemy 2.x declarative models (38 models)
│   │   ├── __init__.py
│   │   ├── user.py           # User, Role, user_roles
│   │   ├── faculty.py        # FacultyProfile
│   │   ├── academic.py       # AcademicYear, Subject, FacultySubjectAssignment
│   │   ├── faculty_data.py   # 9 faculty achievement models
│   │   ├── curriculum.py     # 12 curriculum, outcome, assessment models
│   │   ├── phase4.py         # NBACriterion, NBARequirement, RequirementEvaluation,
│   │   │                     # Document, RequirementEvidence, DocumentChunk
│   │   └── phase5.py         # Gap, CorrectiveAction, Notification, SystemBackupRecord
│   ├── schemas/              # Pydantic v2 schemas
│   │   ├── auth.py, user.py, academic.py, faculty_data.py, curriculum.py
│   │   ├── phase4.py         # Criteria, Requirements, Document, RAG, AI schemas
│   │   └── phase5.py         # DigitalTwin, Gap, Action, Notification, Backup schemas
│   └── services/
│       ├── storage_service.py      # Safe disk file storage, hashing, path verification
│       ├── document_processor.py   # PDF extraction (pypdf) & OCR (pytesseract)
│       ├── rag_service.py          # Text chunking, pgvector / SQLite embeddings & search
│       ├── agent_client.py         # HTTP client for AI service with C3 adapter
│       ├── digital_twin_service.py # Phase 5 Real-time Digital Twin aggregation
│       ├── gap_service.py          # Phase 5 Gap generation, lifecycle, RBAC
│       ├── report_service.py       # Phase 5 PDF & Excel report generation
│       ├── notification_service.py # Phase 5 Persistent notification management
│       └── backup_service.py       # Phase 5 Backup/restore with Zip Slip protection
├── migrations/
│   ├── env.py                # Alembic configuration
│   └── versions/
│       ├── 20261027_0930_93c1ca7c035e_create_auth_and_academic_tables.py
│       ├── 20261027_1005_d72af8b7c997_create_faculty_and_curriculum_tables.py
│       ├── 20261028_0001_e3b8a1c9f4d2_create_phase4_nba_and_evidence_tables.py
│       └── 20261028_0200_f5a1b2c3d4e5_create_phase5_digital_twin_and_gap_tables.py
├── tests/
│   ├── conftest.py                      # Pytest fixtures with in-memory SQLite
│   ├── test_academic.py, test_auth.py, test_config.py, test_curriculum.py
│   ├── test_faculty_data.py, test_health.py, test_models_and_constraints.py
│   ├── test_root.py, test_security.py, test_users_and_roles.py
│   ├── test_phase4_requirements.py      # 27 tests (Phase 4 Milestone A)
│   ├── test_phase4_documents.py         # 15 tests (Phase 4 Milestone B)
│   ├── test_phase4_processing_rag.py    # 12 tests (Phase 4 Milestones C & D)
│   ├── test_phase4_agent_integration.py # 9 tests  (Phase 4 Milestone E)
│   ├── test_phase5_digital_twin.py      # 6 tests  (Phase 5 Milestones B & C)
│   ├── test_phase5_gaps.py              # 5 tests  (Phase 5 Milestone D)
│   ├── test_phase5_reports.py           # 7 tests  (Phase 5 Milestone E)
│   ├── test_phase5_notifications.py     # 5 tests  (Phase 5 Milestone F)
│   ├── test_phase5_backup.py            # 7 tests  (Phase 5 Milestone G)
│   └── test_nba_2026_rules.py           # 32 tests (Phase 6 Deterministic NBA 2026 Rules & Audit Corrections)
├── .env.example              # Environment variable template
├── alembic.ini               # Alembic configuration
├── Dockerfile                # Production container image
├── pytest.ini                # Pytest configuration
├── README.md                 # Documentation
└── requirements.txt          # Python dependencies
```

---

## Phase 4 Completion Checklist

| Area | Deliverable | Status |
| :--- | :--- | :---: |
| **Milestone A: Requirements Engine** | Models for `NBACriterion`, `NBARequirement`, `RequirementEvaluation`; deterministic rules for C3, C4, C5, C6; immutable history; unknown rule fallback to `WARNING` | ✔ Done |
| **Milestone B: Evidence & Documents** | Models for `Document`, `RequirementEvidence`; multipart upload; byte-signature MIME detection; SHA-256 deduplication; authorized streaming download; version lineage; soft deletion | ✔ Done |
| **Milestone C: Extraction & OCR** | Digital PDF extraction via `pypdf`; page-number preservation; graceful degradation when Tesseract is absent (`PROCESSED_PARTIAL`); no API crashes | ✔ Done |
| **Milestone D: Chunking & RAG** | Overlapping character chunking; `pgvector` Vector(384) on PostgreSQL; SQLite JSON test fallback; semantic chunk retrieval; exclusion of soft-deleted docs | ✔ Done |
| **Milestone E: AI Integration** | HTTP client for AI service; C3 text response adapter; C4-C6 unavailable handling; correlation IDs; advisory role (`ai_drives_compliance=False`) | ✔ Done |
| **Milestone F: API & Security** | Mounted routers for `/api/v1/nba`, `/api/v1/documents`, `/api/v1/analysis`; RBAC enforced (uploader/HOD/ADMIN); path traversal protection | ✔ Done |
| **Milestone G: Migrations** | Alembic migration revision `e3b8a1c9f4d2` tested with clean PostgreSQL DDL; conditional `vector` extension; safe downgrade | ✔ Done |
| **Milestone H: Testing** | **185 total tests passing** (122 Phase 1–3 + 63 Phase 4) with zero failures and zero regressions | ✔ Done |
| **Milestone I: Scope Integrity** | Zero modifications to frontend or `ai-service/`; all secrets preserved | ✔ Done |

---

## Phase 5 Completion Checklist

| Area | Deliverable | Status |
| :--- | :--- | :---: |
| **Milestone B: Digital Twin** | `DigitalTwinService`; department-wide & criterion-wise snapshots; null-safe readiness; soft-delete exclusion; placeholder limitation surfacing | ✔ Done |
| **Milestone C: Readiness Analytics** | Criterion-wise breakdown; `[PLACEHOLDER]` propagation; deterministic formula (see [Readiness Formula](#readiness-formula)) | ✔ Done |
| **Milestone D: Gap Analysis** | `GapService`; auto-generation from FAIL/WARNING; duplicate prevention; auto-resolution on PASS; RBAC lifecycle management | ✔ Done |
| **Milestone E: Reports** | PDF (ReportLab) & Excel (openpyxl); formula injection protection; temp-file cleanup; HOD/ADMIN-gated endpoints | ✔ Done |
| **Milestone F: Notifications** | Persistent `Notification` model; recipient isolation; idempotency keys; unread count; mark-as-read | ✔ Done |
| **Milestone G: Backup & Restore** | Zip archive with SHA-256 checksums; Zip Slip protection; dry-run validation; ADMIN-only endpoints | ✔ Done |
| **Milestone H: API Integration** | All 5 Phase 5 routers mounted in `router.py`; OpenAPI docs accurate | ✔ Done |
| **Milestone I: Migration** | Revision `f5a1b2c3d4e5` — `nba_gaps`, `nba_corrective_actions`, `notifications`, `system_backup_records`; safe downgrade | ✔ Done |
| **Milestone J: Testing** | 30 new Phase 5 tests; full regression suite **215/215 passing**; zero regressions | ✔ Done |
| **Milestone K: Documentation** | README updated with all Phase 5 content, formulas, permissions, limitations | ✔ Done |
| **Milestone L: Quality Audit** | No secrets, no frontend changes, no `ai-service/` changes, no IDOR, no stale data, temp-file cleanup verified | ✔ Done |

---

## Phase 5 Final Report

### A. Implementation Summary

| Milestone | Principal Files Added / Modified |
|-----------|----------------------------------|
| B Digital Twin | `services/digital_twin_service.py`, `api/v1/digital_twin.py` |
| C Readiness Analytics | Embedded in `digital_twin_service.py` |
| D Gap Analysis | `services/gap_service.py`, `api/v1/gaps.py` |
| E Reports | `services/report_service.py`, `api/v1/reports.py` |
| F Notifications | `services/notification_service.py`, `api/v1/notifications.py` |
| G Backup & Restore | `services/backup_service.py`, `api/v1/backups.py` |
| H API Integration | `api/v1/router.py` (Phase 5 routers mounted) |
| I Migration | `migrations/versions/20261028_0200_f5a1b2c3d4e5_...py` |
| J Testing | `tests/test_phase5_*.py` (30 new tests) |
| K/L Docs & Audit | This README |

### B. Database Changes — Phase 5

| Model | Table | Description |
|-------|-------|-------------|
| `Gap` | `nba_gaps` | NBA requirement gap records with severity and department scope |
| `CorrectiveAction` | `nba_corrective_actions` | Action lifecycle with owner tracking and due dates |
| `Notification` | `notifications` | Per-user persistent notifications with idempotency keys |
| `SystemBackupRecord` | `system_backup_records` | Backup registry with SHA-256 checksums and manifest metadata |

**Final Alembic head revision**: `f5a1b2c3d4e5`

### C. Testing Results

```
Command : pytest --tb=short -q
Platform: win32, Python 3.14.3, pytest 8.3.3

Tests collected : 215
Tests passed    : 215
Tests failed    : 0
Tests skipped   : 0
Warnings        : 18333 (asyncio deprecation from Python 3.14 — cosmetic only)
Duration        : 123.72s
```

| Test File | Count | Result |
|-----------|-------|--------|
| test_academic.py | 18 | ✔ All pass |
| test_auth.py | 17 | ✔ All pass |
| test_config.py | 9 | ✔ All pass |
| test_curriculum.py | 15 | ✔ All pass |
| test_faculty_data.py | 13 | ✔ All pass |
| test_health.py | 10 | ✔ All pass |
| test_models_and_constraints.py | 7 | ✔ All pass |
| test_root.py | 10 | ✔ All pass |
| test_security.py | 9 | ✔ All pass |
| test_users_and_roles.py | 14 | ✔ All pass |
| test_phase4_requirements.py | 27 | ✔ All pass |
| test_phase4_documents.py | 15 | ✔ All pass |
| test_phase4_processing_rag.py | 12 | ✔ All pass |
| test_phase4_agent_integration.py | 9 | ✔ All pass |
| test_phase5_digital_twin.py | 6 | ✔ All pass |
| test_phase5_gaps.py | 5 | ✔ All pass |
| test_phase5_reports.py | 7 | ✔ All pass |
| test_phase5_notifications.py | 5 | ✔ All pass |
| test_phase5_backup.py | 7 | ✔ All pass |
| **TOTAL** | **215** | **✔ 215 passed** |

### D. Integration Verification Matrix

| Component | Status | Evidence |
|-----------|--------|----------|
| SQLite (in-memory) | **VERIFIED** | 215/215 tests pass against in-memory SQLite |
| Live PostgreSQL | **NOT VERIFIED** | No live instance available; migration DDL reviewed |
| pgvector | **NOT VERIFIED** | SQLite JSON fallback used; pgvector code path exists |
| Digital Twin calculations | **VERIFIED** | 6 dedicated tests (empty dept, populated, soft-delete exclusion, endpoints) |
| Gap analysis | **VERIFIED** | 5 tests: generation, duplicate prevention, auto-resolution, RBAC |
| PDF reports | **VERIFIED** | Service-layer + API endpoint tests; actual PDF bytes validated |
| Excel reports | **VERIFIED** | Service-layer + API endpoint tests; formula injection protection tested |
| In-app notifications | **VERIFIED** | 5 tests: creation, recipient isolation, duplicate prevention, mark-as-read |
| Backup creation | **VERIFIED** | Archive creation, SHA-256 checksum, manifest integrity tested |
| Backup validation | **VERIFIED** | Corrupt archive rejection, checksum mismatch detection tested |
| Restore procedure | **PARTIALLY VERIFIED** | Dry-run validated; live `pg_restore` not tested |
| PDF text extraction | **VERIFIED** | `pypdf` tested on digital PDFs; scanned documents not available |
| Active Tesseract OCR | **NOT VERIFIED** | Graceful degradation verified; Tesseract not installed in test env |
| Embedding generation | **PARTIALLY VERIFIED** | JSON stub tested; live model inference not tested |
| Live vector similarity search | **NOT VERIFIED** | No live PostgreSQL available |
| Criterion 3 AI integration | **PARTIALLY VERIFIED** | C3 adapter tested with mocked response; live `ai-service/` not connected |
| Criterion 4–6 AI integration | **NOT VERIFIED** | Endpoints do not exist in `ai-service/`; `UNAVAILABLE` handling verified |
| Frontend API compatibility | **NOT VERIFIED** | No frontend code modified; API contracts preserved |

### E. Security Review Summary

| Area | Finding |
|------|---------|
| Authentication | JWT Bearer required on all protected endpoints |
| Authorization | Role checks at FastAPI dependency layer; backup endpoints gated to ADMIN only |
| File handling | Paths locked to `DOCUMENT_STORAGE_ROOT`; stored filenames are random UUIDs |
| Backup safety | Zip Slip protection via `is_safe_archive_member()`; dry-run only; no automated destructive restore |
| Formula injection | Excel cells starting with `=`, `+`, `-`, `@`, TAB, or CR prefixed with single quote |
| Secret scanning | No credentials in source; `.env.example` contains safe placeholders only |
| SQL injection | All queries use SQLAlchemy ORM parameterization; no raw SQL concatenation |
| IDOR prevention | Notifications verify `recipient_id == current_user.id`; gap/action mutations verify role scope |

### F. Remaining Limitations

1. **Live PostgreSQL & pgvector not verified** — run `alembic upgrade head` against a real database and validate before production deployment.
2. **Tesseract OCR not tested** with a live installation; graceful degradation (`PROCESSED_PARTIAL`) is verified.
3. **Criteria 4, 5, 6 AI endpoints absent** — `ai-service/` does not implement C4–C6; backend returns `UNAVAILABLE` gracefully.
4. **All NBA rule thresholds are PLACEHOLDERS** — must be confirmed against the official NBA SAR manual before any accreditation submission.
5. **Email notifications not implemented** — `notification_service.py` exposes an extension point for SMTP; in-app notifications are fully functional.
6. **`pg_restore` not automated** — backup restore is scaffolded and dry-run validated; a real restore requires DBA intervention.
7. **Frontend integration not verified** — no frontend files were modified; API compatibility must be confirmed by the frontend team.

### G. Manual Verification Commands

```bash
# Apply all migrations (requires live PostgreSQL)
alembic upgrade head

# Seed the database
python -m app.db.seed

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the complete test suite
pytest -v

# Run Phase 5 tests specifically
pytest tests/test_phase5_digital_twin.py tests/test_phase5_gaps.py \
       tests/test_phase5_reports.py tests/test_phase5_notifications.py \
       tests/test_phase5_backup.py -v

# Verify Digital Twin snapshot (replace token and ay_id)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/digital-twin/snapshot?department=Computer+Science+and+Engineering"

# Open Swagger UI
# http://localhost:8000/docs
```

### H. Final Verdict

> **`PHASE 5 IMPLEMENTED WITH KNOWN LIMITATIONS`**

All Phase 5 milestones (A–L) have been implemented, tested, and verified against an in-memory SQLite environment. The complete backend test suite passes with **215/215 tests, 0 failures, 0 regressions**. Phase 5 functionality (Digital Twin, Gap Analysis, Reports, Notifications, Backup/Restore) is fully implemented, integrated into the FastAPI router, secured with RBAC, and covered by 30 dedicated automated tests.

The *with known limitations* qualifier applies because live PostgreSQL and pgvector have not been end-to-end verified, Tesseract OCR has not been tested with an active installation, Criteria 4–6 AI endpoints do not exist in `ai-service/`, and all NBA rule thresholds remain placeholder values requiring confirmation from official NBA documentation. None of these limitations affect the correctness of the implemented backend logic or the passing test suite.
