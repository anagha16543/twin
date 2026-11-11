"""
tests/test_root.py

Tests for the root endpoint and global API structure.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for GET /"""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Root endpoint must return HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_json(self, client: TestClient) -> None:
        """Root endpoint must return a JSON body."""
        response = client.get("/")
        assert response.headers["content-type"].startswith("application/json")

    def test_root_contains_service_key(self, client: TestClient) -> None:
        """Response must include a 'service' identifier."""
        data = client.get("/").json()
        assert "service" in data
        assert isinstance(data["service"], str)
        assert len(data["service"]) > 0

    def test_root_contains_version(self, client: TestClient) -> None:
        """Response must include a 'version' field."""
        data = client.get("/").json()
        assert "version" in data

    def test_root_contains_docs_link(self, client: TestClient) -> None:
        """Response must include a link to /docs."""
        data = client.get("/").json()
        assert "docs" in data
        assert data["docs"] == "/docs"

    def test_root_contains_health_link(self, client: TestClient) -> None:
        """Response must include a 'health' link pointing into /api/v1."""
        data = client.get("/").json()
        assert "health" in data
        assert data["health"].startswith("/api/v1")


class TestAPIPrefix:
    """Verify the /api/v1 prefix is active."""

    def test_health_reachable_under_api_prefix(self, client: TestClient) -> None:
        """GET /api/v1/health must be reachable (not 404)."""
        response = client.get("/api/v1/health")
        assert response.status_code != 404

    def test_v1_routes_not_accessible_without_prefix(self, client: TestClient) -> None:
        """The /health route must NOT be reachable without the api/v1 prefix."""
        response = client.get("/health")
        assert response.status_code == 404


class TestSwaggerDocs:
    """Verify Swagger UI and OpenAPI schema are served."""

    def test_swagger_ui_available(self, client: TestClient) -> None:
        """GET /docs must return HTTP 200."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_available(self, client: TestClient) -> None:
        """GET /openapi.json must return a valid OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
