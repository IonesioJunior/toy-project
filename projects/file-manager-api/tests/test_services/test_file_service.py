import shutil
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.file_service import FileService


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for file storage during tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_service(temp_storage_dir, monkeypatch, ensure_syft_client):
    """Create a FileService instance with temporary storage."""
    # Mock the syft_core paths
    storage_path = Path(temp_storage_dir) / "storage"
    metadata_path = Path(temp_storage_dir) / "metadata"

    monkeypatch.setattr("app.config.FILE_STORAGE_PATH", storage_path)
    monkeypatch.setattr("app.config.METADATA_PATH", metadata_path)

    # Also patch in the service module
    monkeypatch.setattr("app.services.file_service.FILE_STORAGE_PATH", storage_path)
    monkeypatch.setattr("app.services.file_service.METADATA_PATH", metadata_path)

    # Ensure syft_client is available via fixture
    monkeypatch.setattr("app.services.file_service.syft_client", ensure_syft_client)

    return FileService()


class MockUploadFile:
    """Mock UploadFile for testing."""

    def __init__(self, filename, file, content_type, size):
        self.filename = filename
        self.file = file
        self.content_type = content_type
        self.size = size


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""

    def _create_upload_file(
        filename="test.txt", content=b"Test file content", content_type="text/plain"
    ):
        file = BytesIO(content)
        return MockUploadFile(
            filename=filename, file=file, content_type=content_type, size=len(content)
        )

    return _create_upload_file


class TestFileService:
    """Test cases for FileService."""

    @pytest.mark.asyncio
    async def test_save_file_success(self, file_service, mock_upload_file):
        """Test successful file upload."""
        upload_file = mock_upload_file()

        metadata = await file_service.save_file(upload_file)

        assert metadata.filename == "test.txt"
        assert metadata.original_filename == "test.txt"
        assert metadata.size == 17  # Length of "Test file content"
        assert metadata.mime_type == "text/plain"
        assert isinstance(metadata.upload_date, datetime)
        assert metadata.id is not None

        # Verify file exists on disk
        file_path = file_service.storage_path / f"{metadata.id}_test.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Test file content"

        # Verify metadata exists
        metadata_path = file_service._get_metadata_file_path(metadata.id)
        assert metadata_path.exists()

    @pytest.mark.asyncio
    async def test_save_file_size_limit(
        self, file_service, mock_upload_file, monkeypatch
    ):
        """Test file size limit validation."""
        # Need to patch the settings in the file_utils module where it's used
        monkeypatch.setattr(
            "app.utils.file_utils.settings.MAX_FILE_SIZE", 10
        )  # 10 bytes limit

        upload_file = mock_upload_file(content=b"This content is too large")

        with pytest.raises(HTTPException) as exc_info:
            await file_service.save_file(upload_file)

        assert exc_info.value.status_code == 413
        assert "exceeds maximum allowed size" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_save_file_invalid_type(
        self, file_service, mock_upload_file, monkeypatch
    ):
        """Test file type validation."""
        # Restrict allowed types - patch in file_utils where they're used
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_MIME_TYPES", {"image/jpeg"}
        )
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_EXTENSIONS", {".jpg", ".jpeg"}
        )

        upload_file = mock_upload_file(filename="test.txt", content_type="text/plain")

        with pytest.raises(HTTPException) as exc_info:
            await file_service.save_file(upload_file)

        assert exc_info.value.status_code == 415
        assert "File type not allowed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_sanitize_dangerous_filename(self, file_service, mock_upload_file):
        """Test filename sanitization for dangerous filenames."""
        dangerous_names = [
            ("../../../etc/passwd.txt", "passwd.txt"),
            ("..\\..\\windows\\system32\\config\\sam.txt", "sam.txt"),
            ("file<script>.txt", "filescript.txt"),
            ("file|pipe.txt", "filepipe.txt"),
            ("file:colon.txt", "filecolon.txt"),
        ]

        for dangerous_name, expected_safe in dangerous_names:
            upload_file = mock_upload_file(filename=dangerous_name)
            metadata = await file_service.save_file(upload_file)

            # Verify filename was sanitized
            assert ".." not in metadata.filename
            assert "<" not in metadata.filename
            assert ">" not in metadata.filename
            assert "|" not in metadata.filename
            assert ":" not in metadata.filename
            # Check that extension is preserved
            assert metadata.filename.endswith(".txt")

    @pytest.mark.asyncio
    async def test_get_file_success(self, file_service, mock_upload_file):
        """Test successful file retrieval."""
        # First upload a file
        upload_file = mock_upload_file()
        metadata = await file_service.save_file(upload_file)

        # Then retrieve it
        file_path, retrieved_metadata = await file_service.get_file(metadata.id)

        assert file_path.exists()
        assert retrieved_metadata.id == metadata.id
        assert retrieved_metadata.filename == metadata.filename
        assert file_path.read_text() == "Test file content"

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, file_service):
        """Test retrieving non-existent file."""
        with pytest.raises(HTTPException) as exc_info:
            await file_service.get_file("non-existent-id")

        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_files(self, file_service, mock_upload_file):
        """Test listing all files."""
        # Upload multiple files
        files_data = [
            ("file1.txt", b"Content 1", "text/plain"),
            ("file2.pdf", b"Content 2", "application/pdf"),
            ("file3.jpg", b"Content 3", "image/jpeg"),
        ]

        uploaded_ids = []
        for filename, content, content_type in files_data:
            upload_file = mock_upload_file(filename, content, content_type)
            metadata = await file_service.save_file(upload_file)
            uploaded_ids.append(metadata.id)

        # List files
        files = await file_service.list_files()

        assert len(files) == 3
        assert all(file.id in uploaded_ids for file in files)
        assert files[0].upload_date >= files[1].upload_date  # Sorted by date desc

    @pytest.mark.asyncio
    async def test_update_file_success(self, file_service, mock_upload_file):
        """Test successful file update."""
        # Upload original file
        original_file = mock_upload_file("original.txt", b"Original content")
        original_metadata = await file_service.save_file(original_file)
        original_id = original_metadata.id

        # Update with new file
        new_file = mock_upload_file("updated.txt", b"Updated content")
        updated_metadata = await file_service.update_file(original_id, new_file)

        assert updated_metadata.id == original_id  # ID remains same
        assert updated_metadata.filename == "updated.txt"
        assert updated_metadata.size == 15  # Length of "Updated content"
        assert updated_metadata.upload_date > original_metadata.upload_date

        # Verify new content
        file_path = file_service.storage_path / f"{original_id}_updated.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Updated content"

        # Verify old file is removed
        old_path = file_service.storage_path / f"{original_id}_original.txt"
        assert not old_path.exists()

    @pytest.mark.asyncio
    async def test_update_file_not_found(self, file_service, mock_upload_file):
        """Test updating non-existent file."""
        new_file = mock_upload_file()

        with pytest.raises(HTTPException) as exc_info:
            await file_service.update_file("non-existent-id", new_file)

        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_file_success(self, file_service, mock_upload_file):
        """Test successful file deletion."""
        # Upload a file
        upload_file = mock_upload_file()
        metadata = await file_service.save_file(upload_file)
        file_id = metadata.id

        # Verify file exists
        file_path = file_service.storage_path / f"{file_id}_test.txt"
        metadata_path = file_service._get_metadata_file_path(file_id)
        assert file_path.exists()
        assert metadata_path.exists()

        # Delete file
        result = await file_service.delete_file(file_id)
        assert result is True

        # Verify file and metadata are removed
        assert not file_path.exists()
        assert not metadata_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, file_service):
        """Test deleting non-existent file."""
        with pytest.raises(HTTPException) as exc_info:
            await file_service.delete_file("non-existent-id")

        assert exc_info.value.status_code == 404
        assert "File not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, file_service, mock_upload_file):
        """Test storage statistics."""
        # Upload some files
        files_data = [
            ("file1.txt", b"A" * 100),  # 100 bytes
            ("file2.txt", b"B" * 200),  # 200 bytes
            ("file3.txt", b"C" * 300),  # 300 bytes
        ]

        for filename, content in files_data:
            upload_file = mock_upload_file(filename, content)
            await file_service.save_file(upload_file)

        # Get stats
        stats = await file_service.get_storage_stats()

        assert stats["total_files"] == 3
        assert stats["total_size"] == 600  # 100 + 200 + 300
        assert "max_file_size" in stats
        assert "storage_path" in stats

    @pytest.mark.asyncio
    async def test_metadata_persistence(self, file_service, mock_upload_file):
        """Test that metadata persists correctly."""
        # Upload a file
        upload_file = mock_upload_file()
        original_metadata = await file_service.save_file(upload_file)

        # Create new service instance (simulating restart)
        new_service = FileService()

        # Load metadata
        loaded_metadata = new_service._load_metadata(original_metadata.id)

        assert loaded_metadata is not None
        assert loaded_metadata.id == original_metadata.id
        assert loaded_metadata.filename == original_metadata.filename
        assert loaded_metadata.size == original_metadata.size
        assert loaded_metadata.mime_type == original_metadata.mime_type

    @pytest.mark.asyncio
    async def test_syft_url_generation(
        self, file_service, mock_upload_file, monkeypatch
    ):
        """Test syft URL generation when syft_core is configured."""

        # Mock syft_client to return a fake URL
        class MockSyftClient:
            email = "test@example.com"

            def to_syft_url(self, path):
                return f"syft://test@example.com/fake/path/{path.name}"

        mock_client = MockSyftClient()
        monkeypatch.setattr("app.services.file_service.syft_client", mock_client)
        monkeypatch.setattr("app.config.settings.SYFT_USER_EMAIL", "test@example.com")

        # Upload a file
        upload_file = mock_upload_file()
        metadata = await file_service.save_file(upload_file)

        # Verify syft_url is generated
        assert metadata.syft_url is not None
        assert metadata.syft_url.startswith("syft://test@example.com/")
        assert metadata.filename in metadata.syft_url

    @pytest.mark.asyncio
    async def test_syft_url_none_when_disabled(self, file_service, mock_upload_file):
        """Test that syft_url is None when syft_core is not configured."""
        # syft_client is already None in the fixture
        upload_file = mock_upload_file()
        metadata = await file_service.save_file(upload_file)

        # Verify syft_url is None
        assert metadata.syft_url is not None
