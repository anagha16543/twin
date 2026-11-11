"""
AI-NBA Readiness System — Backend
api/v1/router.py

Aggregates all v1 API routers into a single APIRouter that is then
mounted on the FastAPI application by main.py.

Adding a new domain router:
    1. Create backend/app/api/v1/<domain>.py with its own APIRouter.
    2. Import it here and call v1_router.include_router(...)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analysis,
    auth,
    backups,
    criterion3,
    curriculum,
    digital_twin,
    documents,
    faculty_data,
    gaps,
    health,
    notifications,
    reports,
    requirements,
    subjects,
    users,
)

v1_router = APIRouter()

v1_router.include_router(health.router)
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(subjects.router)
v1_router.include_router(faculty_data.router)
v1_router.include_router(curriculum.router)
v1_router.include_router(requirements.router)
v1_router.include_router(documents.router)
v1_router.include_router(analysis.router)
v1_router.include_router(digital_twin.router)
v1_router.include_router(gaps.router)
v1_router.include_router(reports.router)
v1_router.include_router(notifications.router)
v1_router.include_router(backups.router)
v1_router.include_router(criterion3.router)

