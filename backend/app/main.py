"""
AI-NBA Readiness System — Backend
app/main.py

FastAPI application factory.  A single `app` object is created here;
there is no competing entry point anywhere in the backend package.

Startup behaviour
-----------------
* Loads configuration from environment / .env file (via Settings).
* Mounts all v1 API routes under /api/v1.
* Configures CORS from environment variables — no credentials are
  embedded here.
* Provides Swagger UI at /docs and ReDoc at /redoc.
* Does NOT run Alembic migrations automatically on startup.
* Does NOT create default users or seed data.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import v1_router
from app.core.config import get_settings

settings = get_settings()

# --------------------------------------------------------------------------- #
# Application instance
# --------------------------------------------------------------------------- #

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "REST API for the AI-Driven NBA Accreditation Readiness System. "
        "Provides endpoints for managing accreditation data, health probes, "
        "and (in later phases) authentication, reports, and AI-agent integration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --------------------------------------------------------------------------- #
# Middleware
# --------------------------------------------------------------------------- #

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Global exception handler
# --------------------------------------------------------------------------- #

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exceptions.

    Returns a consistent JSON error shape without leaking internal details
    to the client.  The full traceback is still visible in server logs.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred. Please contact the administrator.",
        },
    )

# --------------------------------------------------------------------------- #
# Routers
# --------------------------------------------------------------------------- #

app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

# --------------------------------------------------------------------------- #
# Frontend (HTML/CSS/JS) served from <repo>/frontend at /app — one server,
# one port, no CORS setup needed. Open http://localhost:8000/app/
# --------------------------------------------------------------------------- #

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    @app.get("/portal", include_in_schema=False)
    def portal_redirect() -> RedirectResponse:
        return RedirectResponse(url="/app/")

# --------------------------------------------------------------------------- #
# Root endpoint
# --------------------------------------------------------------------------- #

@app.get(
    "/",
    tags=["Root"],
    summary="Service identification",
    response_description="Basic service metadata.",
)
def root() -> dict:
    """
    Root endpoint — identifies the service and reports basic metadata.

    This endpoint is intentionally lightweight and does not require
    authentication so that it can be used as a quick sanity-check.
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
