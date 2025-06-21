"""Tests for health endpoint functionality."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health endpoint reports syft_core status correctly."""

    def test_health_check_includes_syftbox_user(self, client: TestClient):
        """Test that health check includes syftbox_user field."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "syftbox_user" in data
        assert data["syftbox_user"] is not None

        # In testing mode, should be from MockSyftClient
        assert "@" in data["syftbox_user"]

    def test_health_check_reports_storage_configured(self, client: TestClient):
        """Test that health check reports storage_configured status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "storage_configured" in data
        assert data["storage_configured"] is True

    def test_health_check_includes_all_required_fields(self, client: TestClient):
        """Test that health check includes all required fields."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        required_fields = ["status", "syftbox_user", "storage_configured"]

        for field in required_fields:
            assert field in data
            assert data[field] is not None

        assert data["status"] == "healthy"

    def test_health_check_fails_without_syft_client(
        self, client: TestClient, monkeypatch
    ):
        """Test that health check fails gracefully without syft_client."""
        # Temporarily set syft_client to None
        monkeypatch.setattr("app.main.syft_client", None)

        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert "detail" in data
        assert "SyftBox not available" in data["detail"]

    def test_health_endpoint_performance(self, client: TestClient):
        """Test that health endpoint responds quickly."""
        import time

        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        assert response.status_code == 200

        # Health check should respond in less than 100ms
        response_time = (end_time - start_time) * 1000
        assert response_time < 100, f"Health check took {response_time}ms"

    def test_startup_event_validates_syft_core(self, monkeypatch):
        """Test that app startup validates syft_core availability."""
        # Test with syft_client set to None
        monkeypatch.setattr("app.main.syft_client", None)

        from app.main import app as fastapi_app
        from app.main import lifespan

        with pytest.raises(RuntimeError) as exc_info:
            import asyncio
            from contextlib import AsyncExitStack

            async def test_lifespan():
                async with AsyncExitStack() as stack:
                    await stack.enter_async_context(lifespan(fastapi_app))

            asyncio.run(test_lifespan())

        assert "SyftBox is not properly configured" in str(exc_info.value)
        assert "syftbox init" in str(exc_info.value)
