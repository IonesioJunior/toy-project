from unittest.mock import patch

from fastapi import status

from src.app.utils.exceptions import DocumentAlreadyExistsError, DocumentNotFoundError


class TestDocumentRoutes:
    """Test cases for document API routes"""

    def test_create_document_success(
        self, client, sample_document, mock_vector_service
    ):
        """Test successful document creation"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.post(
                "/api/v1/documents", json=sample_document.model_dump()
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == sample_document.id
            assert data["status"] == "success"
            assert "message" in data

    def test_create_document_already_exists(
        self, client, sample_document, mock_vector_service
    ):
        """Test document creation when document already exists"""
        mock_vector_service.create_document.side_effect = DocumentAlreadyExistsError(
            sample_document.id
        )

        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.post(
                "/api/v1/documents", json=sample_document.model_dump()
            )

            assert response.status_code == status.HTTP_409_CONFLICT

    def test_get_document_success(self, client, mock_vector_service):
        """Test successful document retrieval"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.get("/api/v1/documents/test_doc_1")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "test_doc_1"
            assert "content" in data
            assert "metadata" in data

    def test_get_document_not_found(self, client, mock_vector_service):
        """Test document retrieval when document doesn't exist"""
        mock_vector_service.get_document.side_effect = DocumentNotFoundError(
            "nonexistent"
        )

        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.get("/api/v1/documents/nonexistent")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_document_success(self, client, mock_vector_service):
        """Test successful document update"""
        update_data = {"content": "Updated content", "metadata": {"updated": True}}

        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.put("/api/v1/documents/test_doc_1", json=update_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "test_doc_1"
            assert data["status"] == "success"

    def test_delete_document_success(self, client, mock_vector_service):
        """Test successful document deletion"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.delete("/api/v1/documents/test_doc_1")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "test_doc_1"
            assert data["status"] == "success"

    def test_list_documents(self, client, mock_vector_service):
        """Test document listing with pagination"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.get("/api/v1/documents?limit=10&offset=0")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "documents" in data
            assert "total" in data
            assert data["limit"] == 10
            assert data["offset"] == 0

    def test_search_documents(self, client, mock_vector_service):
        """Test document search"""
        search_query = {"query_text": "artificial intelligence", "n_results": 5}

        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.post("/api/v1/documents/search", json=search_query)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "documents" in data
            assert "ids" in data
            assert "distances" in data
            assert "metadatas" in data

    def test_batch_create_documents(
        self, client, sample_documents, mock_vector_service
    ):
        """Test batch document creation"""
        batch_data = {"documents": [doc.model_dump() for doc in sample_documents[:3]]}

        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.post("/api/v1/documents/batch", json=batch_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert "successful" in data
            assert "failed" in data

    def test_delete_all_documents_without_confirmation(
        self, client, mock_vector_service
    ):
        """Test delete all documents without confirmation"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.delete("/api/v1/documents")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_all_documents_with_confirmation(self, client, mock_vector_service):
        """Test delete all documents with confirmation"""
        with patch(
            "src.app.routes.documents.VectorService", return_value=mock_vector_service
        ):
            response = client.delete("/api/v1/documents?confirm=true")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
