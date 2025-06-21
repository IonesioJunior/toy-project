"""File management endpoints for LLM Chat."""

import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.exceptions import ExternalServiceError
from src.services.file_manager_client import FileInfo, file_manager_client

router = APIRouter(prefix="/api/files", tags=["files"])
logger = logging.getLogger(__name__)


class FileContentRequest(BaseModel):
    """Request model for fetching multiple file contents."""

    file_ids: List[str]


class FileContentResponse(BaseModel):
    """Response model for file contents."""

    contents: Dict[str, str]
    failed_ids: List[str]


@router.get("/", response_model=List[FileInfo])
async def list_files() -> List[FileInfo]:
    """
    Get list of available files from the file manager.

    Returns:
        List of file information objects

    Raises:
        HTTPException: If file manager service is unavailable
    """
    try:
        files = await file_manager_client.get_files()
        return files

    except ExternalServiceError as e:
        logger.error(f"Failed to fetch files: {str(e)}")
        # Return empty list to allow UI to function when file manager is down
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching files: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Internal server error while fetching files"
        )


@router.get("/{file_id}/content")
async def get_file_content(file_id: str) -> Dict[str, str]:
    """
    Get content of a specific file.

    Args:
        file_id: UUID of the file

    Returns:
        Dictionary with file_id and content

    Raises:
        HTTPException: If file not found or service unavailable
    """
    try:
        content = await file_manager_client.get_file_content(file_id)
        return {"file_id": file_id, "content": content}

    except ExternalServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        logger.error(f"Failed to fetch file content: {str(e)}")
        raise HTTPException(
            status_code=503, detail="File manager service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching file content: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Internal server error while fetching file content"
        )


@router.post("/contents", response_model=FileContentResponse)
async def get_multiple_files_content(
    request: FileContentRequest,
) -> FileContentResponse:
    """
    Get content for multiple files.

    Args:
        request: Request containing list of file IDs

    Returns:
        Dictionary mapping file IDs to their contents, plus list of failed IDs

    Note:
        This endpoint will return partial results if some files fail to load
    """
    try:
        if not request.file_ids:
            return FileContentResponse(contents={}, failed_ids=[])

        # Limit number of files to prevent abuse
        if len(request.file_ids) > 10:
            raise HTTPException(
                status_code=400, detail="Maximum 10 files can be requested at once"
            )

        contents = await file_manager_client.get_multiple_files_content(
            request.file_ids
        )

        # Identify failed IDs
        failed_ids = [fid for fid in request.file_ids if fid not in contents]

        return FileContentResponse(contents=contents, failed_ids=failed_ids)

    except HTTPException:
        raise
    except ExternalServiceError as e:
        logger.error(f"Failed to fetch file contents: {str(e)}")
        raise HTTPException(
            status_code=503, detail="File manager service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching file contents: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Internal server error while fetching file contents"
        )


@router.get("/health")
async def check_file_manager_health() -> Dict[str, bool]:
    """Check if file manager service is accessible."""
    try:
        is_healthy = await file_manager_client.health_check()
        return {"file_manager_available": is_healthy}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"file_manager_available": False}
