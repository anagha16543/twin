"""
AI-NBA Readiness System — Backend
api/v1/health.py

Health-check endpoints.  Two routes are exposed:

  GET /api/v1/health          — simple liveness probe
  GET /api/v1/health/db       — database connectivity probe (no credentials)
"""

from __future__ import annotations

from fastapi import APIRouter
from app.db.session import check_db_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Service liveness probe",
    response_description="Service is alive and responding.",
)
def health_check() -> dict:
    """
    Returns a lightweight liveness response.

    This endpoint does **not** touch the database, so it remains available
    even when the database is down.  Use it for container/load-balancer
    liveness probes.
    """
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@router.get(
    "/db",
    summary="Database readiness probe",
    response_description="Reports whether the database is reachable.",
)
def db_health_check() -> dict:
    """
    Attempts a minimal query (`SELECT 1`) against the configured database.

    * Returns `{"status": "ok", ...}` when the database is reachable.
    * Returns `{"status": "error", ...}` with a safe error type (no
      credentials or internal connection strings) when it is not.

    Use this as a readiness probe so that traffic is only routed to the
    service after the database is available.
    """
    result = check_db_connection()
    return result
