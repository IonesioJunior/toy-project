from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def cleanup_storage(temp_test_dir, monkeypatch):
    """Ensure clean state between tests."""
    storage_path = Path(temp_test_dir) / "storage"
    metadata_path = Path(temp_test_dir) / "metadata"

    # Setup clean directories
    storage_path.mkdir(parents=True, exist_ok=True)
    metadata_path.mkdir(parents=True, exist_ok=True)

    # Mock paths to use temp directory
    monkeypatch.setattr("app.config.FILE_STORAGE_PATH", storage_path)
    monkeypatch.setattr("app.config.METADATA_PATH", metadata_path)
    monkeypatch.setattr("app.services.file_service.FILE_STORAGE_PATH", storage_path)
    monkeypatch.setattr("app.services.file_service.METADATA_PATH", metadata_path)

    # Use mock syft_client for route tests
    from app.config import MockSyftClient

    mock_client = MockSyftClient("test@example.com")
    monkeypatch.setattr("app.config.syft_client", mock_client)
    monkeypatch.setattr("app.services.file_service.syft_client", mock_client)
    monkeypatch.setattr("app.config.settings.SYFT_USER_EMAIL", "test@example.com")

    yield

    # Cleanup is handled by temp_test_dir fixture


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Force app reload to pick up mocked paths
    return TestClient(app)


class TestFileRoutes:
    """Integration tests for file management API endpoints."""

    def test_upload_file_success(self, client):
        """Test successful file upload."""
        files = {"file": ("test.txt", b"Hello, World!", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test.txt"
        assert data["message"] == "File uploaded successfully"

    def test_upload_file_no_file(self, client):
        """Test upload without file."""
        response = client.post(f"{settings.API_PREFIX}/files/")
        assert response.status_code == 422  # Validation error

    def test_upload_file_size_limit(self, client, monkeypatch):
        """Test file size limit enforcement."""
        # Patch in the module where it's used
        monkeypatch.setattr(
            "app.utils.file_utils.settings.MAX_FILE_SIZE", 10
        )  # 10 bytes limit

        files = {
            "file": (
                "large.txt",
                b"This content is too large for the limit",
                "text/plain",
            )
        }
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]

    def test_upload_file_invalid_type(self, client, monkeypatch):
        """Test invalid file type rejection."""
        # Restrict to only images - patch in the module where it's used
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_MIME_TYPES",
            {"image/jpeg", "image/png"},
        )
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_EXTENSIONS",
            {".jpg", ".jpeg", ".png"},
        )

        files = {"file": ("test.txt", b"Text content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 415
        assert "File type not allowed" in response.json()["detail"]

    def test_list_files_empty(self, client):
        """Test listing files when none exist."""
        response = client.get(f"{settings.API_PREFIX}/files/")

        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total"] == 0

    def test_list_files_with_data(self, client):
        """Test listing multiple files."""
        # Upload multiple files
        test_files = [
            ("file1.txt", b"Content 1", "text/plain"),
            ("file2.txt", b"Content 2", "text/plain"),
            ("file3.txt", b"Content 3", "text/plain"),
        ]

        uploaded_ids = []
        for filename, content, content_type in test_files:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201
            uploaded_ids.append(response.json()["id"])

        # List files
        response = client.get(f"{settings.API_PREFIX}/files/")
        assert response.status_code == 200

        data = response.json()
        assert len(data["files"]) == 3
        assert data["total"] == 3

        # Verify all uploaded files are in the list
        listed_ids = [file["id"] for file in data["files"]]
        for file_id in uploaded_ids:
            assert file_id in listed_ids

    def test_download_file_success(self, client):
        """Test successful file download."""
        # Upload a file
        content = b"Download test content"
        files = {"file": ("download_test.txt", content, "text/plain")}
        upload_response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_response.status_code == 201
        file_id = upload_response.json()["id"]

        # Download the file
        download_response = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_response.status_code == 200
        assert download_response.content == content
        assert download_response.headers["content-type"] == "text/plain; charset=utf-8"
        assert (
            'attachment; filename="download_test.txt"'
            in download_response.headers["content-disposition"]
        )

    def test_download_file_not_found(self, client):
        """Test downloading non-existent file."""
        response = client.get(f"{settings.API_PREFIX}/files/non-existent-id")
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]

    def test_update_file_success(self, client):
        """Test successful file update."""
        # Upload original file
        files = {"file": ("original.txt", b"Original content", "text/plain")}
        upload_response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_response.status_code == 201
        file_id = upload_response.json()["id"]

        # Update with new file
        new_files = {"file": ("updated.txt", b"Updated content", "text/plain")}
        update_response = client.put(
            f"{settings.API_PREFIX}/files/{file_id}", files=new_files
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["id"] == file_id  # ID should remain the same
        assert data["filename"] == "updated.txt"
        assert data["message"] == "File updated successfully"

        # Verify content was updated
        download_response = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_response.content == b"Updated content"

    def test_update_file_not_found(self, client):
        """Test updating non-existent file."""
        files = {"file": ("new.txt", b"New content", "text/plain")}
        response = client.put(
            f"{settings.API_PREFIX}/files/non-existent-id", files=files
        )

        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]

    def test_delete_file_success(self, client):
        """Test successful file deletion."""
        # Upload a file
        files = {"file": ("delete_test.txt", b"Delete me", "text/plain")}
        upload_response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_response.status_code == 201
        file_id = upload_response.json()["id"]

        # Delete the file
        delete_response = client.delete(f"{settings.API_PREFIX}/files/{file_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "File deleted successfully"

        # Verify file is gone
        download_response = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_response.status_code == 404

    def test_delete_file_not_found(self, client):
        """Test deleting non-existent file."""
        response = client.delete(f"{settings.API_PREFIX}/files/non-existent-id")
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]

    def test_get_storage_stats(self, client):
        """Test storage statistics endpoint."""
        # Upload some files
        test_files = [
            ("file1.txt", b"A" * 100, "text/plain"),  # 100 bytes
            ("file2.txt", b"B" * 200, "text/plain"),  # 200 bytes
            ("file3.txt", b"C" * 300, "text/plain"),  # 300 bytes
        ]

        for filename, content, content_type in test_files:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201

        # Get stats
        response = client.get(f"{settings.API_PREFIX}/files/stats/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["total_files"] == 3
        assert data["total_size"] == 600  # 100 + 200 + 300
        assert "max_file_size" in data
        assert "storage_path" in data

    def test_file_with_special_characters(self, client):
        """Test handling files with special characters in filename."""
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "fiлe_with_unicode.txt",
            "file@special#chars.txt",
        ]

        for filename in special_names:
            files = {"file": (filename, b"Content", "text/plain")}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201

            # Verify sanitized filename
            data = response.json()
            assert data["filename"]  # Should have a filename
            assert ".." not in data["filename"]  # No path traversal

    def test_concurrent_file_operations(self, client):
        """Test handling concurrent file operations."""
        import concurrent.futures

        def upload_file(index):
            files = {
                "file": (
                    f"concurrent_{index}.txt",
                    f"Content {index}".encode(),
                    "text/plain",
                )
            }
            return client.post(f"{settings.API_PREFIX}/files/", files=files)

        # Upload files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_file, i) for i in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All uploads should succeed
        assert all(response.status_code == 201 for response in responses)

        # Verify all files exist
        list_response = client.get(f"{settings.API_PREFIX}/files/")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 10

    def test_api_documentation(self, client):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

        # Check that file endpoints are documented
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()

        # Verify file endpoints exist in the API spec
        paths = openapi["paths"]
        assert f"{settings.API_PREFIX}/files/" in paths
        assert f"{settings.API_PREFIX}/files/{{file_id}}" in paths
        assert f"{settings.API_PREFIX}/files/stats/summary" in paths

    def test_upload_returns_syft_url(self, client):
        """Test that syft_url is included in upload response when syft_core is enabled."""
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 201
        data = response.json()
        assert "syft_url" in data
        assert data["syft_url"] is not None
        assert data["syft_url"].startswith("syft://test@example.com/")

    def test_list_files_includes_syft_url(self, client):
        """Test that file list includes syft_url when syft_core is enabled."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_response.status_code == 201

        # List files
        list_response = client.get(f"{settings.API_PREFIX}/files/")
        assert list_response.status_code == 200

        data = list_response.json()
        assert len(data["files"]) == 1
        file_item = data["files"][0]
        assert "syft_url" in file_item
        assert file_item["syft_url"] is not None
        assert file_item["syft_url"].startswith("syft://")

    def test_update_returns_syft_url(self, client):
        """Test that update response includes syft_url when syft_core is enabled."""
        # Upload original file
        files = {"file": ("original.txt", b"Original content", "text/plain")}
        upload_response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_response.status_code == 201
        file_id = upload_response.json()["id"]

        # Update file
        new_files = {"file": ("updated.txt", b"Updated content", "text/plain")}
        update_response = client.put(
            f"{settings.API_PREFIX}/files/{file_id}", files=new_files
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert "syft_url" in data
        assert data["syft_url"] is not None
        assert "updated.txt" in data["syft_url"]

    def test_internal_server_error_upload(self, client, monkeypatch):
        """Test 500 error handling during upload."""

        def mock_save_file(*args, **kwargs):
            raise Exception("Unexpected database error")

        monkeypatch.setattr(
            "app.services.file_service.FileService.save_file", mock_save_file
        )

        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_internal_server_error_list(self, client, monkeypatch):
        """Test 500 error handling during file listing."""

        def mock_list_files(*args, **kwargs):
            raise Exception("Database connection failed")

        monkeypatch.setattr(
            "app.services.file_service.FileService.list_files", mock_list_files
        )

        response = client.get(f"{settings.API_PREFIX}/files/")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_internal_server_error_download(self, client, monkeypatch):
        """Test 500 error handling during download."""

        def mock_get_file(*args, **kwargs):
            raise Exception("File system error")

        monkeypatch.setattr(
            "app.services.file_service.FileService.get_file", mock_get_file
        )

        response = client.get(f"{settings.API_PREFIX}/files/test-id")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_internal_server_error_update(self, client, monkeypatch):
        """Test 500 error handling during update."""

        def mock_update_file(*args, **kwargs):
            raise Exception("Permission denied")

        monkeypatch.setattr(
            "app.services.file_service.FileService.update_file", mock_update_file
        )

        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = client.put(f"{settings.API_PREFIX}/files/test-id", files=files)

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_internal_server_error_delete(self, client, monkeypatch):
        """Test 500 error handling during deletion."""

        def mock_delete_file(*args, **kwargs):
            raise Exception("File locked")

        monkeypatch.setattr(
            "app.services.file_service.FileService.delete_file", mock_delete_file
        )

        response = client.delete(f"{settings.API_PREFIX}/files/test-id")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_internal_server_error_stats(self, client, monkeypatch):
        """Test 500 error handling for storage stats."""

        def mock_get_stats(*args, **kwargs):
            raise Exception("Stats calculation failed")

        monkeypatch.setattr(
            "app.services.file_service.FileService.get_storage_stats", mock_get_stats
        )

        response = client.get(f"{settings.API_PREFIX}/files/stats/summary")

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
