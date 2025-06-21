"""Client service for interacting with the File Manager API."""

import logging
from typing import Any, Dict, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class FileManagerError(Exception):
    """Exception for file manager related errors"""

    pass


class FileManagerClient:
    """Client for interacting with the File Manager API."""

    def __init__(self) -> None:
        self.base_url = settings.file_manager_api_url
        self.timeout = httpx.Timeout(30.0)  # 30 second timeout
        self._is_available: Optional[bool] = None  # Cache availability status

    async def check_availability(self) -> bool:
        """Check if the file manager service is available."""
        if self._is_available is not None:
            return self._is_available

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                is_available = response.status_code == 200
                self._is_available = is_available
                return is_available
        except Exception as e:
            logger.warning(f"File manager service not available: {str(e)}")
            self._is_available = False
            return False

    async def upload_document_file(
        self, content: str, filename: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a document to the file manager.

        Args:
            content: The document content
            filename: The filename to use
            metadata: Optional metadata to attach to the file

        Returns:
            Dict with file info including id and syft_url, or None if failed
        """
        if not await self.check_availability():
            logger.warning("File manager not available, skipping file upload")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare file data
                files = {"file": (filename, content.encode("utf-8"), "text/plain")}

                # Add metadata to form data if provided
                data = {}
                if metadata:
                    # File manager expects metadata as individual form fields
                    for key, value in metadata.items():
                        if key not in ["created_at", "updated_at", "file_manager_id"]:
                            data[f"metadata_{key}"] = str(value)

                response = await client.post(
                    f"{self.base_url}/api/files/", files=files, data=data
                )
                response.raise_for_status()

                result: Dict[str, Any] = response.json()
                logger.info(
                    f"Successfully uploaded document to file manager: {result['id']}"
                )
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error uploading to file manager: {e.response.status_code}"
            )
            raise FileManagerError(f"Failed to upload document: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error uploading to file manager: {str(e)}")
            raise FileManagerError(f"Unexpected error during upload: {str(e)}")

    async def delete_document_file(self, file_id: str) -> bool:
        """
        Delete a document from the file manager.

        Args:
            file_id: The UUID of the file to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not file_id:
            logger.warning("No file_id provided for deletion")
            return True

        if not await self.check_availability():
            logger.warning("File manager not available, skipping file deletion")
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(f"{self.base_url}/api/files/{file_id}")
                response.raise_for_status()

                logger.info(f"Successfully deleted file from file manager: {file_id}")
                return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found in file manager: {file_id}")
                return False  # Return False when file not found

            logger.error(
                f"HTTP error deleting from file manager: {e.response.status_code}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from file manager: {str(e)}")
            return False

    async def get_document_file(self, file_id: str) -> Optional[str]:
        """
        Retrieve a document's content from the file manager.

        Args:
            file_id: The UUID of the file

        Returns:
            The file content as a string, or None if failed
        """
        if not file_id:
            logger.warning("No file_id provided for retrieval")
            return None

        if not await self.check_availability():
            logger.warning("File manager not available")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/files/{file_id}")
                response.raise_for_status()

                content = response.text
                logger.info(f"Successfully retrieved file from file manager: {file_id}")
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found in file manager: {file_id}")
            else:
                logger.error(
                    f"HTTP error retrieving from file manager: {e.response.status_code}"
                )
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving from file manager: {str(e)}")
            return None

    async def update_document_file(
        self, file_id: str, content: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing document in the file manager.

        Args:
            file_id: The UUID of the file to update
            content: The new document content
            filename: The new filename

        Returns:
            Dict with updated file info, or None if failed
        """
        if not file_id:
            logger.warning("No file_id provided for update")
            return None

        if not await self.check_availability():
            logger.warning("File manager not available, skipping file update")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                files = {"file": (filename, content.encode("utf-8"), "text/plain")}

                response = await client.put(
                    f"{self.base_url}/api/files/{file_id}", files=files
                )
                response.raise_for_status()

                result: Dict[str, Any] = response.json()
                logger.info(f"Successfully updated document in file manager: {file_id}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating file manager: {e.response.status_code}")
            raise FileManagerError(f"Failed to update document: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error updating file manager: {str(e)}")
            raise FileManagerError(f"Unexpected error during update: {str(e)}")


# Global instance
file_manager_client = FileManagerClient()
