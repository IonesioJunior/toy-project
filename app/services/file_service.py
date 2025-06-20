import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile

from app.config import FILE_STORAGE_PATH, METADATA_PATH, settings, syft_client
from app.models.file import FileListItem, FileMetadata
from app.utils.file_utils import (
    ensure_directory_exists,
    generate_storage_filename,
    sanitize_filename,
    validate_file_size,
    validate_file_type,
)


class FileService:
    def __init__(self) -> None:
        if not syft_client:
            raise RuntimeError("FileService requires syft_core to be initialized")

        self.storage_path = FILE_STORAGE_PATH
        ensure_directory_exists(self.storage_path)
        self.metadata_path = METADATA_PATH
        ensure_directory_exists(self.metadata_path)

    def _get_metadata_file_path(self, file_id: str) -> Path:
        """Get the path to a file's metadata JSON file."""
        return self.metadata_path / f"{file_id}.json"

    def _save_metadata(self, metadata: FileMetadata) -> None:
        """Save file metadata to JSON file."""
        metadata_file = self._get_metadata_file_path(metadata.id)
        with open(metadata_file, "w") as f:
            json.dump(metadata.model_dump(), f, default=str)

    def _load_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Load file metadata from JSON file."""
        metadata_file = self._get_metadata_file_path(file_id)
        if not metadata_file.exists():
            return None

        with open(metadata_file, "r") as f:
            data = json.load(f)
            # Convert datetime strings back to datetime objects
            if "upload_date" in data:
                data["upload_date"] = datetime.fromisoformat(data["upload_date"])
            return FileMetadata(**data)

    def _delete_metadata(self, file_id: str) -> None:
        """Delete file metadata JSON file."""
        metadata_file = self._get_metadata_file_path(file_id)
        if metadata_file.exists():
            metadata_file.unlink()

    def _generate_syft_url(self, file_path: Path) -> str:
        """Generate syft:// URL for a file. Raises error if syft_core not configured."""
        if not settings.SYFT_USER_EMAIL or not syft_client:
            raise RuntimeError("syft_core not properly initialized")

        try:
            syft_url = syft_client.to_syft_url(file_path)
            return str(syft_url)
        except Exception as e:
            raise RuntimeError(f"Failed to generate syft URL: {e}")

    async def save_file(self, file: UploadFile) -> FileMetadata:
        """
        Save an uploaded file to storage.

        Args:
            file: The uploaded file

        Returns:
            FileMetadata object with file information

        Raises:
            HTTPException: If file validation fails or save operation fails
        """
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        # Validate file size
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes",
            )

        # Validate file type
        if (
            not file.content_type
            or not file.filename
            or not validate_file_type(file.content_type, file.filename)
        ):
            raise HTTPException(status_code=415, detail="File type not allowed")

        # Sanitize filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        safe_filename = sanitize_filename(file.filename)

        # Generate storage filename first to get the file path
        file_id = str(uuid.uuid4())
        storage_filename = generate_storage_filename(file_id, safe_filename)
        file_path = self.storage_path / storage_filename

        # Generate syft URL
        syft_url = self._generate_syft_url(file_path)

        # Create metadata with syft URL
        metadata = FileMetadata(
            id=file_id,
            filename=safe_filename,
            original_filename=file.filename or safe_filename,
            size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            syft_url=syft_url,
        )

        try:
            # Save file to disk
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Save metadata
            self._save_metadata(metadata)

        except IOError:
            # Clean up on failure
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500, detail="Failed to save file to storage"
            )

        return metadata

    async def get_file(self, file_id: str) -> tuple[Path, FileMetadata]:
        """
        Get a file and its metadata by ID.

        Args:
            file_id: The file ID

        Returns:
            Tuple of (file_path, metadata)

        Raises:
            HTTPException: If file not found
        """
        # Load metadata
        metadata = self._load_metadata(file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")

        # Find the file
        storage_filename = generate_storage_filename(metadata.id, metadata.filename)
        file_path = self.storage_path / storage_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found in storage")

        return file_path, metadata

    async def list_files(self) -> List[FileListItem]:
        """
        List all files in storage.

        Returns:
            List of FileListItem objects
        """
        files = []

        # Iterate through all metadata files
        for metadata_file in self.metadata_path.glob("*.json"):
            file_id = metadata_file.stem
            metadata = self._load_metadata(file_id)

            if metadata:
                # Verify file still exists
                storage_filename = generate_storage_filename(
                    metadata.id, metadata.filename
                )
                file_path = self.storage_path / storage_filename

                if file_path.exists():
                    # Generate syft URL for the file
                    syft_url = self._generate_syft_url(file_path)

                    files.append(
                        FileListItem(
                            id=metadata.id,
                            filename=metadata.filename,
                            size=metadata.size,
                            mime_type=metadata.mime_type,
                            upload_date=metadata.upload_date,
                            syft_url=syft_url,
                            is_owner=None,
                            shared_with=None,
                        )
                    )
                else:
                    # Clean up orphaned metadata
                    self._delete_metadata(file_id)

        # Sort by upload date (newest first)
        files.sort(key=lambda x: x.upload_date, reverse=True)

        return files

    async def update_file(self, file_id: str, new_file: UploadFile) -> FileMetadata:
        """
        Update an existing file with a new version.

        Args:
            file_id: The file ID to update
            new_file: The new file to replace with

        Returns:
            Updated FileMetadata

        Raises:
            HTTPException: If file not found or validation fails
        """
        # Check if file exists
        old_metadata = self._load_metadata(file_id)
        if not old_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        # Get new file size
        new_file.file.seek(0, 2)
        file_size = new_file.file.tell()
        new_file.file.seek(0)

        # Validate new file
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes",
            )

        if (
            not new_file.content_type
            or not new_file.filename
            or not validate_file_type(new_file.content_type, new_file.filename)
        ):
            raise HTTPException(status_code=415, detail="File type not allowed")

        # Sanitize new filename
        if not new_file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        safe_filename = sanitize_filename(new_file.filename)

        # Remove old file
        old_storage_filename = generate_storage_filename(
            old_metadata.id, old_metadata.filename
        )
        old_file_path = self.storage_path / old_storage_filename

        # Generate new storage filename
        new_storage_filename = generate_storage_filename(file_id, safe_filename)
        new_file_path = self.storage_path / new_storage_filename

        # Generate syft URL for the new file
        syft_url = self._generate_syft_url(new_file_path)

        # Create new metadata (keeping same ID)
        new_metadata = FileMetadata(
            id=file_id,  # Keep same ID
            filename=safe_filename,
            original_filename=new_file.filename or safe_filename,
            size=file_size,
            mime_type=new_file.content_type or "application/octet-stream",
            upload_date=datetime.now(timezone.utc),  # Update timestamp
            syft_url=syft_url,
        )

        try:
            # Save new file
            with open(new_file_path, "wb") as buffer:
                shutil.copyfileobj(new_file.file, buffer)

            # Remove old file if it exists and is different
            if old_file_path.exists() and old_file_path != new_file_path:
                old_file_path.unlink()

            # Update metadata
            self._save_metadata(new_metadata)

        except IOError:
            # Clean up on failure
            if new_file_path.exists() and new_file_path != old_file_path:
                new_file_path.unlink()
            raise HTTPException(status_code=500, detail="Failed to update file")

        return new_metadata

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file and its metadata.

        Args:
            file_id: The file ID to delete

        Returns:
            True if file was deleted

        Raises:
            HTTPException: If file not found
        """
        # Load metadata
        metadata = self._load_metadata(file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete file
        storage_filename = generate_storage_filename(metadata.id, metadata.filename)
        file_path = self.storage_path / storage_filename

        try:
            if file_path.exists():
                file_path.unlink()

            # Delete metadata
            self._delete_metadata(file_id)

        except IOError:
            raise HTTPException(status_code=500, detail="Failed to delete file")

        return True

    async def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        total_files = 0
        total_size = 0

        for metadata_file in self.metadata_path.glob("*.json"):
            metadata = self._load_metadata(metadata_file.stem)
            if metadata:
                total_files += 1
                total_size += metadata.size

        return {
            "total_files": total_files,
            "total_size": total_size,
            "max_file_size": settings.MAX_FILE_SIZE,
            "storage_path": str(self.storage_path),
        }
