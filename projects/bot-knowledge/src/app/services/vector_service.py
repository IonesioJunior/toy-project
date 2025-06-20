import chromadb
from chromadb.api.models.Collection import Collection
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import uuid
import os

from ..database import chroma_client
from ..config import settings
from ..models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    QueryRequest,
    QueryResponse
)
from ..utils.exceptions import (
    DocumentNotFoundError,
    DocumentAlreadyExistsError,
    ChromaDBError
)

logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing vector database operations"""
    
    def __init__(self):
        self.client = chroma_client.client
        self._collection: Optional[Collection] = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or get the ChromaDB collection"""
        try:
            self._collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{settings.chroma_collection_name}' initialized")
            
            # Warm up the embedding model by adding a dummy document if collection is empty
            self._warmup_embedding_model()
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {str(e)}")
            raise ChromaDBError("initialize_collection", e)
    
    def _warmup_embedding_model(self):
        """Warm up the embedding model to avoid timeouts on first use"""
        # Skip warmup in test environment
        if os.environ.get('APP_ENV') == 'testing':
            logger.info("Skipping embedding model warmup in test environment")
            return
            
        try:
            # Check if collection has any documents
            count = self._collection.count()
            if count == 0:
                logger.info("Warming up embedding model with a test document...")
                # Add a temporary document to initialize the embedding model
                self._collection.add(
                    documents=["This is a test document to initialize the embedding model."],
                    ids=["__warmup_test__"],
                    metadatas=[{"_warmup": True}]
                )
                # Remove the test document immediately
                self._collection.delete(ids=["__warmup_test__"])
                logger.info("Embedding model warmed up successfully")
        except Exception as e:
            logger.warning(f"Failed to warm up embedding model: {str(e)}")
            # Don't raise error, this is just an optimization
    
    @property
    def collection(self) -> Collection:
        """Get the current collection"""
        if self._collection is None:
            self._initialize_collection()
        return self._collection
    
    def _document_exists(self, document_id: str) -> bool:
        """Check if a document exists"""
        try:
            result = self.collection.get(ids=[document_id])
            return len(result['ids']) > 0
        except Exception:
            return False
    
    def create_document(self, document: DocumentCreate) -> DocumentResponse:
        """Create a new document in the vector database"""
        try:
            # Check if document already exists
            if self._document_exists(document.id):
                raise DocumentAlreadyExistsError(document.id)
            
            # Add timestamp metadata
            metadata = document.metadata.copy() if document.metadata else {}
            metadata['created_at'] = datetime.utcnow().isoformat()
            metadata['updated_at'] = metadata['created_at']
            
            # Add document to collection with retry logic for model download timeouts
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.collection.add(
                        documents=[document.content],
                        ids=[document.id],
                        metadatas=[metadata]
                    )
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if "timeout" in error_msg and retry_count < max_retries - 1:
                        retry_count += 1
                        logger.warning(f"Timeout during document creation (attempt {retry_count}/{max_retries}), retrying in 10 seconds...")
                        import time
                        time.sleep(10)
                        continue
                    elif "timeout" in error_msg:
                        # Final timeout - provide helpful error message
                        raise Exception("Document upload timed out. This may happen when ChromaDB is downloading the embedding model for the first time. Please try again in a few minutes.")
                    else:
                        raise e
            
            logger.info(f"Document created with ID: {document.id}")
            
            return DocumentResponse(
                id=document.id,
                content=document.content,
                metadata=document.metadata,
                created_at=datetime.fromisoformat(metadata['created_at']),
                updated_at=datetime.fromisoformat(metadata['updated_at'])
            )
            
        except (DocumentAlreadyExistsError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to create document: {str(e)}")
            raise ChromaDBError("create_document", e)
    
    def get_document(self, document_id: str) -> DocumentResponse:
        """Retrieve a document by ID"""
        try:
            result = self.collection.get(ids=[document_id])
            
            if not result['ids']:
                raise DocumentNotFoundError(document_id)
            
            metadata = result['metadatas'][0] or {}
            
            # Extract timestamps
            created_at = metadata.pop('created_at', None)
            updated_at = metadata.pop('updated_at', None)
            
            return DocumentResponse(
                id=result['ids'][0],
                content=result['documents'][0],
                metadata=metadata,
                created_at=datetime.fromisoformat(created_at) if created_at else None,
                updated_at=datetime.fromisoformat(updated_at) if updated_at else None
            )
            
        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to get document: {str(e)}")
            raise ChromaDBError("get_document", e)
    
    def update_document(self, document_id: str, update: DocumentUpdate) -> DocumentResponse:
        """Update an existing document"""
        try:
            # Get existing document
            existing = self.get_document(document_id)
            
            # Prepare updated content and metadata
            updated_content = update.content if update.content is not None else existing.content
            updated_metadata = existing.metadata.copy()
            
            if update.metadata is not None:
                updated_metadata.update(update.metadata)
            
            # Add timestamps
            updated_metadata['created_at'] = existing.created_at.isoformat() if existing.created_at else datetime.utcnow().isoformat()
            updated_metadata['updated_at'] = datetime.utcnow().isoformat()
            
            # Update in ChromaDB
            self.collection.update(
                ids=[document_id],
                documents=[updated_content],
                metadatas=[updated_metadata]
            )
            
            logger.info(f"Document updated with ID: {document_id}")
            
            # Remove timestamps from metadata for response
            created_at = updated_metadata.pop('created_at')
            updated_at = updated_metadata.pop('updated_at')
            
            return DocumentResponse(
                id=document_id,
                content=updated_content,
                metadata=updated_metadata,
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at)
            )
            
        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to update document: {str(e)}")
            raise ChromaDBError("update_document", e)
    
    def delete_document(self, document_id: str) -> Dict[str, str]:
        """Delete a document by ID"""
        try:
            # Check if document exists
            if not self._document_exists(document_id):
                raise DocumentNotFoundError(document_id)
            
            # Delete from ChromaDB
            self.collection.delete(ids=[document_id])
            
            logger.info(f"Document deleted with ID: {document_id}")
            
            return {"id": document_id, "status": "deleted"}
            
        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise ChromaDBError("delete_document", e)
    
    def list_documents(self, limit: int = 10, offset: int = 0) -> Tuple[List[DocumentResponse], int]:
        """List all documents with pagination"""
        try:
            # Get all documents
            all_data = self.collection.get()
            total = len(all_data['ids'])
            
            # Apply pagination
            start_idx = offset
            end_idx = min(offset + limit, total)
            
            documents = []
            for i in range(start_idx, end_idx):
                metadata = all_data['metadatas'][i] or {}
                
                # Extract timestamps
                created_at = metadata.pop('created_at', None)
                updated_at = metadata.pop('updated_at', None)
                
                documents.append(DocumentResponse(
                    id=all_data['ids'][i],
                    content=all_data['documents'][i],
                    metadata=metadata,
                    created_at=datetime.fromisoformat(created_at) if created_at else None,
                    updated_at=datetime.fromisoformat(updated_at) if updated_at else None
                ))
            
            return documents, total
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise ChromaDBError("list_documents", e)
    
    def query_documents(self, query: QueryRequest) -> QueryResponse:
        """Query documents by similarity"""
        try:
            # Build where clause for metadata filtering
            where = None
            if query.metadata_filter:
                where = query.metadata_filter
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query.query_text],
                n_results=query.n_results,
                where=where
            )
            
            # Process results
            if results['ids'] and results['ids'][0]:
                return QueryResponse(
                    documents=results['documents'][0],
                    ids=results['ids'][0],
                    distances=results['distances'][0],
                    metadatas=results['metadatas'][0]
                )
            else:
                return QueryResponse(
                    documents=[],
                    ids=[],
                    distances=[],
                    metadatas=[]
                )
            
        except Exception as e:
            logger.error(f"Failed to query documents: {str(e)}")
            raise ChromaDBError("query_documents", e)
    
    def create_documents_batch(self, documents: List[DocumentCreate]) -> List[Dict[str, Any]]:
        """Create multiple documents in batch"""
        results = []
        
        for doc in documents:
            try:
                created = self.create_document(doc)
                results.append({
                    "id": doc.id,
                    "status": "success",
                    "message": "Document created successfully"
                })
            except DocumentAlreadyExistsError as e:
                results.append({
                    "id": doc.id,
                    "status": "error",
                    "message": str(e)
                })
            except Exception as e:
                results.append({
                    "id": doc.id,
                    "status": "error",
                    "message": f"Failed to create document: {str(e)}"
                })
        
        return results
    
    def delete_all_documents(self) -> Dict[str, str]:
        """Delete all documents in the collection"""
        try:
            # Get all document IDs
            all_data = self.collection.get()
            
            if all_data['ids']:
                # Delete all documents
                self.collection.delete(ids=all_data['ids'])
                count = len(all_data['ids'])
                logger.info(f"Deleted {count} documents from collection")
                return {"status": "success", "message": f"Deleted {count} documents"}
            else:
                return {"status": "success", "message": "No documents to delete"}
            
        except Exception as e:
            logger.error(f"Failed to delete all documents: {str(e)}")
            raise ChromaDBError("delete_all_documents", e)
    
    def reset_collection(self):
        """Reset the collection (delete and recreate)"""
        try:
            # Delete the collection
            self.client.delete_collection(name=settings.chroma_collection_name)
            logger.info(f"Collection '{settings.chroma_collection_name}' deleted")
            
            # Reinitialize
            self._collection = None
            self._initialize_collection()
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {str(e)}")
            raise ChromaDBError("reset_collection", e)