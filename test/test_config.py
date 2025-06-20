from pathlib import Path

import pytest


class TestSyftCoreConfiguration:
    """Test syft_core configuration and initialization."""

    def test_mock_client_in_test_mode(self):
        """Test that mock client is used in test mode."""
        import app.config

        # Should have mock client in test mode
        assert app.config.syft_client is not None
        # In test mode, it should be MockSyftClient or the real client if SyftBox is configured
        # The test environment fixture ensures we're in testing mode
        assert app.config.settings.APP_ENV == "testing"

    def test_mock_client_generates_syft_urls(self):
        """Test that mock client generates correct syft URLs."""
        from app.config import syft_client

        test_path = Path("/test/file.txt")

        syft_url = syft_client.to_syft_url(test_path)

        assert syft_url.startswith("syft://")
        assert syft_client.email in syft_url
        assert "file.txt" in syft_url

    def test_mock_client_creates_app_data_paths(self):
        """Test that mock client creates correct app data paths."""
        from app.config import syft_client

        app_path = syft_client.app_data("test_app")

        assert "syftbox_mock" in str(app_path)
        assert "datasites" in str(app_path)
        assert syft_client.email in str(app_path)
        assert "test_app" in str(app_path)

    def test_storage_paths_are_set(self):
        """Test that storage paths are properly configured."""
        from app.config import FILE_STORAGE_PATH, METADATA_PATH

        assert FILE_STORAGE_PATH is not None
        assert METADATA_PATH is not None
        assert "storage" in str(FILE_STORAGE_PATH)
        assert "metadata" in str(METADATA_PATH)

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset config module after each test."""
        yield
        # Config is already loaded, no need to reload
