"""Client service for interacting with the File Manager API."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class FileInfo(BaseModel):
    """File information from the file manager."""

    id: str
    filename: str
    size: int
    mime_type: str
    upload_date: datetime
    syft_url: Optional[str] = None


class FileManagerClient:
    """Client for interacting with the File Manager API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.file_manager_api_url
        self.timeout = httpx.Timeout(30.0)  # 30 second timeout

    async def get_files(self) -> List[FileInfo]:
        """
        Fetch list of available files from the file manager.

        Returns:
            List of FileInfo objects

        Raises:
            ExternalServiceError: If the request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/files/")
                response.raise_for_status()

                data = response.json()
                files = []

                for file_data in data.get("files", []):
                    # Convert ISO datetime string to datetime object
                    if isinstance(file_data.get("upload_date"), str):
                        file_data["upload_date"] = datetime.fromisoformat(
                            file_data["upload_date"].replace("Z", "+00:00")
                        )

                    files.append(FileInfo(**file_data))

                logger.info(f"Retrieved {len(files)} files from file manager")
                return files

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from file manager: {e.response.status_code}")
            raise ExternalServiceError(
                f"File manager returned error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error to file manager: {str(e)}")
            # Return empty list if file manager is not available
            logger.warning("File manager service not available, returning empty list")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching files: {str(e)}")
            raise ExternalServiceError("Unexpected error while fetching files")

    async def get_file_content(self, file_id: str) -> str:
        """
        Retrieve the content of a specific file.

        Args:
            file_id: The UUID of the file

        Returns:
            The file content as a string

        Raises:
            ExternalServiceError: If the request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/files/{file_id}")
                response.raise_for_status()

                # Read the content as text
                content = response.text

                logger.info(
                    f"Retrieved content for file {file_id}, size: {len(content)} chars"
                )
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"File not found: {file_id}")
                raise ExternalServiceError(f"File {file_id} not found")

            logger.error(f"HTTP error from file manager: {e.response.status_code}")
            raise ExternalServiceError(
                f"File manager returned error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error to file manager: {str(e)}")
            raise ExternalServiceError("Unable to connect to file manager service")
        except Exception as e:
            logger.error(f"Unexpected error fetching file content: {str(e)}")
            raise ExternalServiceError("Unexpected error while fetching file content")

    async def get_multiple_files_content(self, file_ids: List[str]) -> Dict[str, str]:
        """
        Retrieve content for multiple files.

        Args:
            file_ids: List of file UUIDs

        Returns:
            Dictionary mapping file_id to content

        Note:
            Failed retrievals are logged but don't stop the process
        """
        contents = {}

        for file_id in file_ids:
            try:
                content = await self.get_file_content(file_id)
                contents[file_id] = content
            except ExternalServiceError as e:
                logger.warning(f"Failed to retrieve file {file_id}: {str(e)}")
                # Continue with other files

        return contents

    async def health_check(self) -> bool:
        """
        Check if the file manager service is accessible.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"File manager health check failed: {str(e)}")
            return False


# Global instance
file_manager_client = FileManagerClient()
