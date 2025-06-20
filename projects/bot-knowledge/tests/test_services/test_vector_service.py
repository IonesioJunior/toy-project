import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.app.services.vector_service import VectorService
from src.app.models.document import DocumentCreate, DocumentUpdate, QueryRequest
from src.app.utils.exceptions import DocumentNotFoundError, DocumentAlreadyExistsError


class TestVectorService:
    """Test cases for VectorService"""
    
    @pytest.fixture
    def mock_collection(self):
        """Create a mock ChromaDB collection"""
        collection = MagicMock()
        collection.add = MagicMock()
        collection.get = MagicMock()
        collection.update = MagicMock()
        collection.delete = MagicMock()
        collection.query = MagicMock()
        return collection
    
    @pytest.fixture
    def vector_service(self, mock_collection):
        """Create a VectorService instance with mocked dependencies"""
        with patch('src.app.services.vector_service.chroma_client') as mock_client:
            mock_client.client.get_or_create_collection.return_value = mock_collection
            service = VectorService()
            service._collection = mock_collection
            return service
    
    def test_create_document_success(self, vector_service, sample_document, mock_collection):
        """Test successful document creation"""
        mock_collection.get.return_value = {'ids': []}
        
        result = vector_service.create_document(sample_document)
        
        assert result.id == sample_document.id
        assert result.content == sample_document.content
        assert result.metadata == sample_document.metadata
        mock_collection.add.assert_called_once()
    
    def test_create_document_already_exists(self, vector_service, sample_document, mock_collection):
        """Test document creation when document already exists"""
        mock_collection.get.return_value = {'ids': [sample_document.id]}
        
        with pytest.raises(DocumentAlreadyExistsError):
            vector_service.create_document(sample_document)
    
    def test_get_document_success(self, vector_service, mock_collection):
        """Test successful document retrieval"""
        mock_collection.get.return_value = {
            'ids': ['test_doc_1'],
            'documents': ['Test content'],
            'metadatas': [{
                'category': 'test',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }]
        }
        
        result = vector_service.get_document('test_doc_1')
        
        assert result.id == 'test_doc_1'
        assert result.content == 'Test content'
        assert result.metadata['category'] == 'test'
    
    def test_get_document_not_found(self, vector_service, mock_collection):
        """Test document retrieval when document doesn't exist"""
        mock_collection.get.return_value = {'ids': []}
        
        with pytest.raises(DocumentNotFoundError):
            vector_service.get_document('nonexistent')
    
    def test_update_document_success(self, vector_service, mock_collection):
        """Test successful document update"""
        # Mock existing document
        mock_collection.get.return_value = {
            'ids': ['test_doc_1'],
            'documents': ['Old content'],
            'metadatas': [{
                'category': 'test',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }]
        }
        
        update = DocumentUpdate(content="New content", metadata={"updated": True})
        result = vector_service.update_document('test_doc_1', update)
        
        assert result.id == 'test_doc_1'
        assert result.content == 'New content'
        mock_collection.update.assert_called_once()
    
    def test_delete_document_success(self, vector_service, mock_collection):
        """Test successful document deletion"""
        mock_collection.get.return_value = {'ids': ['test_doc_1']}
        
        result = vector_service.delete_document('test_doc_1')
        
        assert result['id'] == 'test_doc_1'
        assert result['status'] == 'deleted'
        mock_collection.delete.assert_called_once_with(ids=['test_doc_1'])
    
    def test_delete_document_not_found(self, vector_service, mock_collection):
        """Test document deletion when document doesn't exist"""
        mock_collection.get.return_value = {'ids': []}
        
        with pytest.raises(DocumentNotFoundError):
            vector_service.delete_document('nonexistent')
    
    def test_list_documents(self, vector_service, mock_collection):
        """Test document listing with pagination"""
        mock_collection.get.return_value = {
            'ids': ['doc1', 'doc2', 'doc3'],
            'documents': ['Content 1', 'Content 2', 'Content 3'],
            'metadatas': [
                {'created_at': datetime.utcnow().isoformat(), 'updated_at': datetime.utcnow().isoformat()},
                {'created_at': datetime.utcnow().isoformat(), 'updated_at': datetime.utcnow().isoformat()},
                {'created_at': datetime.utcnow().isoformat(), 'updated_at': datetime.utcnow().isoformat()}
            ]
        }
        
        documents, total = vector_service.list_documents(limit=2, offset=0)
        
        assert len(documents) == 2
        assert total == 3
    
    def test_query_documents(self, vector_service, mock_collection):
        """Test document querying"""
        mock_collection.query.return_value = {
            'ids': [['doc1', 'doc2']],
            'documents': [['Content 1', 'Content 2']],
            'distances': [[0.1, 0.3]],
            'metadatas': [[{'category': 'test'}, {'category': 'test'}]]
        }
        
        query = QueryRequest(query_text="test query", n_results=2)
        result = vector_service.query_documents(query)
        
        assert len(result.ids) == 2
        assert len(result.documents) == 2
        assert len(result.distances) == 2
        mock_collection.query.assert_called_once()
    
    def test_create_documents_batch(self, vector_service, sample_documents, mock_collection):
        """Test batch document creation"""
        mock_collection.get.return_value = {'ids': []}
        
        results = vector_service.create_documents_batch(sample_documents[:3])
        
        assert len(results) == 3
        assert all(r['status'] == 'success' for r in results)
    
    def test_delete_all_documents(self, vector_service, mock_collection):
        """Test deleting all documents"""
        mock_collection.get.return_value = {
            'ids': ['doc1', 'doc2', 'doc3']
        }
        
        result = vector_service.delete_all_documents()
        
        assert result['status'] == 'success'
        assert 'Deleted 3 documents' in result['message']
        mock_collection.delete.assert_called_once_with(ids=['doc1', 'doc2', 'doc3'])