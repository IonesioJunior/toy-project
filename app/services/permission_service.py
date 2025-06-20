"""Service for managing SyftBox permissions."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import HTTPException, status

try:
    from syft_core.permissions import PermissionRule, SyftPermission
except ImportError:
    # For testing, create mock classes
    class PermissionRule:
        pass

    class SyftPermission:
        def __init__(self, path):
            self.path = path

        def has_permission(self, user_email, file_path, permission):
            # In mock mode, only owner has permissions
            return False


import re

from app.config import FILE_STORAGE_PATH, syft_client
from app.models.permissions import (
    BulkPermissionRequest,
    PermissionList,
    PermissionRequest,
    PermissionResponse,
    PermissionUpdate,
)
from app.services.file_service import FileService


class PermissionService:
    """Service for managing file and folder permissions using SyftBox."""

    def __init__(self):
        """Initialize the permission service."""
        if not syft_client:
            raise RuntimeError("SyftBox client not initialized")
        self.syft_client = syft_client
        self.storage_path = FILE_STORAGE_PATH

    def _get_permission_file_path(self, file_path: Path) -> Path:
        """Get the path to the .syftperm file for a given path."""
        if file_path.is_file():
            # For files, permission file is in the same directory
            return file_path.parent / ".syftperm"
        else:
            # For directories, permission file is inside the directory
            return file_path / ".syftperm"

    def _load_permissions(self, file_path: Path) -> Dict:
        """Load permissions from .syftperm file."""
        perm_file = self._get_permission_file_path(file_path)

        if not perm_file.exists():
            # Initialize with owner having full permissions
            return {
                "rules": [
                    {
                        "id": str(uuid.uuid4()),
                        "user": self.syft_client.email,
                        "path": "*",
                        "permissions": ["READ", "WRITE", "CREATE", "ADMIN"],
                        "allow": True,
                        "priority": 100,
                    }
                ]
            }

        try:
            with open(perm_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid permission file format",
            )

    def _save_permissions(self, file_path: Path, permissions: Dict) -> None:
        """Save permissions to .syftperm file."""
        perm_file = self._get_permission_file_path(file_path)

        # Ensure directory exists
        perm_file.parent.mkdir(parents=True, exist_ok=True)

        with open(perm_file, "w") as f:
            json.dump(permissions, f, indent=2)

    def _is_owner(self, file_path: Path) -> bool:
        """Check if the current user is the owner of the file/folder."""
        # In SyftBox, the owner is determined by the datasite path
        # Check if the file is within the user's datasite
        try:
            file_path.relative_to(self.syft_client.my_datasite)
            return True
        except ValueError:
            # File is not in user's datasite
            return False

    async def get_permissions(self, file_id: str) -> PermissionList:
        """Get all permissions for a file."""
        # Get file metadata
        file_service = FileService()
        _, metadata = await file_service.get_file(file_id)

        # Get actual file path
        file_path = self.storage_path / f"{file_id}_{metadata.filename}"

        # Load permissions
        perm_data = self._load_permissions(file_path)

        # Convert to response models
        permissions = []
        for rule in perm_data.get("rules", []):
            permissions.append(
                PermissionResponse(
                    id=rule.get("id", str(uuid.uuid4())),
                    user=rule["user"],
                    path=rule.get("path", metadata.filename),
                    permissions=rule["permissions"],
                    allow=rule.get("allow", True),
                    priority=rule.get("priority", 0),
                    created_date=(
                        datetime.fromisoformat(rule["created_date"])
                        if "created_date" in rule
                        else datetime.now()
                    ),
                )
            )

        return PermissionList(
            permissions=permissions,
            total=len(permissions),
            file_path=str(file_path),
            is_owner=self._is_owner(file_path),
        )

    async def grant_permission(
        self, file_id: str, request: PermissionRequest
    ) -> PermissionResponse:
        """Grant permissions to a user for a file."""
        # Get file metadata
        file_service = FileService()
        _, metadata = await file_service.get_file(file_id)

        # Get actual file path
        file_path = self.storage_path / f"{file_id}_{metadata.filename}"

        # Check if user is owner
        if not self._is_owner(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the file owner can manage permissions",
            )

        # Load existing permissions
        perm_data = self._load_permissions(file_path)

        # Check if rule already exists for this user
        for rule in perm_data.get("rules", []):
            if rule["user"] == request.user and rule.get("path", "*") == (
                request.path_pattern or "*"
            ):
                # Update existing rule
                rule["permissions"] = request.permissions
                rule["updated_date"] = datetime.now().isoformat()

                # Save and return
                self._save_permissions(file_path, perm_data)

                return PermissionResponse(
                    id=rule["id"],
                    user=rule["user"],
                    path=rule.get("path", metadata.filename),
                    permissions=rule["permissions"],
                    allow=rule.get("allow", True),
                    priority=rule.get("priority", 0),
                )

        # Create new rule
        new_rule = {
            "id": str(uuid.uuid4()),
            "user": request.user,
            "path": request.path_pattern or metadata.filename,
            "permissions": request.permissions,
            "allow": True,
            "priority": 0,
            "created_date": datetime.now().isoformat(),
        }

        if "rules" not in perm_data:
            perm_data["rules"] = []
        perm_data["rules"].append(new_rule)

        # Save permissions
        self._save_permissions(file_path, perm_data)

        return PermissionResponse(
            id=new_rule["id"],
            user=new_rule["user"],
            path=new_rule["path"],
            permissions=new_rule["permissions"],
            allow=new_rule["allow"],
            priority=new_rule["priority"],
        )

    async def update_permission(
        self, file_id: str, permission_id: str, update: PermissionUpdate
    ) -> PermissionResponse:
        """Update an existing permission rule."""
        # Get file metadata
        file_service = FileService()
        _, metadata = await file_service.get_file(file_id)

        # Get actual file path
        file_path = self.storage_path / f"{file_id}_{metadata.filename}"

        # Check if user is owner
        if not self._is_owner(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the file owner can manage permissions",
            )

        # Load permissions
        perm_data = self._load_permissions(file_path)

        # Find and update the rule
        rule_found = False
        for rule in perm_data.get("rules", []):
            if rule.get("id") == permission_id:
                rule_found = True

                # Update fields if provided
                if update.permissions is not None:
                    rule["permissions"] = update.permissions
                if update.allow is not None:
                    rule["allow"] = update.allow
                if update.priority is not None:
                    rule["priority"] = update.priority

                rule["updated_date"] = datetime.now().isoformat()

                # Save permissions
                self._save_permissions(file_path, perm_data)

                return PermissionResponse(
                    id=rule["id"],
                    user=rule["user"],
                    path=rule.get("path", metadata.filename),
                    permissions=rule["permissions"],
                    allow=rule.get("allow", True),
                    priority=rule.get("priority", 0),
                )

        if not rule_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission rule not found",
            )

    async def revoke_permission(
        self, file_id: str, permission_id: str
    ) -> Dict[str, str]:
        """Revoke a permission rule."""
        # Get file metadata
        file_service = FileService()
        _, metadata = await file_service.get_file(file_id)

        # Get actual file path
        file_path = self.storage_path / f"{file_id}_{metadata.filename}"

        # Check if user is owner
        if not self._is_owner(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the file owner can manage permissions",
            )

        # Load permissions
        perm_data = self._load_permissions(file_path)

        # Find and remove the rule
        original_count = len(perm_data.get("rules", []))
        perm_data["rules"] = [
            rule
            for rule in perm_data.get("rules", [])
            if rule.get("id") != permission_id
        ]

        if len(perm_data["rules"]) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission rule not found",
            )

        # Don't allow removing all permissions from owner
        owner_has_permission = any(
            rule["user"] == self.syft_client.email for rule in perm_data["rules"]
        )

        if not owner_has_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove all permissions from the owner",
            )

        # Save permissions
        self._save_permissions(file_path, perm_data)

        return {"message": "Permission revoked successfully"}

    async def apply_bulk_permissions(
        self, request: BulkPermissionRequest
    ) -> Dict[str, any]:
        """Apply permissions to multiple files/folders using patterns."""
        # For bulk permissions, work with the storage directory
        base_path = self.storage_path

        # Find matching paths
        matching_paths = []
        if request.recursive and base_path.is_dir():
            # Recursive search
            for path in base_path.rglob(request.path_pattern):
                if self._is_owner(path):
                    matching_paths.append(path)
        else:
            # Non-recursive search
            for path in base_path.glob(request.path_pattern):
                if self._is_owner(path):
                    matching_paths.append(path)

        if not matching_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No matching files found for pattern: {request.path_pattern}",
            )

        # Apply permissions to each matching path
        results = {"processed": 0, "failed": 0, "paths": []}

        for path in matching_paths:
            try:
                # Load existing permissions
                perm_data = self._load_permissions(path)

                # Add or update rule for the user
                rule_exists = False
                for rule in perm_data.get("rules", []):
                    if rule["user"] == request.user:
                        rule["permissions"] = request.permissions
                        rule["updated_date"] = datetime.now().isoformat()
                        rule_exists = True
                        break

                if not rule_exists:
                    new_rule = {
                        "id": str(uuid.uuid4()),
                        "user": request.user,
                        "path": "*",
                        "permissions": request.permissions,
                        "allow": True,
                        "priority": 0,
                        "created_date": datetime.now().isoformat(),
                    }
                    if "rules" not in perm_data:
                        perm_data["rules"] = []
                    perm_data["rules"].append(new_rule)

                # Save permissions
                self._save_permissions(path, perm_data)

                results["processed"] += 1
                results["paths"].append(str(path))

            except Exception:
                results["failed"] += 1

        return {
            "message": f"Bulk permissions applied to {results['processed']} paths",
            "details": results,
        }

    def check_permission(
        self, file_path: Path, user: str, permission_type: str
    ) -> bool:
        """Check if a user has specific permission for a file."""
        try:
            # Use syft_core's permission system
            syft_permission = SyftPermission(file_path.parent)

            # Convert permission type to list format
            permission_list = [permission_type.upper()]

            # Check permission
            has_permission = syft_permission.has_permission(
                user_email=user, file_path=file_path, permission=permission_list
            )

            return has_permission

        except Exception:
            # If permission check fails, default to owner-only access
            return self._is_owner(file_path)

    def get_available_datasites(self) -> List[str]:
        """Get list of datasite emails available for sharing.

        Returns a list of email addresses from available datasites,
        excluding the current user's datasite.
        """
        datasites = []

        # Check if datasites directory exists
        if hasattr(syft_client, "datasites") and syft_client.datasites.exists():
            # Iterate through directories in datasites folder
            for datasite_dir in syft_client.datasites.iterdir():
                if datasite_dir.is_dir():
                    # Extract email from directory name
                    email = datasite_dir.name

                    # Validate it looks like an email
                    if self._is_valid_email(email) and email != syft_client.email:
                        datasites.append(email)

        # Sort for consistent ordering
        datasites.sort()
        return datasites

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))
