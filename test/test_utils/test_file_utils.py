import hashlib

import pytest

from app.utils.file_utils import (
    calculate_file_hash,
    ensure_directory_exists,
    generate_storage_filename,
    parse_storage_filename,
    sanitize_filename,
    validate_file_size,
    validate_file_type,
)


class TestFileUtils:
    """Test file utility functions."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("test.txt") == "test.txt"
        assert (
            sanitize_filename("my file.txt") == "my-file.txt"
        )  # Spaces become hyphens
        assert sanitize_filename("file-name.txt") == "file-name.txt"
        assert sanitize_filename("file_name.txt") == "file_name.txt"

    def test_sanitize_filename_dangerous(self):
        """Test sanitization of dangerous filenames."""
        # Path traversal attempts
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert (
            sanitize_filename("..\\..\\windows\\system32\\config")
            == "windowssystem32config"
        )
        assert sanitize_filename("./../../secret.txt") == "secret.txt"

        # Special characters
        assert sanitize_filename("file<script>.txt") == "filescript.txt"
        assert sanitize_filename("file|pipe.txt") == "filepipe.txt"
        assert sanitize_filename("file:colon.txt") == "filecolon.txt"
        assert sanitize_filename("file*star.txt") == "filestar.txt"
        assert sanitize_filename("file?question.txt") == "filequestion.txt"
        assert sanitize_filename('file"quote.txt') == "filequote.txt"
        assert sanitize_filename("file>greater.txt") == "filegreater.txt"
        assert sanitize_filename("file<less.txt") == "fileless.txt"

    def test_sanitize_filename_unicode(self):
        """Test sanitization with unicode characters."""
        # Non-ASCII characters are removed, then leading dot is stripped
        assert sanitize_filename("файл.txt") == "txt"  # Cyrillic removed, dot stripped
        assert sanitize_filename("文件.txt") == "txt"  # Chinese removed, dot stripped
        assert sanitize_filename("ملف.txt") == "txt"  # Arabic removed, dot stripped

        # Mixed unicode and special chars - unicode is removed
        assert sanitize_filename("файл<script>.txt") == "script.txt"
        assert sanitize_filename("文件|pipe.txt") == "pipe.txt"

    def test_validate_file_type_valid(self, monkeypatch):
        """Test validation of allowed file types."""
        # Mock settings
        monkeypatch.setattr(
            "app.config.settings.ALLOWED_MIME_TYPES",
            {"text/plain", "image/jpeg", "application/pdf"},
        )
        monkeypatch.setattr(
            "app.config.settings.ALLOWED_EXTENSIONS", {".txt", ".jpg", ".jpeg", ".pdf"}
        )

        assert validate_file_type("text/plain", "test.txt") is True
        assert validate_file_type("image/jpeg", "image.jpg") is True
        assert validate_file_type("image/jpeg", "photo.jpeg") is True
        assert validate_file_type("application/pdf", "document.pdf") is True

    def test_validate_file_type_invalid(self, monkeypatch):
        """Test file type validation with invalid types."""
        from app.utils.file_utils import validate_file_type

        # Patch where settings is used in file_utils
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_MIME_TYPES", {"image/jpeg"}
        )
        monkeypatch.setattr(
            "app.utils.file_utils.settings.ALLOWED_EXTENSIONS", {".jpg"}
        )

        # These should be invalid (both MIME and extension must match)
        assert validate_file_type("text/plain", "document.txt") is False
        assert validate_file_type("text/html", "script.html") is False
        assert validate_file_type("application/pdf", "document.pdf") is False

        # This should be valid
        assert validate_file_type("image/jpeg", "photo.jpg") is True

    def test_validate_file_size_valid(self, monkeypatch):
        """Test file size validation within limits."""
        monkeypatch.setattr(
            "app.config.settings.MAX_FILE_SIZE", 10 * 1024 * 1024
        )  # 10MB

        assert validate_file_size(1) is True  # Minimum valid size
        assert validate_file_size(1024) is True  # 1KB
        assert validate_file_size(1024 * 1024) is True  # 1MB
        assert validate_file_size(10 * 1024 * 1024) is True  # Exactly 10MB

    def test_validate_file_size_invalid(self, monkeypatch):
        """Test file size validation exceeding limits."""
        monkeypatch.setattr(
            "app.config.settings.MAX_FILE_SIZE", 10 * 1024 * 1024
        )  # 10MB

        assert validate_file_size(0) is False  # Zero size is invalid
        assert validate_file_size(10 * 1024 * 1024 + 1) is False  # 10MB + 1 byte
        assert validate_file_size(20 * 1024 * 1024) is False  # 20MB
        assert validate_file_size(-1) is False  # Negative size

    def test_generate_storage_filename(self):
        """Test storage filename generation."""
        file_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        filename = "test.txt"

        result = generate_storage_filename(file_id, filename)
        assert result == f"{file_id}_{filename}"

        # Test with special characters (already sanitized)
        result = generate_storage_filename(file_id, "my file.txt")
        assert result == f"{file_id}_my file.txt"

    def test_parse_storage_filename_valid(self):
        """Test parsing valid storage filenames."""
        # Standard format
        file_id, filename = parse_storage_filename("uuid123_test.txt")
        assert file_id == "uuid123"
        assert filename == "test.txt"

        # UUID format
        file_id, filename = parse_storage_filename(
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890_document.pdf"
        )
        assert file_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert filename == "document.pdf"

        # Multiple underscores in filename
        file_id, filename = parse_storage_filename("id123_my_special_file.txt")
        assert file_id == "id123"
        assert filename == "my_special_file.txt"

    def test_parse_storage_filename_invalid(self):
        """Test parsing invalid storage filenames."""
        # No underscore
        file_id, filename = parse_storage_filename("justfilename.txt")
        assert file_id == ""
        assert filename == "justfilename.txt"

        # Empty string
        file_id, filename = parse_storage_filename("")
        assert file_id == ""
        assert filename == ""

        # Only underscore
        file_id, filename = parse_storage_filename("_")
        assert file_id == ""
        assert filename == ""

    def test_ensure_directory_exists(self, tmp_path):
        """Test directory creation."""
        # Test creating new directory
        new_dir = tmp_path / "new" / "nested" / "directory"
        assert not new_dir.exists()

        ensure_directory_exists(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

        # Test with existing directory (should not raise)
        ensure_directory_exists(new_dir)
        assert new_dir.exists()

    def test_calculate_file_hash(self, tmp_path):
        """Test file hash calculation."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World! This is a test file."
        test_file.write_bytes(test_content)

        # Calculate hash
        hash_result = calculate_file_hash(test_file)

        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

        # Verify consistency
        assert hash_result == calculate_file_hash(test_file)

        # Verify against known hash
        expected_hash = hashlib.sha256(test_content).hexdigest()
        assert hash_result == expected_hash

    def test_calculate_file_hash_different_files(self, tmp_path):
        """Test that different files produce different hashes."""
        # Create two different files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_bytes(b"Content 1")
        file2.write_bytes(b"Content 2")

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        assert hash1 != hash2

    def test_calculate_file_hash_large_file(self, tmp_path):
        """Test hash calculation for large files."""
        # Create a large file (10MB)
        large_file = tmp_path / "large.bin"
        large_content = b"x" * (10 * 1024 * 1024)
        large_file.write_bytes(large_content)

        # Should handle large files efficiently (chunks)
        hash_result = calculate_file_hash(large_file)

        assert len(hash_result) == 64
        expected_hash = hashlib.sha256(large_content).hexdigest()
        assert hash_result == expected_hash

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("", "unnamed"),  # Empty string returns "unnamed"
            ("   test.txt   ", "test.txt"),  # Whitespace is stripped
            ("TEST.TXT", "TEST.TXT"),  # Case preservation
            (".hidden", "hidden"),  # Leading dots are stripped
            ("no_extension", "no_extension"),  # No extension
            ("multiple.dots.txt", "multiple.dots.txt"),  # Multiple dots
            ("café.txt", "cafe.txt"),  # Accented characters are normalized
            (
                "//double//slashes.txt",
                "slashes.txt",
            ),  # Path components removed by basename
        ],
    )
    def test_sanitize_filename_edge_cases(self, filename, expected):
        """Test edge cases for filename sanitization."""
        assert sanitize_filename(filename) == expected
