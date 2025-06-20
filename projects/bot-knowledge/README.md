# FastAPI ChromaDB Vector Database API

A production-ready FastAPI application that provides CRUD endpoints for managing documents in a ChromaDB vector database.

## Overview

This project implements a RESTful API for document management using ChromaDB as the vector database backend. It supports full CRUD operations, vector similarity search, batch operations, and persistent storage.

## Features

- **Full CRUD Operations**: Create, Read, Update, and Delete documents
- **Vector Search**: Query documents by semantic similarity
- **Batch Operations**: Create multiple documents in a single request
- **Persistent Storage**: Data persists across application restarts
- **Pagination**: Efficient handling of large datasets
- **Type Safety**: Full Pydantic model validation
- **Auto Documentation**: Interactive API docs via Swagger UI and ReDoc
- **Docker Support**: Ready for containerized deployment
- **Comprehensive Testing**: Unit and integration tests included

## Prerequisites

- Python 3.13+
- Dependencies listed in `pyproject.toml`

## Quick Start

### Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the application
python -m src.main

# Or use uvicorn directly
uvicorn src.app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Using Docker

```bash
# From the project directory
# Build and run development container
docker build -f Dockerfile -t fastapi-chromadb .
docker run -p 8000:8000 -v $(pwd)/chroma_db:/app/chroma_db fastapi-chromadb

# Production build
docker build -f Dockerfile.prod -t fastapi-chromadb:prod .
docker run -p 8000:8000 -v $(pwd)/chroma_db:/app/chroma_db fastapi-chromadb:prod

# Or use docker-compose from infrastructure directory
cd ../../infrastructure/docker
docker-compose up bot-knowledge-dev
```

## Project Structure

```
bot-knowledge/
├── Dockerfile             # Development Dockerfile
├── Dockerfile.prod        # Production Dockerfile
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py       # FastAPI application
│   │   ├── config.py     # Configuration settings
│   │   ├── database.py   # ChromaDB client
│   │   ├── models/       # Pydantic models
│   │   │   └── document.py
│   │   ├── routes/       # API endpoints
│   │   │   ├── documents.py
│   │   │   └── health.py
│   │   ├── services/     # Business logic
│   │   │   └── vector_service.py
│   │   └── utils/        # Utilities
│   │       └── exceptions.py
│   └── main.py          # Entry point
├── tests/
│   ├── conftest.py      # Test fixtures
│   ├── test_routes/     # Route tests
│   └── test_services/   # Service tests
└── pyproject.toml       # Project dependencies
```

## API Endpoints

### Health Check
- `GET /health` - Health status of the API and dependencies
- `GET /ready` - Readiness check

### Document Operations
- `POST /api/v1/documents` - Create a new document
- `GET /api/v1/documents/{id}` - Get document by ID
- `PUT /api/v1/documents/{id}` - Update document
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents` - List documents (paginated)
- `POST /api/v1/documents/search` - Vector similarity search
- `POST /api/v1/documents/batch` - Batch create documents
- `DELETE /api/v1/documents?confirm=true` - Delete all documents

## Usage Examples

### Create a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "doc_001",
    "content": "This is a document about artificial intelligence and machine learning.",
    "metadata": {
      "category": "technology",
      "author": "John Doe",
      "tags": ["AI", "ML", "tech"]
    }
  }'
```

### Search Documents
```bash
curl -X POST "http://localhost:8000/api/v1/documents/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "neural networks and deep learning",
    "n_results": 5,
    "metadata_filter": {"category": "technology"}
  }'
```

### List Documents with Pagination
```bash
curl "http://localhost:8000/api/v1/documents?limit=10&offset=0"
```

## Configuration

Environment variables can be set via `.env` file:

```env
# Application settings
APP_NAME=FastAPI ChromaDB API
APP_VERSION=1.0.0
DEBUG_MODE=false

# ChromaDB settings
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=documents

# API settings
API_PREFIX=/api/v1
MAX_PAGE_SIZE=100
DEFAULT_PAGE_SIZE=10

# Server settings
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_routes/test_documents.py
```

### Code Quality
```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/ tests/
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

## Performance Considerations

- ChromaDB uses efficient vector indexing for fast similarity search
- Pagination is implemented to handle large datasets
- Batch operations reduce overhead for bulk document creation
- Persistent storage ensures data durability

## Security Notes

- CORS is configured (customize `cors_allowed_origins` for production)
- Input validation via Pydantic models
- Error messages don't expose sensitive information
- Production Docker image runs as non-root user

## Contributing

Please refer to the main repository's contributing guidelines.

## License

See the main repository's license file.