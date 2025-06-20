import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple

from app.config import settings


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's safe for filesystem storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any path components to prevent path traversal
    filename = os.path.basename(filename)

    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename)

    # Remove non-ASCII characters
    filename = filename.encode("ASCII", "ignore").decode("ASCII")

    # Replace spaces and dangerous characters
    filename = re.sub(r"[^\w\s.-]", "", filename)
    filename = re.sub(r"[-\s]+", "-", filename)

    # Remove leading/trailing dots and hyphens
    filename = filename.strip(".-")

    # Split name and extension
    name, ext = os.path.splitext(filename)

    # Ensure filename is not empty
    if not name:
        name = "unnamed"

    # Limit filename length (keep extension)
    max_name_length = 100
    if len(name) > max_name_length:
        name = name[:max_name_length]

    # Reconstruct filename
    filename = name + ext

    return filename


def validate_file_type(mime_type: str, filename: str) -> bool:
    """
    Validate if a file type is allowed based on MIME type and extension.

    Args:
        mime_type: MIME type of the file
        filename: Name of the file

    Returns:
        True if file type is allowed, False otherwise
    """
    # Check MIME type
    if mime_type not in settings.ALLOWED_MIME_TYPES:
        return False

    # Check file extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False

    return True


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.

    Args:
        filename: Name of the file

    Returns:
        File extension (lowercase, including dot)
    """
    return os.path.splitext(filename)[1].lower()


def validate_file_size(size: int) -> bool:
    """
    Validate if file size is within allowed limits.

    Args:
        size: File size in bytes

    Returns:
        True if size is within limits, False otherwise
    """
    return 0 < size <= settings.MAX_FILE_SIZE


def generate_storage_filename(file_id: str, original_filename: str) -> str:
    """
    Generate a filename for storage that includes the file ID.

    Args:
        file_id: Unique file identifier
        original_filename: Original filename (already sanitized)

    Returns:
        Storage filename
    """
    return f"{file_id}_{original_filename}"


def parse_storage_filename(storage_filename: str) -> Tuple[str, str]:
    """
    Parse a storage filename to extract file ID and original filename.

    Args:
        storage_filename: Filename as stored on disk

    Returns:
        Tuple of (file_id, original_filename)
    """
    parts = storage_filename.split("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", storage_filename


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to directory
    """
    directory.mkdir(parents=True, exist_ok=True)


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file for integrity checking.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use

    Returns:
        Hex digest of the file hash
    """
    import hashlib

    hash_obj = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()
