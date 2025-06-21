import os
import shutil
import tempfile
from pathlib import Path

# Set test environment before any app imports
os.environ["APP_ENV"] = "testing"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set test environment for all tests."""
    monkeypatch.setenv("APP_ENV", "testing")


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_data():
    """Provide mock data for tests."""
    return {"test_name": "TestUser", "expected_message": "Hello from toy-project!"}


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for test isolation."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_syft_client(monkeypatch):
    """Mock syft_core client for testing."""

    class MockSyftClient:
        email = "test@example.com"

        def app_data(self, name):
            return Path("/tmp/test_datasite") / name

        def makedirs(self, path):
            path.mkdir(parents=True, exist_ok=True)

        def to_syft_url(self, path):
            return f"syft://test@example.com/test/path/{path.name}"

    mock_client = MockSyftClient()
    monkeypatch.setattr("app.config.syft_client", mock_client)
    monkeypatch.setattr("app.services.file_service.syft_client", mock_client)
    monkeypatch.setattr("app.config.settings.SYFT_USER_EMAIL", "test@example.com")

    return mock_client


@pytest.fixture
def mock_syft_client_custom():
    """Provide a customizable mock syft client."""
    from app.config import MockSyftClient

    return MockSyftClient("test@example.com")


@pytest.fixture
def ensure_syft_client(monkeypatch, mock_syft_client_custom):
    """Ensure syft_client is available for all tests."""
    monkeypatch.setattr("app.config.syft_client", mock_syft_client_custom)
    monkeypatch.setattr(
        "app.services.file_service.syft_client", mock_syft_client_custom
    )
    monkeypatch.setattr("app.main.syft_client", mock_syft_client_custom)
    monkeypatch.setattr(
        "app.config.settings.SYFT_USER_EMAIL", mock_syft_client_custom.email
    )
    return mock_syft_client_custom


@pytest.fixture(autouse=True)
def cleanup_test_storage():
    """Clean up test storage before and after each test."""
    # Import here to ensure it's after environment setup
    from app.config import FILE_STORAGE_PATH, METADATA_PATH

    # Get the base storage directory
    test_storage = Path("/tmp/syftbox_mock")

    # Clean before test
    if test_storage.exists():
        shutil.rmtree(test_storage, ignore_errors=True)

    # Also clean the specific storage paths
    if FILE_STORAGE_PATH.exists():
        shutil.rmtree(FILE_STORAGE_PATH, ignore_errors=True)
    if METADATA_PATH.exists():
        shutil.rmtree(METADATA_PATH, ignore_errors=True)

    # Recreate the directories
    FILE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.mkdir(parents=True, exist_ok=True)

    yield

    # Clean after test
    if test_storage.exists():
        shutil.rmtree(test_storage, ignore_errors=True)
