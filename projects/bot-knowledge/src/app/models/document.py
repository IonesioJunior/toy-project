from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DocumentBase(BaseModel):
    content: str = Field(..., description="The document content")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional metadata for the document"
    )


class DocumentCreate(DocumentBase):
    id: str = Field(..., description="Unique identifier for the document")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "content": "This is a sample document about machine learning and AI.",
                "metadata": {
                    "category": "technology",
                    "author": "John Doe",
                    "tags": ["AI", "ML", "technology"]
                }
            }
        }


class DocumentUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Updated document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated content about deep learning and neural networks.",
                "metadata": {
                    "category": "AI",
                    "updated": True
                }
            }
        }


class DocumentResponse(DocumentBase):
    id: str = Field(..., description="Document ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "content": "This is a sample document about machine learning and AI.",
                "metadata": {
                    "category": "technology",
                    "author": "John Doe"
                },
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T14:30:00"
            }
        }


class DocumentList(BaseModel):
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "id": "doc_001",
                        "content": "Sample document content",
                        "metadata": {"category": "technology"}
                    }
                ],
                "total": 100,
                "limit": 10,
                "offset": 0
            }
        }


class QueryRequest(BaseModel):
    query_text: str = Field(..., description="Text to search for similar documents")
    n_results: int = Field(default=5, ge=1, le=100, description="Number of results to return")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional metadata filters"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "artificial intelligence and neural networks",
                "n_results": 5,
                "metadata_filter": {"category": "technology"}
            }
        }


class QueryResponse(BaseModel):
    documents: List[str] = Field(..., description="Document contents")
    ids: List[str] = Field(..., description="Document IDs")
    distances: List[float] = Field(..., description="Distance scores (lower is more similar)")
    metadatas: List[Dict[str, Any]] = Field(..., description="Document metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": ["Document about AI", "Document about ML"],
                "ids": ["doc_001", "doc_002"],
                "distances": [0.1, 0.3],
                "metadatas": [
                    {"category": "AI"},
                    {"category": "ML"}
                ]
            }
        }


class BatchCreateRequest(BaseModel):
    documents: List[DocumentCreate] = Field(..., description="List of documents to create")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "id": "doc_001",
                        "content": "First document",
                        "metadata": {"index": 1}
                    },
                    {
                        "id": "doc_002",
                        "content": "Second document",
                        "metadata": {"index": 2}
                    }
                ]
            }
        }


class BatchCreateResponse(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Results for each document")
    total: int = Field(..., description="Total documents processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")


class OperationResponse(BaseModel):
    id: str = Field(..., description="Document ID")
    status: str = Field(..., description="Operation status")
    message: Optional[str] = Field(None, description="Additional message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "status": "success",
                "message": "Document created successfully"
            }
        }