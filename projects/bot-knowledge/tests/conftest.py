import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import tempfile
import shutil
from pathlib import Path

from src.app.main import app
from src.app.services.vector_service import VectorService
from src.app.models.document import DocumentCreate, DocumentResponse
from datetime import datetime


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB during tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_vector_service():
    """Create a mock vector service"""
    service = MagicMock(spec=VectorService)
    
    # Mock document response
    mock_doc = DocumentResponse(
        id="test_doc_1",
        content="Test document content",
        metadata={"category": "test"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Configure mock methods
    service.create_document.return_value = mock_doc
    service.get_document.return_value = mock_doc
    service.update_document.return_value = mock_doc
    service.delete_document.return_value = {"id": "test_doc_1", "status": "deleted"}
    service.list_documents.return_value = ([mock_doc], 1)
    service.query_documents.return_value = {
        "documents": ["Test document content"],
        "ids": ["test_doc_1"],
        "distances": [0.1],
        "metadatas": [{"category": "test"}]
    }
    service.create_documents_batch.return_value = [
        {"id": "test_doc_1", "status": "success", "message": "Document created successfully"}
    ]
    service.delete_all_documents.return_value = {"status": "success", "message": "All documents deleted"}
    
    return service


@pytest.fixture
def sample_document():
    """Create a sample document for testing"""
    return DocumentCreate(
        id="test_doc_1",
        content="This is a test document about artificial intelligence and machine learning.",
        metadata={
            "category": "technology",
            "author": "Test Author",
            "tags": ["AI", "ML", "test"]
        }
    )


@pytest.fixture
def sample_documents():
    """Create multiple sample documents for testing"""
    return [
        DocumentCreate(
            id=f"test_doc_{i}",
            content=f"Test document {i} content about topic {i}",
            metadata={"index": i, "category": f"category_{i % 3}"}
        )
        for i in range(5)
    ]


@pytest.fixture(autouse=True)
def mock_chroma_client(temp_chroma_dir):
    """Mock ChromaDB client for all tests"""
    with patch('src.app.database.settings.chroma_persist_directory', temp_chroma_dir):
        yield


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    with patch('src.app.config.settings') as mock:
        mock.app_name = "Test FastAPI ChromaDB API"
        mock.app_version = "1.0.0-test"
        mock.debug_mode = True
        mock.chroma_persist_directory = "./test_chroma_db"
        mock.chroma_collection_name = "test_documents"
        mock.api_prefix = "/api/v1"
        mock.max_page_size = 100
        mock.default_page_size = 10
        mock.cors_allowed_origins = ["*"]
        mock.host = "0.0.0.0"
        mock.port = 8000
        mock.reload = False
        yield mock