from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Dict, Any
import logging

from ..models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentList,
    QueryRequest,
    QueryResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    OperationResponse
)
from ..services.vector_service import VectorService
from ..utils.exceptions import (
    DocumentNotFoundError,
    DocumentAlreadyExistsError,
    ChromaDBError
)
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.api_prefix, tags=["documents"])


def get_vector_service() -> VectorService:
    """Dependency to get vector service instance"""
    return VectorService()


@router.post("/documents", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    service: VectorService = Depends(get_vector_service)
) -> OperationResponse:
    """Create a new document in the vector database"""
    try:
        created_doc = service.create_document(document)
        return OperationResponse(
            id=created_doc.id,
            status="success",
            message="Document created successfully"
        )
    except DocumentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    service: VectorService = Depends(get_vector_service)
) -> DocumentResponse:
    """Retrieve a document by ID"""
    try:
        return service.get_document(document_id)
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.put("/documents/{document_id}", response_model=OperationResponse)
async def update_document(
    document_id: str,
    update: DocumentUpdate,
    service: VectorService = Depends(get_vector_service)
) -> OperationResponse:
    """Update an existing document"""
    try:
        updated_doc = service.update_document(document_id, update)
        return OperationResponse(
            id=updated_doc.id,
            status="success",
            message="Document updated successfully"
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete("/documents/{document_id}", response_model=OperationResponse)
async def delete_document(
    document_id: str,
    service: VectorService = Depends(get_vector_service)
) -> OperationResponse:
    """Delete a document by ID"""
    try:
        result = service.delete_document(document_id)
        return OperationResponse(
            id=document_id,
            status="success",
            message="Document deleted successfully"
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/documents", response_model=DocumentList)
async def list_documents(
    limit: int = Query(
        default=settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Number of documents to return"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of documents to skip"
    ),
    service: VectorService = Depends(get_vector_service)
) -> DocumentList:
    """List all documents with pagination"""
    try:
        documents, total = service.list_documents(limit=limit, offset=offset)
        return DocumentList(
            documents=documents,
            total=total,
            limit=limit,
            offset=offset
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/documents/search", response_model=QueryResponse)
async def search_documents(
    query: QueryRequest,
    service: VectorService = Depends(get_vector_service)
) -> QueryResponse:
    """Search for similar documents using vector similarity"""
    try:
        return service.query_documents(query)
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error searching documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/documents/batch", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_documents_batch(
    batch: BatchCreateRequest,
    service: VectorService = Depends(get_vector_service)
) -> BatchCreateResponse:
    """Create multiple documents in batch"""
    try:
        results = service.create_documents_batch(batch.documents)
        
        # Count successes and failures
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "error")
        
        return BatchCreateResponse(
            results=results,
            total=len(batch.documents),
            successful=successful,
            failed=failed
        )
    except Exception as e:
        logger.error(f"Unexpected error in batch creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during batch creation"
        )


@router.delete("/documents", response_model=Dict[str, str])
async def delete_all_documents(
    confirm: bool = Query(
        default=False,
        description="Confirm deletion of all documents"
    ),
    service: VectorService = Depends(get_vector_service)
) -> Dict[str, str]:
    """Delete all documents (requires confirmation)"""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion not confirmed. Set 'confirm=true' to proceed."
        )
    
    try:
        return service.delete_all_documents()
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting all documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )