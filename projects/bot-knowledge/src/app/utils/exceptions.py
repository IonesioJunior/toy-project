from typing import Optional, Any


class VectorDBException(Exception):
    """Base exception for Vector DB operations"""
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class DocumentNotFoundError(VectorDBException):
    """Raised when a document is not found"""
    def __init__(self, document_id: str):
        message = f"Document with ID '{document_id}' not found"
        super().__init__(message, {"document_id": document_id})


class DocumentAlreadyExistsError(VectorDBException):
    """Raised when trying to create a document that already exists"""
    def __init__(self, document_id: str):
        message = f"Document with ID '{document_id}' already exists"
        super().__init__(message, {"document_id": document_id})


class ChromaDBError(VectorDBException):
    """Raised when ChromaDB operations fail"""
    def __init__(self, operation: str, error: Exception):
        message = f"ChromaDB operation '{operation}' failed: {str(error)}"
        super().__init__(message, {"operation": operation, "error": str(error)})


class ValidationError(VectorDBException):
    """Raised when validation fails"""
    def __init__(self, field: str, message: str):
        full_message = f"Validation error for field '{field}': {message}"
        super().__init__(full_message, {"field": field, "message": message})