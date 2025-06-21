"""Tests for syft_url generation and presence in API responses."""

from fastapi.testclient import TestClient

from app.config import settings


class TestSyftUrlGeneration:
    """Test that syft_url is always present and valid in API responses."""

    def test_upload_returns_syft_url(self, client: TestClient):
        """Test that file upload returns a non-null syft_url."""
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 201
        data = response.json()

        # Verify syft_url is present and not None
        assert "syft_url" in data
        assert data["syft_url"] is not None
        assert isinstance(data["syft_url"], str)
        assert data["syft_url"].startswith("syft://")
        assert "test.txt" in data["syft_url"]

    def test_list_includes_syft_url_for_all_files(self, client: TestClient):
        """Test that file list includes syft_url for all files."""
        # Upload multiple files
        files_to_upload = [
            ("test1.txt", b"Content 1", "text/plain"),
            ("test2.pdf", b"Content 2", "application/pdf"),
            ("test3.csv", b"Content 3", "text/csv"),
        ]

        uploaded_ids = []
        for filename, content, content_type in files_to_upload:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201
            uploaded_ids.append(response.json()["id"])

        # List files
        response = client.get(f"{settings.API_PREFIX}/files/")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= len(files_to_upload)

        # Check each file has syft_url
        for file_info in data["files"]:
            if file_info["id"] in uploaded_ids:
                assert "syft_url" in file_info
                assert file_info["syft_url"] is not None
                assert isinstance(file_info["syft_url"], str)
                assert file_info["syft_url"].startswith("syft://")

    def test_update_maintains_syft_url_format(self, client: TestClient):
        """Test that file update maintains syft_url format."""
        # Upload initial file
        files = {"file": ("original.txt", b"Original content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert response.status_code == 201

        file_id = response.json()["id"]
        original_syft_url = response.json()["syft_url"]

        # Update file
        new_files = {"file": ("updated.txt", b"Updated content", "text/plain")}
        response = client.put(f"{settings.API_PREFIX}/files/{file_id}", files=new_files)
        assert response.status_code == 200

        data = response.json()
        assert "syft_url" in data
        assert data["syft_url"] is not None
        assert isinstance(data["syft_url"], str)
        assert data["syft_url"].startswith("syft://")
        assert "updated.txt" in data["syft_url"]

        # Verify the URL changed to reflect new filename
        assert data["syft_url"] != original_syft_url

    def test_syft_url_follows_expected_pattern(self, client: TestClient):
        """Test that syft_url follows the expected pattern."""
        files = {"file": ("pattern_test.txt", b"Test content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 201
        syft_url = response.json()["syft_url"]

        # Expected pattern: syft://email/app_data/file_management/storage/filename
        assert syft_url.startswith("syft://")

        # In testing mode, email should be from MockSyftClient
        assert "@" in syft_url  # Contains email
        assert "/app_data/file_management/storage/" in syft_url
        assert syft_url.endswith("pattern_test.txt")

    def test_storage_stats_includes_syft_paths(self, client: TestClient):
        """Test that storage stats includes syft-based storage path."""
        response = client.get(f"{settings.API_PREFIX}/files/stats/summary")
        assert response.status_code == 200

        data = response.json()
        assert "storage_path" in data
        assert data["storage_path"] is not None

        # In testing mode, should include mock path
        storage_path = data["storage_path"]
        assert "syftbox_mock" in storage_path or "datasite" in storage_path
