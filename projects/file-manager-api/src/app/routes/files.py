import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.models.file import (
    ErrorResponse,
    FileDeleteResponse,
    FileListResponse,
    FileUpdateResponse,
    FileUploadResponse,
)
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


def get_file_service() -> FileService:
    """Dependency to get FileService instance."""
    return FileService()


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=201,
    responses={
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def upload_file(
    file: Annotated[UploadFile, File(description="File to upload")],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileUploadResponse:
    """
    Upload a new file.

    - **file**: The file to upload

    Returns the file ID and filename on success.
    """
    try:
        metadata = await service.save_file(file)
        return FileUploadResponse(
            id=metadata.id, filename=metadata.filename, syft_url=metadata.syft_url
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while uploading file"
        )


@router.get(
    "/",
    response_model=FileListResponse,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def list_files(
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileListResponse:
    """
    List all uploaded files.

    Returns a list of file metadata including ID, filename, size, and upload date.
    """
    try:
        files = await service.list_files()
        return FileListResponse(files=files, total=len(files))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while listing files"
        )


@router.get(
    "/{file_id}",
    responses={
        200: {
            "description": "File retrieved successfully",
            "content": {"application/octet-stream": {}},
        },
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def download_file(
    file_id: str,
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    """
    Download a file by ID.

    - **file_id**: The unique identifier of the file

    Returns the file content with appropriate headers.
    """
    try:
        file_path, metadata = await service.get_file(file_id)

        # Determine media type
        media_type = metadata.mime_type
        if not media_type:
            media_type = (
                mimetypes.guess_type(metadata.filename)[0] or "application/octet-stream"
            )

        # Return file response
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=metadata.original_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{metadata.original_filename}"'
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while downloading file"
        )


@router.put(
    "/{file_id}",
    response_model=FileUpdateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_file(
    file_id: str,
    file: Annotated[UploadFile, File(description="New file to replace existing")],
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileUpdateResponse:
    """
    Update an existing file with a new version.

    - **file_id**: The unique identifier of the file to update
    - **file**: The new file to replace the existing one

    Returns the file ID and new filename on success.
    """
    try:
        metadata = await service.update_file(file_id, file)
        return FileUpdateResponse(
            id=metadata.id, filename=metadata.filename, syft_url=metadata.syft_url
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while updating file"
        )


@router.delete(
    "/{file_id}",
    response_model=FileDeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_file(
    file_id: str,
    service: Annotated[FileService, Depends(get_file_service)],
) -> FileDeleteResponse:
    """
    Delete a file by ID.

    - **file_id**: The unique identifier of the file to delete

    Returns a success message on completion.
    """
    try:
        await service.delete_file(file_id)
        return FileDeleteResponse()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while deleting file"
        )


@router.get(
    "/stats/summary",
    response_model=dict,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_storage_stats(
    service: Annotated[FileService, Depends(get_file_service)],
) -> dict:
    """
    Get storage statistics.

    Returns information about total files, total size, and storage configuration.
    """
    try:
        stats = await service.get_storage_stats()
        return stats
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal server error while getting storage stats"
        )
