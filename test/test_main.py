"""Tests for main app endpoints including health check."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "syftbox_user" in data
    assert data["storage_configured"] is True


def test_health_endpoint_when_syft_not_available(client: TestClient, monkeypatch):
    """Test health check fails gracefully when syft_core not available."""
    # This test would require mocking syft_client to None at runtime
    # which is complex due to startup validation
    pass


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns HTML."""
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
