"""
tests/test_health.py

Tests for the health endpoints:
  GET /api/v1/health          — liveness probe
  GET /api/v1/health/db       — database readiness probe
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestLivenessProbe:
    """Tests for GET /api/v1/health"""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Liveness probe must return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client: TestClient) -> None:
        """Liveness probe must return a JSON body."""
        response = client.get("/api/v1/health")
        assert response.headers["content-type"].startswith("application/json")

    def test_health_status_ok(self, client: TestClient) -> None:
        """Liveness probe must report status='ok'."""
        data = client.get("/api/v1/health").json()
        assert data["status"] == "ok"

    def test_health_contains_service(self, client: TestClient) -> None:
        """Liveness probe must identify the service."""
        data = client.get("/api/v1/health").json()
        assert "service" in data

    def test_health_contains_version(self, client: TestClient) -> None:
        """Liveness probe must include a version string."""
        data = client.get("/api/v1/health").json()
        assert "version" in data

    def test_health_contains_environment(self, client: TestClient) -> None:
        """Liveness probe must include the current environment."""
        data = client.get("/api/v1/health").json()
        assert "environment" in data


class TestDBHealthProbe:
    """Tests for GET /api/v1/health/db"""

    def test_db_health_returns_200_when_db_ok(self, client: TestClient) -> None:
        """
        When the database is reachable, the endpoint must return HTTP 200
        with status='ok'.
        """
        mock_result = {"status": "ok", "detail": "Database connection is healthy."}
        with patch("app.api.v1.health.check_db_connection", return_value=mock_result):
            response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_db_health_returns_200_when_db_down(self, client: TestClient) -> None:
        """
        When the database is unreachable, the endpoint still returns HTTP 200
        but with status='error'.  The endpoint must NOT crash or return 5xx.
        """
        mock_result = {
            "status": "error",
            "detail": "Database unreachable: OperationalError",
        }
        with patch("app.api.v1.health.check_db_connection", return_value=mock_result):
            response = client.get("/api/v1/health/db")
        assert response.status_code == 200
        assert response.json()["status"] == "error"

    def test_db_health_does_not_expose_credentials(self, client: TestClient) -> None:
        """
        Even on error, the response must not contain the database password
        or full connection URL.
        """
        mock_result = {
            "status": "error",
            "detail": "Database unreachable: OperationalError",
        }
        with patch("app.api.v1.health.check_db_connection", return_value=mock_result):
            response = client.get("/api/v1/health/db")
        body = response.text
        # The test DATABASE_URL contains "testpass" — it must NOT appear in the response
        assert "testpass" not in body
        assert "postgresql+psycopg" not in body
        assert "postgresql+psycopg2" not in body

    def test_db_health_contains_status_key(self, client: TestClient) -> None:
        """Response must always include a 'status' key."""
        mock_result = {"status": "ok", "detail": "Database connection is healthy."}
        with patch("app.api.v1.health.check_db_connection", return_value=mock_result):
            data = client.get("/api/v1/health/db").json()
        assert "status" in data
