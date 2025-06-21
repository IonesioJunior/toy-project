import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from chromadb.api.models.Collection import Collection

from ..config import settings
from ..database import chroma_client
from ..models.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    QueryRequest,
    QueryResponse,
)
from ..utils.exceptions import (
    ChromaDBError,
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
)
from .file_manager_client import FileManagerError, file_manager_client

logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing vector database operations"""

    def __init__(self) -> None:
        self.client = chroma_client.client
        self._collection: Optional[Collection] = None
        self._initialize_collection()

    def _initialize_collection(self) -> None:
        """Initialize or get the ChromaDB collection"""
        try:
            self._collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{settings.chroma_collection_name}' initialized")

            # Warm up the embedding model by adding a dummy document if
            # collection is empty
            self._warmup_embedding_model()

        except Exception as e:
            logger.error(f"Failed to initialize collection: {str(e)}")
            raise ChromaDBError("initialize_collection", e)

    def _warmup_embedding_model(self) -> None:
        """Warm up the embedding model to avoid timeouts on first use"""
        # Skip warmup in test environment
        if os.environ.get("APP_ENV") == "testing":
            logger.info("Skipping embedding model warmup in test environment")
            return

        try:
            logger.info("Warming up embedding model...")
            # Always warm up the model by creating a temporary document
            # This ensures the model is downloaded during startup
            if self._collection is None:
                logger.warning("Collection not initialized, skipping warmup")
                return
            
            self._collection.add(
                documents=[
                    "This is a test document to initialize the embedding model."
                ],
                ids=["__warmup_test__"],
                metadatas=[{"_warmup": True}],
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
        if self._collection is None:
            raise ChromaDBError("collection", Exception("Failed to initialize collection"))
        return self._collection

    def _document_exists(self, document_id: str) -> bool:
        """Check if a document exists"""
        try:
            result = self.collection.get(ids=[document_id])
            return len(result["ids"]) > 0
        except Exception:
            return False

    async def create_document(self, document: DocumentCreate) -> DocumentResponse:
        """Create a new document in the vector database"""
        try:
            # Check if document already exists
            if self._document_exists(document.id):
                raise DocumentAlreadyExistsError(document.id)

            # Add timestamp metadata
            metadata = document.metadata.copy() if document.metadata else {}
            metadata["created_at"] = datetime.now(timezone.utc).isoformat()
            metadata["updated_at"] = metadata["created_at"]

            # Try to upload to file manager first if enabled
            file_manager_id = None
            file_manager_url = None
            if settings.enable_file_manager:
                try:
                    # Create filename from document ID
                    filename = f"document_{document.id}.txt"

                    # Upload to file manager
                    file_result = await file_manager_client.upload_document_file(
                        content=document.content,
                        filename=filename,
                        metadata=document.metadata,
                    )

                    if file_result:
                        file_manager_id = file_result.get("id")
                        file_manager_url = file_result.get("syft_url")

                        # Add file manager info to metadata
                        metadata["file_manager_id"] = file_manager_id
                        metadata["file_manager_url"] = file_manager_url
                        metadata["file_size"] = len(document.content.encode("utf-8"))
                        metadata["mime_type"] = "text/plain"

                        logger.info(
                            f"Document uploaded to file manager with ID: "
                            f"{file_manager_id}"
                        )
                    else:
                        logger.warning("File manager upload returned no result")

                except FileManagerError as e:
                    logger.error(f"File manager upload failed: {str(e)}")
                    # Continue without file storage
                except Exception as e:
                    logger.error(f"Unexpected error during file upload: {str(e)}")
                    # Continue without file storage

            # Add document to collection with retry logic for model download timeouts
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    self.collection.add(
                        documents=[document.content],
                        ids=[document.id],
                        metadatas=[metadata],
                    )
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if "timeout" in error_msg and retry_count < max_retries - 1:
                        retry_count += 1
                        logger.warning(
                            f"Timeout during document creation "
                            f"(attempt {retry_count}/{max_retries}), "
                            f"retrying in 10 seconds..."
                        )
                        import time

                        time.sleep(10)
                        continue
                    elif "timeout" in error_msg:
                        # If we uploaded to file manager, try to clean up
                        if file_manager_id and isinstance(file_manager_id, str):
                            logger.warning(
                                "Cleaning up file manager upload due to "
                                "ChromaDB timeout"
                            )
                            await file_manager_client.delete_document_file(
                                file_manager_id
                            )
                        # Final timeout - provide helpful error message
                        raise Exception(
                            "Document upload timed out. This may happen when "
                            "ChromaDB is downloading the embedding model for "
                            "the first time. Please try again in a few minutes."
                        )
                    else:
                        # If we uploaded to file manager, try to clean up
                        if file_manager_id and isinstance(file_manager_id, str):
                            logger.warning(
                                "Cleaning up file manager upload due to ChromaDB error"
                            )
                            await file_manager_client.delete_document_file(
                                file_manager_id
                            )
                        raise e

            logger.info(f"Document created with ID: {document.id}")

            # Extract file manager fields from metadata for response
            response_metadata = document.metadata.copy() if document.metadata else {}
            file_manager_id = metadata.get("file_manager_id")
            file_manager_url = metadata.get("file_manager_url")
            file_size = metadata.get("file_size")
            mime_type = metadata.get("mime_type")

            return DocumentResponse(
                id=document.id,
                content=document.content,
                metadata=response_metadata,
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=datetime.fromisoformat(metadata["updated_at"]),
                file_manager_id=file_manager_id,
                file_manager_url=file_manager_url,
                file_size=file_size,
                mime_type=mime_type,
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

            if not result["ids"]:
                raise DocumentNotFoundError(document_id)

            # Handle None values in ChromaDB results
            raw_metadata = result["metadatas"][0] if result["metadatas"] else None
            # Cast Mapping to dict for mutable operations
            metadata: Dict[str, Any] = dict(raw_metadata) if raw_metadata else {}

            # Extract timestamps and file manager fields
            created_at = metadata.pop("created_at", None)
            updated_at = metadata.pop("updated_at", None)
            file_manager_id = metadata.pop("file_manager_id", None)
            file_manager_url = metadata.pop("file_manager_url", None)
            file_size = metadata.pop("file_size", None)
            mime_type = metadata.pop("mime_type", None)

            # Handle potential None values in results
            document_id = result["ids"][0] if result["ids"] else document_id
            document_content = result["documents"][0] if result["documents"] else ""
            
            return DocumentResponse(
                id=document_id,
                content=document_content,
                metadata=metadata,
                created_at=datetime.fromisoformat(created_at) if created_at and isinstance(created_at, str) else None,
                updated_at=datetime.fromisoformat(updated_at) if updated_at and isinstance(updated_at, str) else None,
                file_manager_id=file_manager_id,
                file_manager_url=file_manager_url,
                file_size=file_size,
                mime_type=mime_type,
            )

        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to get document: {str(e)}")
            raise ChromaDBError("get_document", e)

    async def update_document(
        self, document_id: str, update: DocumentUpdate
    ) -> DocumentResponse:
        """Update an existing document"""
        try:
            # Get existing document
            existing = self.get_document(document_id)

            # Prepare updated content and metadata
            updated_content = (
                update.content if update.content is not None else existing.content
            )
            updated_metadata = existing.metadata.copy() if existing.metadata else {}

            if update.metadata is not None:
                updated_metadata.update(update.metadata)

            # Add timestamps
            updated_metadata["created_at"] = (
                existing.created_at.isoformat()
                if existing.created_at
                else datetime.now(timezone.utc).isoformat()
            )
            updated_metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update file in file manager if content changed and file exists
            if settings.enable_file_manager and update.content is not None:
                file_manager_id = updated_metadata.get("file_manager_id")
                if file_manager_id and isinstance(file_manager_id, str):
                    try:
                        filename = f"document_{document_id}.txt"
                        file_result = await file_manager_client.update_document_file(
                            file_id=file_manager_id,
                            content=updated_content,
                            filename=filename,
                        )

                        if file_result:
                            # Update metadata with new file info
                            updated_metadata["file_manager_url"] = file_result.get(
                                "syft_url", updated_metadata.get("file_manager_url")
                            )
                            updated_metadata["file_size"] = len(
                                updated_content.encode("utf-8")
                            )
                            logger.info(
                                f"Document updated in file manager: {file_manager_id}"
                            )
                        else:
                            logger.warning(
                                "Failed to update document in file manager: "
                                f"{file_manager_id}"
                            )

                    except FileManagerError as e:
                        logger.error(f"File manager update failed: {str(e)}")
                        # Continue with ChromaDB update
                    except Exception as e:
                        logger.error(f"Unexpected error during file update: {str(e)}")
                        # Continue with ChromaDB update

            # Update in ChromaDB
            self.collection.update(
                ids=[document_id],
                documents=[updated_content],
                metadatas=[updated_metadata],
            )

            logger.info(f"Document updated with ID: {document_id}")

            # Remove timestamps and file manager fields from metadata for response
            created_at = updated_metadata.pop("created_at")
            updated_at = updated_metadata.pop("updated_at")
            file_manager_id = updated_metadata.pop("file_manager_id", None)
            file_manager_url = updated_metadata.pop("file_manager_url", None)
            file_size = updated_metadata.pop("file_size", None)
            mime_type = updated_metadata.pop("mime_type", None)

            return DocumentResponse(
                id=document_id,
                content=updated_content,
                metadata=updated_metadata,
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at),
                file_manager_id=file_manager_id,
                file_manager_url=file_manager_url,
                file_size=file_size,
                mime_type=mime_type,
            )

        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to update document: {str(e)}")
            raise ChromaDBError("update_document", e)

    async def delete_document(self, document_id: str) -> Dict[str, str]:
        """Delete a document by ID"""
        try:
            # Check if document exists
            if not self._document_exists(document_id):
                raise DocumentNotFoundError(document_id)

            # Get document metadata to check for file_manager_id
            file_manager_id = None
            if settings.enable_file_manager:
                try:
                    result = self.collection.get(ids=[document_id])
                    if result["ids"] and result["metadatas"] and result["metadatas"][0]:
                        raw_metadata = result["metadatas"][0]
                        # Convert Mapping to dict for safe access
                        metadata_dict = dict(raw_metadata) if raw_metadata else {}
                        file_manager_id = metadata_dict.get("file_manager_id")
                except Exception as e:
                    logger.warning(f"Could not retrieve file_manager_id: {str(e)}")

            # Delete from ChromaDB
            self.collection.delete(ids=[document_id])

            logger.info(f"Document deleted with ID: {document_id}")

            # Delete from file manager if we have a file_id
            if file_manager_id and settings.enable_file_manager:
                try:
                    # Ensure file_manager_id is a string
                    if isinstance(file_manager_id, str):
                        deleted = await file_manager_client.delete_document_file(
                            file_manager_id
                        )
                    else:
                        deleted = False
                        logger.warning(
                            f"Invalid file_manager_id type: {type(file_manager_id)}"
                        )
                    if deleted:
                        logger.info(
                            f"Document deleted from file manager: {file_manager_id}"
                        )
                    else:
                        logger.warning(
                            "Failed to delete document from file manager: "
                            f"{file_manager_id}"
                        )
                except Exception as e:
                    logger.error(f"Error deleting from file manager: {str(e)}")
                    # Don't fail the overall operation

            return {"id": document_id, "status": "deleted"}

        except (DocumentNotFoundError, ChromaDBError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise ChromaDBError("delete_document", e)

    def list_documents(
        self, limit: int = 10, offset: int = 0
    ) -> Tuple[List[DocumentResponse], int]:
        """List all documents with pagination"""
        try:
            # Get all documents
            all_data = self.collection.get()
            # Handle None values in results
            ids = all_data["ids"] if all_data["ids"] is not None else []
            total = len(ids)

            # Apply pagination
            start_idx = offset
            end_idx = min(offset + limit, total)

            documents = []
            for i in range(start_idx, end_idx):
                # Handle None values in metadatas list
                if all_data["metadatas"] is None or i >= len(all_data["metadatas"]):
                    metadata: Dict[str, Any] = {}
                else:
                    raw_metadata = all_data["metadatas"][i]
                    # Cast Mapping to dict for mutable operations
                    metadata = dict(raw_metadata) if raw_metadata else {}

                # Extract timestamps and file manager fields
                created_at = metadata.pop("created_at", None)
                updated_at = metadata.pop("updated_at", None)
                file_manager_id = metadata.pop("file_manager_id", None)
                file_manager_url = metadata.pop("file_manager_url", None)
                file_size = metadata.pop("file_size", None)
                mime_type = metadata.pop("mime_type", None)

                # Handle potential None values in lists
                doc_id = all_data["ids"][i] if all_data["ids"] and i < len(all_data["ids"]) else f"unknown_{i}"
                doc_content = all_data["documents"][i] if all_data["documents"] and i < len(all_data["documents"]) else ""
                
                documents.append(
                    DocumentResponse(
                        id=doc_id,
                        content=doc_content,
                        metadata=metadata,
                        created_at=(
                            datetime.fromisoformat(created_at) if created_at and isinstance(created_at, str) else None
                        ),
                        updated_at=(
                            datetime.fromisoformat(updated_at) if updated_at and isinstance(updated_at, str) else None
                        ),
                        file_manager_id=file_manager_id,
                        file_manager_url=file_manager_url,
                        file_size=file_size,
                        mime_type=mime_type,
                    )
                )

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
                query_texts=[query.query_text], n_results=query.n_results, where=where
            )

            # Process results with proper None handling
            if results["ids"] and len(results["ids"]) > 0 and results["ids"][0] is not None:
                # Handle potential None values in nested lists
                documents = results["documents"][0] if results["documents"] and len(results["documents"]) > 0 and results["documents"][0] is not None else []
                ids = results["ids"][0] if results["ids"] and len(results["ids"]) > 0 and results["ids"][0] is not None else []
                distances = results["distances"][0] if results["distances"] and len(results["distances"]) > 0 and results["distances"][0] is not None else []
                
                # Handle metadatas - convert Mapping to dict if needed
                raw_metadatas = results["metadatas"][0] if results["metadatas"] and len(results["metadatas"]) > 0 and results["metadatas"][0] is not None else []
                metadatas: List[Dict[str, Any]] = []
                if raw_metadatas:
                    for raw_meta in raw_metadatas:
                        if raw_meta:
                            metadatas.append(dict(raw_meta))
                        else:
                            metadatas.append({})
                
                return QueryResponse(
                    documents=documents if documents else [],
                    ids=ids if ids else [],
                    distances=distances if distances else [],
                    metadatas=metadatas,
                )
            else:
                return QueryResponse(documents=[], ids=[], distances=[], metadatas=[])

        except Exception as e:
            logger.error(f"Failed to query documents: {str(e)}")
            raise ChromaDBError("query_documents", e)

    async def create_documents_batch(
        self, documents: List[DocumentCreate]
    ) -> List[Dict[str, Any]]:
        """Create multiple documents in batch"""
        results = []

        for doc in documents:
            try:
                await self.create_document(doc)
                results.append(
                    {
                        "id": doc.id,
                        "status": "success",
                        "message": "Document created successfully",
                    }
                )
            except DocumentAlreadyExistsError as e:
                results.append({"id": doc.id, "status": "error", "message": str(e)})
            except Exception as e:
                results.append(
                    {
                        "id": doc.id,
                        "status": "error",
                        "message": f"Failed to create document: {str(e)}",
                    }
                )

        return results

    async def delete_all_documents(self) -> Dict[str, str]:
        """Delete all documents in the collection"""
        try:
            # Get all document IDs and metadata
            all_data = self.collection.get()

            # Handle None values in results
            ids = all_data["ids"] if all_data["ids"] is not None else []
            
            if ids:
                # If file manager is enabled, try to delete files
                if settings.enable_file_manager:
                    deleted_files = 0
                    for i, doc_id in enumerate(ids):
                        # Handle None values in metadatas
                        if all_data["metadatas"] is None or i >= len(all_data["metadatas"]):
                            metadata: Dict[str, Any] = {}
                        else:
                            raw_metadata = all_data["metadatas"][i]
                            # Cast Mapping to dict
                            metadata = dict(raw_metadata) if raw_metadata else {}
                        file_manager_id = metadata.get("file_manager_id")

                        if file_manager_id and isinstance(file_manager_id, str):
                            try:
                                deleted = (
                                    await file_manager_client.delete_document_file(
                                        file_manager_id
                                    )
                                )
                                if deleted:
                                    deleted_files += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to delete file {file_manager_id}: {str(e)}"
                                )

                    if deleted_files > 0:
                        logger.info(f"Deleted {deleted_files} files from file manager")

                # Delete all documents from ChromaDB
                self.collection.delete(ids=ids)
                count = len(ids)
                logger.info(f"Deleted {count} documents from collection")
                return {"status": "success", "message": f"Deleted {count} documents"}
            else:
                return {"status": "success", "message": "No documents to delete"}

        except Exception as e:
            logger.error(f"Failed to delete all documents: {str(e)}")
            raise ChromaDBError("delete_all_documents", e)

    def reset_collection(self) -> None:
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
