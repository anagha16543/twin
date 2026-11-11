# =============================================================================
# AI-NBA Readiness System — Backend Dockerfile
# =============================================================================

# Python 3.12 slim — stable production base (minimum version: 3.12+).
# The development venv runs 3.14; adjust the base tag if your registry supports it.
FROM python:3.12-slim AS base

# Keeps Python from generating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering so logs appear immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /backend

# Install system dependencies:
#   build-essential  — C compilation for any source-built packages
#   tesseract-ocr    — OCR engine (Phase 4; gracefully skipped if absent)
#   libpq-dev        — PostgreSQL client headers (psycopg binary is self-contained but kept for safety)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies separately to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Default command — runs with uvicorn; override in docker-compose for dev reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
