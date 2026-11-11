"""
AI-NBA Readiness System — Backend
db/session.py

Provides a reusable SQLAlchemy 2.x engine and session factory.
The database URL is read exclusively from the Settings object — no
credentials are ever hard-coded here.

Usage (dependency injection):
    from app.db.session import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        ...
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


def _build_engine():
    """Create the SQLAlchemy engine from application settings."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        # Echo SQL statements only in debug mode
        echo=settings.DEBUG,
        # Validate connection liveness before returning from pool
        pool_pre_ping=True,
    )


# Module-level engine — initialised once on first import
engine = _build_engine()

# Session factory — does NOT auto-commit or auto-flush
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Import this in every model module:
        from app.db.session import Base
    """


# --------------------------------------------------------------------------- #
# FastAPI dependency
# --------------------------------------------------------------------------- #

def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and guarantee it is closed afterwards.

    Use as a FastAPI dependency:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Health-check helper (does not expose credentials)
# --------------------------------------------------------------------------- #

def check_db_connection() -> dict:
    """
    Attempt a lightweight query to verify database connectivity.

    Returns a dict with keys:
        status  — "ok" | "error"
        detail  — human-readable message (no credentials)
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "detail": "Database connection is healthy."}
    except Exception as exc:  # noqa: BLE001
        # Log the real error server-side; return only a safe summary to callers
        return {"status": "error", "detail": f"Database unreachable: {type(exc).__name__}"}
