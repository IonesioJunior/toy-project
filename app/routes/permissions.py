"""API routes for managing file permissions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.permissions import (
    BulkPermissionRequest,
    PermissionList,
    PermissionRequest,
    PermissionResponse,
    PermissionUpdate,
)
from app.services.permission_service import PermissionService

router = APIRouter(tags=["permissions"])


def get_permission_service() -> PermissionService:
    """Dependency to get permission service instance."""
    return PermissionService()


@router.get("/files/{file_id}/permissions", response_model=PermissionList)
async def get_file_permissions(
    file_id: str, service: Annotated[PermissionService, Depends(get_permission_service)]
):
    """
    Get all permission rules for a specific file.

    Returns a list of permission rules showing who has access and what type.
    Only the file owner can view permissions.
    """
    try:
        return await service.get_permissions(file_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve permissions: {str(e)}",
        )


@router.post("/files/{file_id}/permissions", response_model=PermissionResponse)
async def grant_file_permission(
    file_id: str,
    request: PermissionRequest,
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Grant permissions to a user for a specific file.

    Only the file owner can grant permissions.
    If a rule already exists for the user, it will be updated.

    Permission types:
    - READ: View and download the file
    - WRITE: Modify the file
    - CREATE: Create new files (for directories)
    - ADMIN: Full control including permission management
    """
    try:
        return await service.grant_permission(file_id, request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant permission: {str(e)}",
        )


@router.put(
    "/files/{file_id}/permissions/{permission_id}", response_model=PermissionResponse
)
async def update_file_permission(
    file_id: str,
    permission_id: str,
    update: PermissionUpdate,
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Update an existing permission rule.

    Only the file owner can update permissions.
    Use this to change permission types, priority, or allow/deny status.
    """
    try:
        return await service.update_permission(file_id, permission_id, update)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update permission: {str(e)}",
        )


@router.delete("/files/{file_id}/permissions/{permission_id}")
async def revoke_file_permission(
    file_id: str,
    permission_id: str,
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Revoke a specific permission rule.

    Only the file owner can revoke permissions.
    The owner must always retain at least one permission rule.
    """
    try:
        return await service.revoke_permission(file_id, permission_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke permission: {str(e)}",
        )


@router.post("/permissions/bulk")
async def apply_bulk_permissions(
    request: BulkPermissionRequest,
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Apply permissions to multiple files or folders using glob patterns.

    Examples:
    - "*.csv" - All CSV files in the root
    - "data/*.json" - All JSON files in the data folder
    - "**/*.txt" - All text files recursively (with recursive=true)

    Only files owned by the current user will be affected.
    """
    try:
        return await service.apply_bulk_permissions(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply bulk permissions: {str(e)}",
        )


@router.get("/permissions/check")
async def check_permission(
    file_id: str,
    user: str,
    permission: str,
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Check if a user has a specific permission for a file.

    This is a utility endpoint for verifying permissions.
    Returns true if the user has the requested permission.
    """
    try:
        # Get file metadata to construct path
        from app.services.file_service import FileService

        file_service = FileService()
        _, metadata = await file_service.get_file(file_id)

        # Get actual file path
        from app.config import FILE_STORAGE_PATH

        file_path = FILE_STORAGE_PATH / f"{file_id}_{metadata.filename}"

        # Check permission
        has_permission = service.check_permission(file_path, user, permission)

        return {
            "user": user,
            "file_id": file_id,
            "permission": permission,
            "has_permission": has_permission,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check permission: {str(e)}",
        )


@router.get("/datasites")
async def get_available_datasites(
    service: Annotated[PermissionService, Depends(get_permission_service)],
):
    """
    Get list of available datasites for sharing files.

    Returns a list of email addresses from datasites that exist in the system,
    excluding the current user's datasite. These emails can be used to grant
    permissions for file sharing.
    """
    try:
        datasites = service.get_available_datasites()
        return {
            "datasites": datasites,
            "total": len(datasites),
            "current_user": service.syft_client.email,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve datasites: {str(e)}",
        )
