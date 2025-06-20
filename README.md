# File Management API

A FastAPI-based file management system integrated with SyftBox for secure file storage and sharing.

## Overview

The File Management API provides a comprehensive solution for handling file operations with built-in validation and error handling. Key features include:

- 🚀 RESTful API design
- 📁 Secure file storage with UUID-based naming
- 🔒 Path traversal protection
- 📏 File size (10MB limit) and type validation
- 📊 Storage statistics and monitoring
- 🔄 File CRUD operations (Create, Read, Update, Delete)
- 🌐 SyftBox integration with syft:// URL support
- 📂 Datasite-based storage for decentralized file management

## Prerequisites

### SyftBox Configuration (Required for Production)
1. Install SyftBox: `pip install syft-core`
2. Initialize SyftBox: `syftbox init`
3. Verify configuration: `syftbox status`

The application will not start in production without proper SyftBox configuration.

## Quick Start

### Development Mode
```bash
# Set development environment
export APP_ENV=development

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev,test]"

# Run the application
python -m uvicorn app.main:app --reload
```

### Production Mode
```bash
# Ensure SyftBox is configured first
python -m uvicorn app.main:app --reload
```

### Using Docker
```bash
# Development
docker-compose up app-dev

# Production
docker-compose up app-prod

# Run tests
docker-compose up test
```

The API will be available at:
- Local: `http://localhost:8000`
- Docker Dev: `http://localhost:8001`

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### Key Endpoints

#### File Management
- `POST /api/files/` - Upload a file
- `GET /api/files/` - List all files
- `GET /api/files/{file_id}` - Download a file
- `PUT /api/files/{file_id}` - Update a file
- `DELETE /api/files/{file_id}` - Delete a file
- `GET /api/files/stats/summary` - Get storage statistics

#### System
- `GET /` - Health check
- `GET /health` - Service health with SyftBox status

### Example Usage

```bash
# Upload file
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/files/

# List files
curl http://localhost:8000/api/files/ | jq

# Download file
curl -O -J http://localhost:8000/api/files/{file_id}

# Update file
curl -X PUT -F "file=@new_version.pdf" http://localhost:8000/api/files/{file_id}

# Delete file
curl -X DELETE http://localhost:8000/api/files/{file_id}

# Get storage stats
curl http://localhost:8000/api/files/stats/summary | jq
```

## Configuration

### Environment Modes
- **production** (default): Requires real SyftBox configuration
- **development**: Uses mock SyftBox for local development
- **testing**: Uses mock SyftBox for automated tests

Set via `APP_ENV` environment variable:
```bash
export APP_ENV=development
```

### File Constraints
- **Max File Size**: 10MB (10,485,760 bytes)
- **Allowed Extensions**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.pdf`, `.txt`, `.doc`, `.docx`, `.csv`, `.xlsx`, `.xls`
- **Allowed MIME Types**: Corresponding to the allowed extensions

### Storage Paths

#### With SyftBox (Production)
```
~/.syftbox/datasites/{user_email}/apis/file_management/
├── storage/        # Actual files
└── metadata/       # File metadata in JSON format
```

#### Without SyftBox (Development)
```
/tmp/syftbox_mock/datasites/{mock_email}/apis/file_management/
├── storage/
└── metadata/
```

## Project Structure

```
toy_project/
├── app/
│   ├── config.py          # Environment-aware configuration
│   ├── main.py            # FastAPI application
│   ├── models/            # Pydantic models
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── test/
│   ├── conftest.py        # Test fixtures
│   └── test_*.py          # Test files
├── docker-compose.yml     # Docker services
├── Dockerfile            # Multi-stage Dockerfile
├── pyproject.toml        # Project dependencies
└── justfile              # Task automation
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest test/test_syft_core_mandatory.py -v
```

### Code Quality
```bash
# Type checking
mypy app/

# Linting
ruff check app/

# Formatting
black app/ test/
```

### Common Development Tasks

Using the `justfile`:
```bash
# List available commands
just

# Run development server
just dev

# Run tests
just test

# Format code
just format

# Lint code
just lint
```

## SyftBox Integration

### What is SyftBox?
SyftBox is a decentralized data storage and sharing platform that enables secure, privacy-preserving data collaboration. When integrated with the File Management API, it provides:

- **Decentralized Storage**: Files are stored in user-specific datasites
- **Unique URLs**: Each file gets a syft:// URL for ecosystem-wide referencing
- **Privacy Control**: Files are isolated per user/organization
- **Interoperability**: Files can be accessed by other SyftBox applications

### Syft URLs
Every file uploaded when SyftBox is enabled receives a unique syft:// URL:
```
syft://user@example.com/apis/file_management/storage/{uuid}_{filename}
```

## Security Considerations

### Implemented Security Measures
1. **Path Traversal Protection**: Filenames are sanitized to remove path components
2. **File Type Validation**: Both MIME type and extension are checked
3. **Size Limits**: Enforced file size limits prevent DoS attacks
4. **Filename Sanitization**: Unicode normalization and special character removal

### Recommended Additional Security
- Add authentication & authorization
- Implement rate limiting
- Integrate virus scanning
- Enable encryption at rest

## API Response Models

### FileUploadResponse
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "message": "File uploaded successfully",
  "syft_url": "syft://user@example.com/apis/file_management/storage/550e8400-e29b-41d4-a716-446655440000_document.pdf"
}
```

### FileListResponse
```json
{
  "files": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "document.pdf",
      "size": 245632,
      "mime_type": "application/pdf",
      "upload_date": "2024-01-15T10:30:00.000Z",
      "syft_url": "syft://..."
    }
  ],
  "total": 1
}
```

### StorageStats
```json
{
  "total_files": 15,
  "total_size": 5242880,
  "max_file_size": 10485760,
  "storage_path": "/home/user/.syftbox/datasites/user@example.com/apis/file_management/storage"
}
```

## Troubleshooting

### Common Issues

1. **"File type not allowed" error**
   - Check if file extension is in allowed list
   - Verify MIME type is supported

2. **"File too large" error**
   - Default limit is 10MB
   - Check available disk space

3. **SyftBox Not Configured**
   - Ensure syft-core is installed: `pip install syft-core`
   - Configure SyftBox: `syftbox init`
   - Verify configuration: `syftbox status`

4. **Container Won't Start**
   - Check Docker logs: `docker-compose logs app-dev`
   - Verify environment variable: `docker-compose exec app-dev env | grep APP_ENV`
   - Rebuild if needed: `docker-compose build app-dev`

## License

[Your License Here]