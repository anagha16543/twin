# NBA Twin Readiness — Criterion 3 (start here)

Everything is in this one folder: the backend (FastAPI + rule engine), the AI agents, the HTML/CSS/JS frontend and sample data.

## Run it in Antigravity (or VS Code / any terminal)

1. **Open the folder.** Choose **File → Open Folder** and select this folder.
2. **Open a terminal.** Use **Terminal → New Terminal**.
3. **Start everything:**
   ```bash
   python run.py
   ```
   On Windows, use `py run.py` if `python` isn't on your PATH. You need Python **3.10+** (3.12 recommended).
4. **Wait for setup.** The first run creates `.venv` and installs dependencies, which takes 2–5 minutes. Later runs start in a few seconds.
5. **Use the portal.** Your browser opens **http://localhost:8000/app/**:
   splash screen → login → Criterion 3 dashboard.

| What | Where |
|---|---|
| Portal | http://localhost:8000/app/ |
| Backend API docs (Swagger) | http://localhost:8000/docs |
| AI agent service | http://localhost:8001/ |
| HOD login | `hod@viit.ac.in` / `Hod@12345` |
| Admin login | `admin@example.com` / `Admin@12345` |

Stop with **Ctrl+C**.

### Options

```bash
python run.py --reset   # wipe the local database + uploads (fresh start)
python run.py --demo    # start and load all sample data (3 courses, marks, surveys, rubric, evidence)
python run.py --reset --demo
```

### Real AI answers

The AI agents run in **mock mode** by default, so they return fake text and the app still works offline. For real analysis:
1. Put your key in `ai-service/.env`: `GROQ_API_KEY=...`
2. Set `MOCK_LLM=false` in the same file.
3. Restart.

The AI is advisory only and never changes a score.

## What happens in Criterion 3

```
CO-PO matrix + marks CSV (question → CO)
        → CO attainment  (CIE + SEE direct, course-exit-survey indirect)
        → PO / PSO attainment (Tables 3.8.1 – 3.8.3)
        → NBA Tier-I 2026 Annexure VII rubric for 3.1 – 3.8
             • computed parts: 3.1-C, 3.7.2, 3.8-B   (from your data)
             • reviewer parts: everything else       (HOD scores from evidence)
        → deterministic PASS / WARNING / FAIL, readiness %, gaps
        → weak CO → gap → corrective action → re-assessment → gap auto-closes
```

To check that it really works, follow **[VERIFY_C3.md](VERIFY_C3.md)** step by step.

## Folder map

```
run.py                one-command launcher
START_HERE.md         this file
VERIFY_C3.md          step-by-step Criterion 3 verification
sample_data/          CO-PO matrices + marks CSVs for 3 AIML courses (+ post-remedial marks)
frontend/             HTML/CSS/JS portal (served by the backend at /app)
backend/              FastAPI, rule engine, Criterion 3 service, tests
ai-service/           8 AI agents (Groq), FastAPI on :8001
scripts/seed_c3_demo.py  loads sample data through the API
nba_documents/        NBA Tier-I 2026 manual + rulebook
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Invalid email or password" | The database was seeded with other accounts. Run `python run.py --reset`. |
| Port 8000 / 8001 already in use | Close the other server (or the old `run.py` window), then run again. |
| `pip install` fails on a package | Use Python 3.12, delete `.venv`, run `python run.py` again. |
| The page shows "Could not load the workspace" | The backend isn't running. Check the terminal for the error. |
| Want PostgreSQL instead of SQLite | Set `DATABASE_URL` in `backend/.env`, then run `alembic upgrade head` in `backend/`. |
