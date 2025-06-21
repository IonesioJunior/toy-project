"""Tests for mandatory syft_core behavior in different environments."""

import importlib

import pytest
from syft_core.exceptions import SyftBoxException


def test_production_requires_real_syft_core(monkeypatch):
    """Test that production mode fails without real syft_core."""
    monkeypatch.setenv("APP_ENV", "production")

    # Mock Client.load to raise exception
    def mock_load():
        raise SyftBoxException("SyftBox not configured")

    monkeypatch.setattr("syft_core.Client.load", mock_load)

    with pytest.raises(RuntimeError) as exc_info:
        import app.config

        importlib.reload(app.config)

    assert "Failed to initialize syft_core" in str(exc_info.value)
    assert "syftbox init" in str(exc_info.value)


def test_development_uses_mock_syft_core(monkeypatch):
    """Test that development mode uses mock successfully."""
    monkeypatch.setenv("APP_ENV", "development")

    import app.config

    importlib.reload(app.config)

    assert app.config.syft_client is not None
    assert isinstance(app.config.syft_client, app.config.MockSyftClient)
    assert app.config.syft_client.email == "dev@test.local"


def test_testing_uses_mock_syft_core(monkeypatch):
    """Test that testing mode uses mock successfully."""
    monkeypatch.setenv("APP_ENV", "testing")

    import app.config

    importlib.reload(app.config)

    assert app.config.syft_client is not None
    assert isinstance(app.config.syft_client, app.config.MockSyftClient)


def test_mock_syft_client_generates_correct_urls():
    """Test that MockSyftClient generates correct syft URLs."""
    from pathlib import Path

    from app.config import MockSyftClient

    mock_client = MockSyftClient("test@example.com")
    test_path = Path("/some/path/file.txt")

    syft_url = mock_client.to_syft_url(test_path)

    assert syft_url == "syft://test@example.com/app_data/file_management/storage/file.txt"
    assert mock_client.email == "test@example.com"


def test_mock_syft_client_creates_directories():
    """Test that MockSyftClient creates directories correctly."""
    import tempfile
    from pathlib import Path

    from app.config import MockSyftClient

    with tempfile.TemporaryDirectory() as temp_dir:
        mock_client = MockSyftClient()
        mock_client._base_path = Path(temp_dir)

        app_path = mock_client.app_data("test_app")
        mock_client.makedirs(app_path)

        assert app_path.exists()
        assert app_path.is_dir()


@pytest.fixture(autouse=True)
def reset_config(monkeypatch):
    """Reset config module after each test."""
    yield
    # Reset to testing mode after test
    monkeypatch.setenv("APP_ENV", "testing")
    import app.config

    importlib.reload(app.config)
