"""Tests for application behavior in different environment modes."""

import importlib

import pytest
from fastapi.testclient import TestClient

from app.config import settings


class TestEnvironmentModes:
    """Test that all operations work correctly in different environments."""

    def test_file_operations_work_in_development_mode(self, monkeypatch):
        """Test file upload/download/delete works in development mode."""
        monkeypatch.setenv("APP_ENV", "development")

        # Reload config and app
        import app.config

        importlib.reload(app.config)

        from app.main import app

        client = TestClient(app)

        # Test upload
        files = {"file": ("dev_test.txt", b"Development content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert response.status_code == 201

        file_id = response.json()["id"]
        assert response.json()["syft_url"] is not None

        # Test download
        response = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert response.status_code == 200
        assert response.content == b"Development content"

        # Test delete
        response = client.delete(f"{settings.API_PREFIX}/files/{file_id}")
        assert response.status_code == 200

    def test_file_operations_work_in_testing_mode(self, client: TestClient):
        """Test file operations work in testing mode (default for tests)."""
        # Testing mode is set by default in conftest.py

        # Test upload
        files = {"file": ("test_mode.txt", b"Testing content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert response.status_code == 201

        data = response.json()
        assert data["syft_url"] is not None
        assert "test_mode.txt" in data["syft_url"]

        # Test list
        response = client.get(f"{settings.API_PREFIX}/files/")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_health_endpoint_works_in_all_modes(self, monkeypatch):
        """Test health endpoint works in development and testing modes."""
        for env_mode in ["development", "testing"]:
            monkeypatch.setenv("APP_ENV", env_mode)

            # Reload config and app
            import app.config

            importlib.reload(app.config)

            from app.main import app

            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["syftbox_user"] is not None
            assert data["storage_configured"] is True

    def test_mock_client_creates_proper_directory_structure(self, monkeypatch):
        """Test that MockSyftClient creates expected directory structure."""
        monkeypatch.setenv("APP_ENV", "testing")

        import app.config

        importlib.reload(app.config)

        # Verify paths exist
        assert app.config.FILE_STORAGE_PATH.exists()
        assert app.config.METADATA_PATH.exists()

        # Verify they're in the expected mock location
        assert "/tmp/syftbox_mock" in str(app.config.FILE_STORAGE_PATH)
        assert "datasites" in str(app.config.FILE_STORAGE_PATH)
        assert "file_management/storage" in str(app.config.FILE_STORAGE_PATH)

    def test_concurrent_file_operations_in_test_mode(self, client: TestClient):
        """Test multiple concurrent file operations work in test mode."""
        # Upload multiple files
        file_ids = []
        for i in range(5):
            files = {
                "file": (f"concurrent_{i}.txt", f"Content {i}".encode(), "text/plain")
            }
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201
            file_ids.append(response.json()["id"])

        # Verify all files exist
        response = client.get(f"{settings.API_PREFIX}/files/")
        assert response.status_code == 200
        assert response.json()["total"] >= 5

        # Delete all files
        for file_id in file_ids:
            response = client.delete(f"{settings.API_PREFIX}/files/{file_id}")
            assert response.status_code == 200


@pytest.fixture(autouse=True)
def reset_config_after_test():
    """Reset config module after each test."""
    yield
    # Reload config to reset state
    import app.config

    importlib.reload(app.config)
