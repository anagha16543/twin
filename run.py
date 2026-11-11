#!/usr/bin/env python3
"""
NBA Twin Readiness — one-command launcher (Windows / macOS / Linux)

    python run.py            set up (first time) and start everything
    python run.py --reset    wipe the local database + uploads, then start
    python run.py --demo     start and load the Criterion 3 sample data
    python run.py --no-browser

What it does
  1. creates .venv and installs backend + AI-service requirements (first run only)
  2. writes backend/.env and ai-service/.env with local SQLite defaults (if missing)
  3. creates the database tables and seeds roles, HOD/admin, AY 2026-27, C3-C6
  4. starts the AI agent service on :8001 and the backend on :8000
     (the backend also serves the frontend at http://localhost:8000/app/)
  5. opens the browser. Press Ctrl+C to stop both servers.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
AI = ROOT / "ai-service"
VENV = ROOT / ".venv"
IS_WIN = os.name == "nt"
VPY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
DB_FILE = BACKEND / "nba_local.db"
URL = "http://localhost:8000/app/"

HOD_EMAIL = "hod@viit.ac.in"
HOD_PASSWORD = "Hod@12345"

BACKEND_ENV = f"""# Local development settings written by run.py
APP_ENV=development
DEBUG=false
DATABASE_URL=sqlite:///./nba_local.db
JWT_SECRET_KEY=local-dev-only-secret-change-me-0123456789abcdef
CORS_ORIGINS=http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=Admin@12345
INITIAL_HOD_EMAIL={HOD_EMAIL}
INITIAL_HOD_PASSWORD={HOD_PASSWORD}
INITIAL_HOD_FACULTY_ID=HOD001
INITIAL_HOD_NAME="Dr. K. Suresh"
INITIAL_HOD_DEPARTMENT="Artificial Intelligence and Machine Learning"
AI_SERVICE_BASE_URL=http://localhost:8001
AI_SERVICE_TIMEOUT_SECONDS=60
DOCUMENT_STORAGE_ROOT=./documents/uploads
"""

AI_ENV = """# AI service settings written by run.py
# Put your Groq key here for real AI answers, then set MOCK_LLM=false.
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
MOCK_LLM=true
"""


def say(msg: str) -> None:
    print(f"\033[92m==>\033[0m {msg}" if not IS_WIN else f"==> {msg}", flush=True)


def in_venv() -> bool:
    return Path(sys.executable).resolve() == VPY.resolve() if VPY.exists() else False


def ensure_venv() -> None:
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required (3.12+ recommended).")
    if not VPY.exists():
        say("Creating virtual environment in .venv (first run only)…")
        venv.EnvBuilder(with_pip=True).create(VENV)
    marker = VENV / ".deps_installed"
    reqs = [BACKEND / "requirements.txt", AI / "requirements.txt"]
    stamp = "".join(str(int(p.stat().st_mtime)) for p in reqs)
    if not marker.exists() or marker.read_text() != stamp:
        say("Installing dependencies (a few minutes the first time)…")
        subprocess.check_call([str(VPY), "-m", "pip", "install", "--upgrade", "pip", "-q"])
        subprocess.check_call([str(VPY), "-m", "pip", "install", "-q", "-r", str(reqs[0]), "-r", str(reqs[1])])
        marker.write_text(stamp)


def write_env_files() -> None:
    be = BACKEND / ".env"
    if not be.exists():
        be.write_text(BACKEND_ENV)
        say("Wrote backend/.env (SQLite, local demo accounts)")
    ae = AI / ".env"
    if not ae.exists():
        ae.write_text(AI_ENV)
        say("Wrote ai-service/.env (MOCK_LLM=true — add GROQ_API_KEY for real AI)")


def reset() -> None:
    for p in (DB_FILE, BACKEND / "documents" / "uploads"):
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
    say("Local database and uploads removed")


def init_db() -> None:
    say("Preparing database and seed data…")
    code = (
        "import app.models\n"
        "from app.db.session import Base, engine\n"
        "Base.metadata.create_all(bind=engine)\n"
        "from app.db.seed import seed_database\n"
        "seed_database()\n"
    )
    subprocess.check_call([str(VPY), "-c", code], cwd=str(BACKEND))


def wait_for(url: str, seconds: int = 60) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return True
        except Exception:
            time.sleep(0.7)
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="wipe local database and uploads first")
    ap.add_argument("--demo", action="store_true", help="load the Criterion 3 sample data after start")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    ensure_venv()
    write_env_files()
    if args.reset:
        reset()
    init_db()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WIN else 0
    say("Starting AI agent service on http://localhost:8001 …")
    ai = subprocess.Popen([str(VPY), "-m", "uvicorn", "main:app", "--port", "8001"], cwd=str(AI), env=env,
                          creationflags=flags)
    say("Starting backend on http://localhost:8000 …")
    be = subprocess.Popen([str(VPY), "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd=str(BACKEND), env=env,
                          creationflags=flags)
    procs = [ai, be]

    def stop(*_):
        say("Stopping servers…")
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    if not wait_for("http://localhost:8000/api/v1/health"):
        say("Backend did not start — see the error above.")
        stop()
    wait_for("http://localhost:8001/", 30)

    if args.demo:
        say("Loading Criterion 3 sample data…")
        subprocess.call([str(VPY), str(ROOT / "scripts" / "seed_c3_demo.py"),
                         "--email", HOD_EMAIL, "--password", HOD_PASSWORD])

    print()
    print("  Portal       ->  " + URL)
    print("  API docs     ->  http://localhost:8000/docs")
    print("  AI service   ->  http://localhost:8001/")
    print(f"  HOD login    ->  {HOD_EMAIL}  /  {HOD_PASSWORD}")
    print("  Stop         ->  Ctrl+C")
    print()
    if not args.no_browser:
        webbrowser.open(URL)

    while True:
        for p in procs:
            if p.poll() is not None:
                say("A server exited unexpectedly — stopping.")
                stop()
        time.sleep(1)


if __name__ == "__main__":
    main()
