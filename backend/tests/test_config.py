"""
tests/test_config.py

Tests for the Settings / configuration loading module.
"""

from __future__ import annotations

import os
from unittest.mock import patch


class TestSettingsDefaults:
    """Verify that Settings returns correct defaults."""

    def test_default_app_name(self) -> None:
        """APP_NAME must have a sensible default."""
        # Clear the lru_cache so we get a fresh Settings instance
        from app.core.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings.APP_NAME, str)
        assert len(settings.APP_NAME) > 0

    def test_default_api_prefix(self) -> None:
        """API_V1_PREFIX must default to /api/v1."""
        from app.core.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.API_V1_PREFIX == "/api/v1"

    def test_default_database_url_is_set(self) -> None:
        """DATABASE_URL must be non-empty (provided via test env)."""
        from app.core.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.DATABASE_URL
        assert "postgresql" in settings.DATABASE_URL

    def test_app_version_format(self) -> None:
        """APP_VERSION must look like a semver string (e.g. 0.1.0)."""
        from app.core.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        parts = settings.APP_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestCORSOriginsProperty:
    """Verify that cors_origins_list parses CORS_ORIGINS correctly."""

    def test_single_origin(self) -> None:
        from app.core.config import get_settings
        get_settings.cache_clear()
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.cors_origins_list == ["http://localhost:3000"]

    def test_multiple_origins(self) -> None:
        from app.core.config import get_settings
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "http://localhost:3000,https://app.example.com"},
        ):
            get_settings.cache_clear()
            settings = get_settings()
            origins = settings.cors_origins_list
            assert "http://localhost:3000" in origins
            assert "https://app.example.com" in origins
            assert len(origins) == 2

    def test_origins_with_spaces_trimmed(self) -> None:
        from app.core.config import get_settings
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": " http://localhost:3000 , http://localhost:5173 "},
        ):
            get_settings.cache_clear()
            settings = get_settings()
            for origin in settings.cors_origins_list:
                assert origin == origin.strip()

    def teardown_method(self, _method) -> None:
        """Ensure the lru_cache is cleared after each test."""
        from app.core.config import get_settings
        get_settings.cache_clear()


class TestSettingsFromEnvironment:
    """Verify that environment variables override defaults."""

    def test_app_env_override(self) -> None:
        from app.core.config import get_settings
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.APP_ENV == "production"

    def test_debug_false_override(self) -> None:
        from app.core.config import get_settings
        with patch.dict(os.environ, {"DEBUG": "false"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.DEBUG is False

    def teardown_method(self, _method) -> None:
        from app.core.config import get_settings
        get_settings.cache_clear()
