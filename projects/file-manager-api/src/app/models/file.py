import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class FileMetadata(BaseModel):
    model_config = ConfigDict()

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    size: int
    mime_type: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    syft_url: str = Field(..., description="SyftBox URL for file access")

    @field_serializer("upload_date")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    message: str = "File uploaded successfully"
    syft_url: str = Field(..., description="SyftBox URL for file access")


class FileListItem(BaseModel):
    model_config = ConfigDict()

    id: str
    filename: str
    size: int
    mime_type: str
    upload_date: datetime
    syft_url: str = Field(..., description="SyftBox URL for file access")
    is_owner: Optional[bool] = Field(
        None, description="Whether the current user owns this file"
    )
    shared_with: Optional[List[str]] = Field(
        None, description="List of users this file is shared with"
    )

    @field_serializer("upload_date")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class FileListResponse(BaseModel):
    files: List[FileListItem]
    total: int


class FileUpdateResponse(BaseModel):
    id: str
    filename: str
    message: str = "File updated successfully"
    syft_url: str = Field(..., description="SyftBox URL for file access")


class FileDeleteResponse(BaseModel):
    message: str = "File deleted successfully"


class ErrorResponse(BaseModel):
    detail: str
    status_code: Optional[int] = None
