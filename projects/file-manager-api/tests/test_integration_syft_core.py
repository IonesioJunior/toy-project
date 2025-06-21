import pytest

from app.config import settings


class TestSyftCoreIntegration:
    """Integration tests for syft_core workflows."""

    @pytest.mark.integration
    def test_complete_workflow_with_syft(self, client, mock_syft_client):
        """Test complete file management workflow with syft_core enabled."""
        # 1. Upload a file
        files = {"file": ("test.txt", b"Original content for testing", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        file_id = upload_data["id"]
        syft_url = upload_data["syft_url"]

        assert file_id is not None
        assert syft_url is not None
        assert syft_url.startswith("syft://test@example.com/")
        assert "test.txt" in syft_url

        # 2. List files and verify syft_url is included
        list_resp = client.get(f"{settings.API_PREFIX}/files/")
        assert list_resp.status_code == 200

        list_data = list_resp.json()
        assert list_data["total"] == 1
        files_list = list_data["files"]

        # Find our uploaded file
        uploaded_file = next((f for f in files_list if f["id"] == file_id), None)
        assert uploaded_file is not None
        assert uploaded_file["filename"] == "test.txt"
        assert uploaded_file["size"] == len(b"Original content for testing")
        assert uploaded_file["mime_type"] == "text/plain"
        assert uploaded_file["syft_url"] == syft_url

        # 3. Download the file
        download_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_resp.status_code == 200
        assert download_resp.content == b"Original content for testing"
        assert download_resp.headers["content-type"] == "text/plain; charset=utf-8"

        # 4. Update the file
        new_files = {"file": ("updated.txt", b"New content after update", "text/plain")}
        update_resp = client.put(
            f"{settings.API_PREFIX}/files/{file_id}", files=new_files
        )

        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["id"] == file_id  # ID should remain the same
        assert update_data["filename"] == "updated.txt"
        assert update_data["syft_url"] is not None
        assert "updated.txt" in update_data["syft_url"]

        # Verify content was updated
        download_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_resp.status_code == 200
        assert download_resp.content == b"New content after update"

        # 5. Get storage stats
        stats_resp = client.get(f"{settings.API_PREFIX}/files/stats/summary")
        assert stats_resp.status_code == 200

        stats_data = stats_resp.json()
        assert stats_data["total_files"] == 1
        assert stats_data["total_size"] == len(b"New content after update")
        assert "storage_path" in stats_data

        # 6. Delete the file
        delete_resp = client.delete(f"{settings.API_PREFIX}/files/{file_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["message"] == "File deleted successfully"

        # Verify deletion
        get_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert get_resp.status_code == 404

        # Verify file is removed from list
        list_resp = client.get(f"{settings.API_PREFIX}/files/")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 0
        assert list_resp.json()["files"] == []

    @pytest.mark.integration
    def test_complete_workflow_without_syft(self, client):
        """Test complete file management workflow with mock syft_core."""
        # In testing mode, we use MockSyftClient which always provides syft_url

        # 1. Upload a file
        files = {"file": ("test_no_syft.txt", b"Content without syft", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)

        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        file_id = upload_data["id"]

        assert file_id is not None
        assert upload_data.get("syft_url") is not None  # Always has syft_url now

        # 2. List files and verify syft_url is included
        list_resp = client.get(f"{settings.API_PREFIX}/files/")
        assert list_resp.status_code == 200

        list_data = list_resp.json()
        assert list_data["total"] == 1
        file_item = list_data["files"][0]
        assert file_item["syft_url"] is not None

        # 3. Download works normally
        download_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}")
        assert download_resp.status_code == 200
        assert download_resp.content == b"Content without syft"

        # 4. Update with syft_url
        new_files = {"file": ("updated_no_syft.txt", b"Updated no syft", "text/plain")}
        update_resp = client.put(
            f"{settings.API_PREFIX}/files/{file_id}", files=new_files
        )

        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["syft_url"] is not None  # Always has syft_url now

        # 5. Delete works normally
        delete_resp = client.delete(f"{settings.API_PREFIX}/files/{file_id}")
        assert delete_resp.status_code == 200

    @pytest.mark.integration
    def test_multiple_files_with_syft(self, client, mock_syft_client):
        """Test handling multiple files with syft_core enabled."""
        # Upload multiple files
        test_files = [
            ("doc1.txt", b"Document 1 content", "text/plain"),
            ("doc2.pdf", b"PDF content simulation", "application/pdf"),
            ("image.jpg", b"JPEG image data", "image/jpeg"),
        ]

        uploaded_ids = []
        uploaded_urls = []

        for filename, content, content_type in test_files:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201

            data = response.json()
            uploaded_ids.append(data["id"])
            uploaded_urls.append(data["syft_url"])

            # Verify each has a unique syft URL
            assert data["syft_url"] is not None
            assert filename in data["syft_url"]

        # Verify all syft URLs are unique
        assert len(set(uploaded_urls)) == len(uploaded_urls)

        # List all files
        list_resp = client.get(f"{settings.API_PREFIX}/files/")
        assert list_resp.status_code == 200

        list_data = list_resp.json()
        assert list_data["total"] == 3

        # Verify all files have syft URLs
        for file_item in list_data["files"]:
            assert file_item["syft_url"] is not None
            assert file_item["id"] in uploaded_ids

    @pytest.mark.integration
    def test_error_handling_with_syft(self, client, mock_syft_client):
        """Test error scenarios with syft_core enabled."""
        # Test invalid file type
        files = {
            "file": ("script.exe", b"Executable content", "application/x-executable")
        }
        response = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert response.status_code == 415

        # Test oversized file
        import app.utils.file_utils

        original_size = app.utils.file_utils.settings.MAX_FILE_SIZE
        app.utils.file_utils.settings.MAX_FILE_SIZE = 10  # Set to 10 bytes temporarily

        try:
            files = {"file": ("large.txt", b"This content is too large", "text/plain")}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 413
        finally:
            app.utils.file_utils.settings.MAX_FILE_SIZE = original_size

        # Test non-existent file operations
        fake_id = "non-existent-file-id"

        # Download non-existent
        response = client.get(f"{settings.API_PREFIX}/files/{fake_id}")
        assert response.status_code == 404

        # Update non-existent
        files = {"file": ("new.txt", b"New content", "text/plain")}
        response = client.put(f"{settings.API_PREFIX}/files/{fake_id}", files=files)
        assert response.status_code == 404

        # Delete non-existent
        response = client.delete(f"{settings.API_PREFIX}/files/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.integration
    def test_special_characters_with_syft(self, client, mock_syft_client):
        """Test handling files with special characters in names with syft_core."""
        special_files = [
            ("file with spaces.txt", "Spaces in filename"),
            # Skip non-ASCII filenames as they are stripped by sanitization
            # ("файл-кириллица.txt", "Cyrillic characters"),
            # ("文件-中文.txt", "Chinese characters"),
            ("file_underscore.txt", "Underscores"),
            ("file-dash.txt", "Dashes"),
        ]

        for filename, description in special_files:
            files = {
                "file": (filename, f"{description} content".encode(), "text/plain")
            }
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)

            assert response.status_code == 201, (
                f"Failed for {filename}: {response.json()}"
            )
            data = response.json()

            # Verify syft URL is generated
            assert data["syft_url"] is not None

            # Verify we can download the file
            file_id = data["id"]
            download_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}")
            if download_resp.status_code != 200:
                print(f"Download failed for {filename}: {download_resp.json()}")
            assert download_resp.status_code == 200

    @pytest.mark.integration
    def test_concurrent_operations_with_syft(self, client, mock_syft_client):
        """Test concurrent file operations with syft_core enabled."""
        import concurrent.futures

        def upload_file(index):
            files = {
                "file": (
                    f"concurrent_{index}.txt",
                    f"Concurrent content {index}".encode(),
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
        assert all(r.status_code == 201 for r in responses)

        # All should have unique syft URLs
        syft_urls = [r.json()["syft_url"] for r in responses]
        assert len(set(syft_urls)) == 10  # All unique
        assert all(url is not None for url in syft_urls)

        # Verify all files exist
        list_resp = client.get(f"{settings.API_PREFIX}/files/")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 10
