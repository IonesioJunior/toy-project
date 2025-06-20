"""Permission models for SyftBox permission management."""

import re
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PermissionRequest(BaseModel):
    """Request model for granting permissions."""

    user: str = Field(..., description="Email address or '*' for all users")
    permissions: List[str] = Field(
        ..., description="List of permissions: READ, WRITE, CREATE, ADMIN"
    )
    path_pattern: Optional[str] = Field(
        None, description="Optional glob pattern for bulk permissions"
    )

    @field_validator("user")
    @classmethod
    def validate_user(cls, v):
        """Validate user email or wildcard."""
        if v == "*":
            return v
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address")
        return v.lower()

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permission types."""
        valid_permissions = {"READ", "WRITE", "CREATE", "ADMIN"}
        for perm in v:
            if perm.upper() not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of {valid_permissions}"
                )
        return [p.upper() for p in v]


class PermissionResponse(BaseModel):
    """Response model for permission information."""

    id: str = Field(..., description="Unique permission rule ID")
    user: str = Field(..., description="User email or wildcard")
    path: str = Field(..., description="Path or pattern this permission applies to")
    permissions: List[str] = Field(..., description="Granted permissions")
    allow: bool = Field(
        default=True, description="Whether this is an allow or deny rule"
    )
    priority: int = Field(default=0, description="Rule priority for resolution")
    created_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PermissionUpdate(BaseModel):
    """Request model for updating permissions."""

    permissions: Optional[List[str]] = Field(
        None, description="New list of permissions"
    )
    allow: Optional[bool] = Field(None, description="Change to allow/deny rule")
    priority: Optional[int] = Field(None, description="Update rule priority")

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permission types if provided."""
        if v is None:
            return v
        valid_permissions = {"READ", "WRITE", "CREATE", "ADMIN"}
        for perm in v:
            if perm.upper() not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of {valid_permissions}"
                )
        return [p.upper() for p in v]


class BulkPermissionRequest(BaseModel):
    """Request model for bulk permission operations."""

    user: str = Field(..., description="Email address or '*' for all users")
    permissions: List[str] = Field(..., description="List of permissions to grant")
    path_pattern: str = Field(
        ..., description="Glob pattern for files/folders (e.g., '*.csv', 'data/*')"
    )
    recursive: bool = Field(
        default=False, description="Apply to subdirectories recursively"
    )

    @field_validator("user")
    @classmethod
    def validate_user(cls, v):
        """Validate user email or wildcard."""
        if v == "*":
            return v
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address")
        return v.lower()

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permission types."""
        valid_permissions = {"READ", "WRITE", "CREATE", "ADMIN"}
        for perm in v:
            if perm.upper() not in valid_permissions:
                raise ValueError(
                    f"Invalid permission: {perm}. Must be one of {valid_permissions}"
                )
        return [p.upper() for p in v]


class PermissionList(BaseModel):
    """Response model for listing permissions."""

    permissions: List[PermissionResponse] = Field(
        ..., description="List of permission rules"
    )
    total: int = Field(..., description="Total number of permission rules")
    file_path: str = Field(..., description="Path the permissions apply to")
    is_owner: bool = Field(..., description="Whether the current user is the owner")
