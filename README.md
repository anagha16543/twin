# AI-Driven NBA Accreditation Readiness System

An enterprise-grade, accreditation-compliance intelligence platform designed for higher education institutions undergoing **National Board of Accreditation (NBA)** review under the **Manual for UG Engineering Tier I (2026 Edition)**.

The system pairs a **deterministic Python rule-evaluation engine** with a **centralized pgvector RAG pipeline** and **eight specialized AI agents** to audit institutional data, evaluate compliance, highlight accreditation risks, and prepare auditable self-assessment reports (SAR).

---

## Architecture Overview

```
                          ┌──────────────────────────────────────┐
                          │         Web Frontend / Client        │
                          └──────────────────┬───────────────────┘
                                             │ HTTP REST / JWT
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               FASTAPI BACKEND SERVICE                                  │
│                                                                                        │
│  ┌──────────────────────────┐   ┌─────────────────────────┐   ┌──────────────────────┐ │
│  │   Auth & RBAC (Deps)     │   │  Academic & Curriculum  │   │   Faculty Profiles   │ │
│  │  (ADMIN, HOD, FACULTY)   │   │  (CO-PO, Marks, Survey) │   │  & Research Records  │ │
│  └─────────────┬────────────┘   └────────────┬────────────┘   └──────────┬───────────┘ │
│                │                             │                           │             │
│                ▼                             ▼                           ▼             │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                 PostgreSQL Database with pgvector Extension                      │  │
│  │     Single Authoritative Store for Academic Data, Chunk Embeddings & Evidence     │  │
│  └───────────────────────────────────────────┬──────────────────────────────────────┘  │
│                                              │                                         │
│                ┌─────────────────────────────┴─────────────────────────────┐           │
│                ▼                                                           ▼           │
│  ┌───────────────────────────┐                           ┌───────────────────────────┐ │
│  │ Deterministic NBA Engine  │                           │ Database-Backed RAG       │ │
│  │ (Criteria 3, 4, 5, 6)     │                           │ (pgvector similarity)     │ │
│  │ Status: PASS, WARNING,    │                           │ Cosine Distance Search,   │ │
│  │ FAIL, NOT_APPLICABLE,     │                           │ Academic Year & Dept      │ │
│  │ NEEDS_RULE_CLARIFICATION  │                           │ Metadata Filters          │ │
│  └─────────────┬─────────────┘                           └─────────────┬─────────────┘ │
│                │                                                       │               │
│                │ Verified Metrics Dict                                 │ Passages      │
│                └─────────────────────────────┬─────────────────────────┘               │
└──────────────────────────────────────────────┼─────────────────────────────────────────┘
                                               │ HTTP JSON
                                               │ (Forward-Only Payload)
                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI AI SERVICE & AGENTS                               │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │  Privacy Layer (privacy_utils.py): Strips Phone, Email, PAN, Aadhaar, Bank PII   │  │
│  └───────────────────────────────────────────┬──────────────────────────────────────┘  │
│                                              │ Sanitized Context                       │
│                                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                             Specialized Agent Ensemble                           │  │
│  │  1. Assessment Agent (C3 Scheme)        5. Faculty Agent (C5 Roster & C6 R&D)    │  │
│  │  2. Student Agent (C4 Performance)      6. Compliance Agent (Cross-Criterion)    │  │
│  │  3. Coordinator Agent (C3 Synthesis)    7. Inspection Agent (Audit Readiness)    │  │
│  │  4. Document Agent (RAG Grounding)      8. Report Agent (Accreditation Report)   │  │
│  └───────────────────────────────────────────┬──────────────────────────────────────┘  │
│                                              │ Bounded Prompts (Advisory Only)         │
│                                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │  Centralized Model Client (model_client.py) -> Groq API (openai/gpt-oss-20b)     │  │
│  │  ai_drives_compliance = False (AI explains and summarizes; NEVER alters scores)  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core System Principles

1. **Deterministic Python Source of Truth**: All numeric metrics, percentages, Student-Faculty Ratios (SFR), Faculty Qualification Indices (FQI), success rates, and accreditation marks are computed strictly by deterministic Python functions. AI models never invent, extrapolate, or alter numeric scores.
2. **Advisory Role for AI (`ai_drives_compliance=False`)**: The LLM analyzes and contextualizes verified facts, identifies qualitative evidence gaps, highlights inspection risks, and drafts explanatory audit narratives. It cannot overturn compliance evaluations.
3. **Single Authoritative Document Store (pgvector)**: The PostgreSQL database with `pgvector` is the sole source of truth for accreditation evidence documents, chunk embeddings (384 dimensions), and similarity retrieval. In-memory vector stores are prohibited from acting as secondary document registries.
4. **Ambiguity Resolution Protocol (`NEEDS_RULE_CLARIFICATION`)**: Where the official NBA 2026 Manual leaves formula boundaries, strict inequalities, or double-counting policies undefined (e.g., SFR exactly on band boundaries, funding gaps between ₹1L–₹2L), the system returns `NEEDS_RULE_CLARIFICATION` rather than fabricating arbitrary scores.
5. **Strict PII Minimization**: Prior to forwarding faculty or student rosters to the LLM, `privacy_utils.py` strips all personally identifiable information (phone numbers, personal emails, residential addresses, Aadhaar, PAN, banking details).

---

## NBA Criteria 3, 4, 5 & 6 (Tier I 2026 Edition)

| Criterion | Name | Max Marks | Primary Formulas / Requirements |
|---|---|---|---|
| **Criterion 3** | Outcome-Based Assessment | **120** | Continuous assessment (3.1: 10m), SEE question paper evaluation (3.2: 10m), Lab/workshop conduct (3.3: 10m), Industrial training/internship (3.4: 10m), Projects evaluation (3.5: 20m), Sustainable Development Goals (SDG) (3.6: 10m), Direct/indirect CO attainment (3.7: 25m), PO/PSO attainment (3.8: 25m). Institutional attainment formula configuration required. |
| **Criterion 4** | Students' Performance | **120** | Enrolment Ratio $ER = \frac{N_1+N_4}{N}$ averaged over 3 yrs (4.1: 20m); Success Rate $SR = \frac{B}{\max(A, N+N_2)} \times 100$ and $Points = 1.5 \times \frac{AvgSR}{10}$, max 15 (4.2: 15m); Academic Performance Indices in Years 1–3 (4.3–4.5: 10m each); Placement & Higher Studies $Points = 0.3 \times AvgP$, max 30 (4.6: 30m); Professional activities (4.7: 25m). |
| **Criterion 5** | Faculty Information | **100** | Student-Faculty Ratio $SFR = \frac{S}{TF}$ bands 15 to 25 (5.1: 30m); Faculty Qualification Index $FQI = 2.5 \times \frac{10X + 4Y}{RF}$ where $RF = \frac{S}{20}$, max 25 (5.2: 25m); Faculty Cadre Proportion $AF_1/RF_1 + 0.6(AF_2/RF_2) + 0.4(AF_3/RF_3) \times 12.5$, max 25 (5.3: 25m); Visiting faculty provision & $\ge 50$ hrs/yr (5.4: 10m); Faculty retention rate $FR = \frac{\sum w_i N_i}{RF} \times 2.50$, max 10 (5.5: 10m). |
| **Criterion 6** | Faculty Contributions | **120** | **6.1 Professional Development (60)**: Memberships (6.1.1: 5m), Resource persons (6.1.2.1: 5m), FDP participation (6.1.2.2: 5m), MOOC dev (6.1.3: 7m), MOOC certifications (6.1.4: 8m), FDPs organized $\ge 5$ days (6.1.5: 10m), Student innovation (6.1.6: 10m), Industry training (6.1.7: 10m).<br>**6.2 R&D (60)**: Publications count & quality (6.2.1: 10m), PhD students guided (6.2.2: 5m), Patents & prototypes (6.2.3: 10m), Sponsored research up to 15 marks (6.2.4: 15m), Consultancy up to 15 marks (6.2.5: 15m), Seed money (6.2.6: 5m). |

---

## Specialized AI Agents Ensemble

All eight agents reside in `ai-service/app/agents/` and use `model_client.py` for bounded LLM generation via Groq:

1. **Assessment Agent (`assessment_agent.py`)**: Summarizes Criterion 3 assessment schemes, reports assessment-to-CO coverage, and flags missing rubric records.
2. **Student Agent (`student_agent.py`)**: Explains student academic performance, grade distributions, progression, and placement outcomes without recalculating metrics.
3. **Coordinator Agent (`coordinator_agent.py`)**: Synthesizes verified findings from the Assessment Agent and Student Agent into an auditable Criterion 3 narrative.
4. **Document Agent (`document_agent.py`)**: Answers user queries strictly grounded in passages pre-retrieved from the PostgreSQL/pgvector RAG store with page-level citations.
5. **Faculty Agent (`faculty_agent.py`)**: Explains faculty roster distribution (Criterion 5) and research contributions/patents/grants (Criterion 6) after PII stripping.
6. **Compliance Agent (`compliance_agent.py`)**: Cross-criterion audit agent analyzing system-wide gaps, unresolved threshold warnings, and pending documentation.
7. **Inspection Agent (`inspection_agent.py`)**: Simulates an on-site NBA Visiting Team chair review, evaluating institutional readiness and document verification status.
8. **Report Agent (`report_agent.py`)**: Compiles comprehensive institutional self-assessment reports (SAR) across all evaluated requirements.

---

## Installation & Setup

### Prerequisites

* **Python**: 3.12+ (tested and verified on Python 3.14.3)
* **PostgreSQL**: 14+ with the `pgvector` extension installed (`CREATE EXTENSION vector;`)
* **Operating System**: Windows (PowerShell), macOS, or Linux
* **OCR (Optional)**: Tesseract 5.x for scanned document fallback

### 1. Backend Setup

```powershell
# Navigate to the backend directory
cd C:\dev\AI-NBA-Readiness-System\backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Seed NBA Criteria 3-6 requirements and admin accounts
python -m app.db.seed
```

### 2. AI Service Setup

```powershell
# Navigate to the AI service directory
cd C:\dev\AI-NBA-Readiness-System\ai-service

# Install dependencies (in backend venv or separate dedicated venv)
pip install -r requirements.txt
```

---

## Environment Variables Configuration

Copy `.env.example` or set the following in your deployment environment:

| Variable | Default Value | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/nba_db` | Primary PostgreSQL database connection string |
| `TEST_DATABASE_URL` | `sqlite:///:memory:` | In-memory SQLite for instantaneous local test suites |
| `SECRET_KEY` | *(Set securely)* | JWT signature secret key |
| `ALGORITHM` | `HS256` | JWT encoding algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Access token lifespan (8 hours) |
| `AI_SERVICE_BASE_URL` | `http://localhost:8001` | URL of the running AI agent service |
| `AI_SERVICE_TIMEOUT_SECONDS` | `30.0` | HTTP request timeout for AI analysis requests |
| `GROQ_API_KEY` | *(Set securely)* | Groq Cloud API key for LLM inference |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible API base URL |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Production LLM model identifier |
| `MOCK_LLM` | `false` | When `true`, returns mock responses without making external API calls |

---

## Running the Services

### Start Backend Service (Port 8000)

```powershell
cd C:\dev\AI-NBA-Readiness-System\backend
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* Interactive Swagger API Docs: `http://localhost:8000/docs`
* OpenAPI JSON Specification: `http://localhost:8000/openapi.json`

### Start AI Service (Port 8001)

```powershell
cd C:\dev\AI-NBA-Readiness-System\ai-service
..\backend\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

* AI Service Health Check: `http://localhost:8001/`

---

## Verification & Testing

The system includes comprehensive automated tests covering database models, authentication, role-based access control, document RAG pipelines, deterministic rules, ambiguity handlers, and agent mock evaluations.

### 1. Run Complete Backend Test Suite (247 Tests)

```powershell
cd C:\dev\AI-NBA-Readiness-System\backend
.\.venv\Scripts\pytest.exe -v
```

**Results**: **247 passed, 0 failed** in ~111s.

Test coverage breakdown:
* `tests/test_academic.py`: Academic year and subject management
* `tests/test_curriculum.py`: COs, CO-PO mappings, marks, and grade distributions
* `tests/test_faculty_data.py`: Faculty publications, patents, projects, and consultancies
* `tests/test_phase4_requirements.py`: NBA models, constraints, and idempotent seeding
* `tests/test_phase4_documents.py`: Multipart uploads, chunking, and validation lifecycle
* `tests/test_phase4_processing_rag.py`: Vector retrieval, cosine distance, and department filters
* `tests/test_phase4_agent_integration.py`: Agent contract, advisory enforcement, and unavailable handling
* `tests/test_phase5_digital_twin.py`: Simulation and hypothetical score adjustments
* `tests/test_phase5_gaps.py`: Evidence gap analysis and lifecycle management
* `tests/test_phase5_reports.py`: PDF, CSV, and summary report generation
* `tests/test_phase5_notifications.py`: Accreditation notification dispatching
* `tests/test_phase5_backup.py`: Database backup creation and manifest integrity
* `tests/test_nba_2026_rules.py`: **32 tests** verifying all NBA Tier-I 2026 deterministic rules, sub-criterion weightages, boundary ambiguities, and context aggregators

### 2. Run AI Service Agent Test Suite (15 Tests)

```powershell
cd C:\dev\AI-NBA-Readiness-System\ai-service
..\backend\.venv\Scripts\pytest.exe tests/test_agents.py -v
```

**Results**: **15 passed, 0 failed** in ~1s.

Verifies:
* PII stripping by `privacy_utils.py` (non-mutating shallow copies)
* Offline mock-mode execution of all 8 agents
* Document Agent RAG citation grounding with synthetic passages
* AI Service FastAPI endpoint response formatting

### 3. Verification Matrix

| Component | Status | Verification Details |
|---|---|---|
| **SQLite (In-Memory)** | **VERIFIED** | 247/247 tests passing against SQLite in-memory engine. |
| **Offline Mock LLM** | **VERIFIED** | 15/15 agent tests passing using mock responses (`MOCK_LLM=true`). |
| **NBA 2026 Deterministic Rules** | **VERIFIED** | Criteria 3, 4, 5, 6 verified against official Tier-I manual (Annexure VII, pp. 155–168). |
| **Live PostgreSQL & pgvector** | **NOT VERIFIED** | Tested with SQLite JSON fallback; migration DDL generated and reviewed. |
| **Live Groq API** | **NOT VERIFIED** | Live API calls require valid `GROQ_API_KEY` and network access. |

---

## Project Structure

```
C:\dev\AI-NBA-Readiness-System\
├── backend/
│   ├── app/
│   │   ├── api/v1/                   # FastAPI REST route handlers
│   │   ├── business_rules/           # Deterministic NBA calculation rules
│   │   │   ├── readiness_rules.py    # Rule registry & EvaluationResult dataclass
│   │   │   ├── criterion3_rules.py   # CO-PO attainment & continuous assessment (120 marks)
│   │   │   ├── criterion4_rules.py   # ER, SR, API, placement (120 marks)
│   │   │   ├── criterion5_rules.py   # SFR, FQI, Cadre, retention (100 marks)
│   │   │   └── criterion6_rules.py   # Professional dev & R&D (120 marks)
│   │   ├── core/                     # Configuration, settings & security
│   │   ├── db/                       # SQLAlchemy session & seed scripts (seed_phase4.py)
│   │   ├── models/                   # ORM data models (academic, faculty, phase4, phase5)
│   │   └── services/                 # RAG, readiness, gap, and context services
│   │       ├── agent_client.py       # HTTP client connecting backend to AI agents
│   │       ├── criteria_context_service.py # Database aggregator for C3-C6 rules
│   │       └── rag_service.py        # pgvector RAG ingestion & cosine retrieval
│   ├── tests/                        # 240 automated pytest unit & integration tests
│   └── requirements.txt              # Backend Python dependencies
├── ai-service/
│   ├── app/
│   │   ├── agents/                   # Eight specialized accreditation AI agents
│   │   ├── services/
│   │   │   ├── metrics_service.py    # Deterministic analytics helper functions
│   │   │   └── model_client.py       # Centralized Groq API client with fallback
│   │   └── utils/
│   │       └── privacy_utils.py      # PII sanitization utilities
│   ├── tests/                        # Automated agent test suite (15 tests)
│   ├── main.py                       # AI Service FastAPI application entry point
│   └── requirements.txt              # AI Service dependencies
├── nba_documents/                    # Working rulebook & official NBA Tier I manual
└── README.md                         # System documentation & architectural reference
```

---

## License & Compliance

Developed for institutional accreditation preparation following official National Board of Accreditation (NBA) guidelines. All calculated figures and criteria interpretations must be verified by the institutional Internal Quality Assurance Cell (IQAC) prior to official SAR submission.
