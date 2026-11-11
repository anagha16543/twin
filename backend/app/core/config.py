"""
AI-NBA Readiness System — Backend
core/config.py

Reads all configuration from environment variables (or a .env file when
python-dotenv is available).  No secrets are hard-coded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings resolved from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Ignore extra env vars that are not declared here (e.g. OS variables)
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application metadata
    # ------------------------------------------------------------------ #
    APP_NAME: str = "AI-NBA Readiness System API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"          # development | staging | production
    DEBUG: bool = True

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    API_V1_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    # Comma-separated list of allowed origins, e.g.
    #   CORS_ORIGINS=http://localhost:3000,https://app.example.com
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a parsed list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/nba_readiness"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+psycopg://", 1)
            if v.startswith("postgresql+psycopg2://"):
                return v.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        return v

    # SQLAlchemy connection-pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800   # seconds — recycle connections after 30 min

    # ------------------------------------------------------------------ #
    # Security / JWT
    # ------------------------------------------------------------------ #
    JWT_SECRET_KEY: str = (
        "insecure-dev-jwt-secret-key-replace-in-production-min-32-bytes"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ------------------------------------------------------------------ #
    # Initial Admin / HOD Seed Credentials
    # ------------------------------------------------------------------ #
    INITIAL_ADMIN_EMAIL: str = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    INITIAL_HOD_EMAIL: str = "hod@example.com"
    INITIAL_HOD_PASSWORD: Optional[str] = None
    INITIAL_HOD_FACULTY_ID: str = "HOD001"
    INITIAL_HOD_NAME: str = "Head of Department"
    INITIAL_HOD_DEPARTMENT: str = "Computer Science & Engineering"

    # ------------------------------------------------------------------ #
    # Phase 4 — Document Storage
    # ------------------------------------------------------------------ #
    DOCUMENT_STORAGE_ROOT: str = "./documents/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB

    # ------------------------------------------------------------------ #
    # Phase 4 — AI Service Integration
    # ------------------------------------------------------------------ #
    AI_SERVICE_BASE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT_SECONDS: float = 30.0
    AI_SERVICE_API_KEY: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Phase 4 — RAG & Embeddings
    # ------------------------------------------------------------------ #
    EMBEDDING_MODEL: str = "local-minilm"
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE: Optional[str] = None
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    # ------------------------------------------------------------------ #
    # Phase 4 — OCR
    # ------------------------------------------------------------------ #
    TESSERACT_CMD: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Alembic (used by alembic/env.py to discover the URL)
    # ------------------------------------------------------------------ #
    # No extra field needed — Alembic will call get_settings().DATABASE_URL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
