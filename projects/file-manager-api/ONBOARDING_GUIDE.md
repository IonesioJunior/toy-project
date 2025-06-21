# File Manager API - Complete Onboarding Guide

## Table of Contents
1. [Introduction & Overview](#introduction--overview)
2. [Core Concepts](#core-concepts)
3. [Technical Architecture](#technical-architecture)
4. [API Reference Guide](#api-reference-guide)
5. [SyftBox Integration Deep Dive](#syftbox-integration-deep-dive)
6. [Permission System](#permission-system)
7. [Development Workflow](#development-workflow)
8. [Code Examples & Tutorials](#code-examples--tutorials)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. Introduction & Overview

### What is the File Manager API?

The File Manager API is a **FastAPI-based RESTful service** that provides secure file storage and management capabilities with integrated **SyftBox** support for decentralized data sharing. Think of it as a smart file storage system that not only stores files but also manages who can access them in a decentralized manner.

### Key Features

- 🚀 **RESTful API Design**: Clean, intuitive endpoints for all file operations
- 📁 **Secure File Storage**: UUID-based naming prevents conflicts and enhances security
- 🔒 **Advanced Security**: Path traversal protection, file type validation, size limits
- 📊 **Monitoring**: Built-in storage statistics and file tracking
- 🔄 **Full CRUD Operations**: Create, Read, Update, Delete files with ease
- 🌐 **SyftBox Integration**: Unique `syft://` URLs for decentralized file sharing
- 📂 **Datasite Storage**: User-specific isolated storage areas
- 🔐 **Permission Management**: Fine-grained access control with SyftBox permissions

### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Client App    │────▶│  FastAPI Server │────▶│   SyftBox       │
│                 │     │                 │     │   Integration   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────┐          ┌─────────────┐
                        │   Routes    │          │  Datasites  │
                        │  (Files &   │          │   Storage   │
                        │Permissions) │          └─────────────┘
                        └─────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Services   │
                        │   Layer     │
                        └─────────────┘
                               │
                        ┌──────┴──────┐
                        ▼             ▼
                  ┌──────────┐  ┌──────────┐
                  │   File    │  │Permission│
                  │  Storage  │  │  System  │
                  └──────────┘  └──────────┘
```

---

## 2. Core Concepts

### 2.1 SyftBox Integration

**SyftBox** is a decentralized data storage and sharing platform that enables:
- **Privacy-preserving collaboration**: Files are stored in user-specific datasites
- **Decentralized architecture**: No central server holds all data
- **Unique identification**: Every file gets a `syft://` URL for ecosystem-wide access

### 2.2 Decentralized Storage Model

Files are organized in a hierarchical structure:

```
~/.syftbox/datasites/
└── user@example.com/           # User's datasite
    └── apis/
        └── file_management/
            ├── storage/        # Actual files
            │   └── {uuid}_{filename}
            └── metadata/       # File metadata
                └── {uuid}.json
```

### 2.3 File Lifecycle

1. **Upload**: File is validated → Assigned UUID → Stored with metadata → Syft URL generated
2. **Access**: Request with file ID → Load metadata → Locate file → Serve with proper headers
3. **Update**: Validate new file → Replace old file → Update metadata → Generate new Syft URL
4. **Delete**: Remove file from storage → Delete metadata → Clean up permissions

### 2.4 Permission Model

Permissions follow a **rule-based system**:
- **READ**: View and download files
- **WRITE**: Modify existing files
- **CREATE**: Add new files (for directories)
- **ADMIN**: Full control including permission management

---

## 3. Technical Architecture

### 3.1 Project Structure

```
file-manager-api/
├── src/app/
│   ├── config.py          # Environment configuration & SyftBox setup
│   ├── main.py           # FastAPI application entry point
│   ├── models/           # Pydantic data models
│   │   ├── file.py       # File-related models
│   │   └── permissions.py # Permission models
│   ├── routes/           # API endpoint definitions
│   │   ├── files.py      # File management endpoints
│   │   └── permissions.py # Permission endpoints
│   ├── services/         # Business logic layer
│   │   ├── file_service.py      # File operations
│   │   └── permission_service.py # Permission management
│   └── utils/            # Helper functions
│       └── file_utils.py # File validation & sanitization
├── tests/                # Comprehensive test suite
└── pyproject.toml       # Project dependencies
```

### 3.2 Key Components

#### Configuration (`config.py`)
- Manages environment modes (production/development/testing)
- Initializes SyftBox client or mock client based on environment
- Defines file constraints (size limits, allowed types)

#### Models Layer
- **FileMetadata**: Core file information with Syft URL
- **PermissionRequest/Response**: Permission management DTOs
- **FileListItem**: Enhanced file info with ownership data

#### Routes Layer
- **Files Router**: Handles all file CRUD operations
- **Permissions Router**: Manages access control

#### Services Layer
- **FileService**: Core file operations logic
- **PermissionService**: SyftBox permission integration

### 3.3 Data Flow Example

```
Client Request → FastAPI Route → Service Layer → Storage/SyftBox
                                       ↓
Client Response ← Route Handler ← Service Response
```

---

## 4. API Reference Guide

### 4.1 File Management Endpoints

#### Upload File
```http
POST /api/files/
Content-Type: multipart/form-data

Form Data:
- file: binary file data

Response: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "message": "File uploaded successfully",
  "syft_url": "syft://user@example.com/apis/file_management/storage/550e8400_document.pdf"
}
```

#### List Files
```http
GET /api/files/

Response: 200 OK
{
  "files": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "document.pdf",
      "size": 245632,
      "mime_type": "application/pdf",
      "upload_date": "2024-01-15T10:30:00Z",
      "syft_url": "syft://...",
      "is_owner": true,
      "shared_with": ["alice@example.com"]
    }
  ],
  "total": 1
}
```

#### Download File
```http
GET /api/files/{file_id}

Response: 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="document.pdf"
[Binary file data]
```

#### Update File
```http
PUT /api/files/{file_id}
Content-Type: multipart/form-data

Form Data:
- file: new binary file data

Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "updated_document.pdf",
  "message": "File updated successfully",
  "syft_url": "syft://..."
}
```

#### Delete File
```http
DELETE /api/files/{file_id}

Response: 200 OK
{
  "message": "File deleted successfully"
}
```

#### Storage Statistics
```http
GET /api/files/stats/summary

Response: 200 OK
{
  "total_files": 15,
  "total_size": 5242880,
  "max_file_size": 10485760,
  "storage_path": "/home/user/.syftbox/datasites/user@example.com/apis/file_management/storage"
}
```

### 4.2 Permission Management Endpoints

#### Get File Permissions
```http
GET /api/files/{file_id}/permissions

Response: 200 OK
{
  "permissions": [
    {
      "id": "perm-123",
      "user": "alice@example.com",
      "path": "document.pdf",
      "permissions": ["READ"],
      "allow": true,
      "priority": 0,
      "created_date": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "file_path": "/path/to/file",
  "is_owner": true
}
```

#### Grant Permission
```http
POST /api/files/{file_id}/permissions
Content-Type: application/json

{
  "user": "alice@example.com",
  "permissions": ["READ", "WRITE"],
  "path_pattern": null
}

Response: 200 OK
{
  "id": "perm-456",
  "user": "alice@example.com",
  "path": "document.pdf",
  "permissions": ["READ", "WRITE"],
  "allow": true,
  "priority": 0
}
```

#### Bulk Permissions
```http
POST /api/permissions/bulk
Content-Type: application/json

{
  "user": "team@example.com",
  "permissions": ["READ"],
  "path_pattern": "*.csv",
  "recursive": false
}

Response: 200 OK
{
  "message": "Bulk permissions applied to 5 paths",
  "details": {
    "processed": 5,
    "failed": 0,
    "paths": ["file1.csv", "file2.csv", ...]
  }
}
```

### 4.3 Error Responses

All endpoints follow a consistent error format:

```json
{
  "detail": "Descriptive error message",
  "status_code": 404
}
```

Common status codes:
- `400`: Bad Request (invalid input)
- `403`: Forbidden (permission denied)
- `404`: Not Found
- `413`: Payload Too Large
- `415`: Unsupported Media Type
- `500`: Internal Server Error

---

## 5. SyftBox Integration Deep Dive

### 5.1 What is SyftBox?

SyftBox is a **decentralized data platform** that enables:
- **Secure data sharing** without centralized control
- **Privacy-preserving collaboration** across organizations
- **Unique addressing** through syft:// URLs

### 5.2 Syft URLs Explained

Format: `syft://user@example.com/apis/file_management/storage/{uuid}_{filename}`

Components:
- **Protocol**: `syft://` identifies SyftBox resources
- **User Identity**: Email of the datasite owner
- **Path**: Location within the datasite
- **File Identifier**: UUID + original filename

### 5.3 Datasite Structure

```
~/.syftbox/
├── config.json           # SyftBox configuration
└── datasites/
    └── user@example.com/ # User's datasite
        ├── app_data/     # Application-specific data
        │   └── file_management/
        │       ├── storage/
        │       └── metadata/
        └── .syftperm     # Permission rules
```

### 5.4 Environment Configuration

#### Production Mode
```bash
# Requires real SyftBox installation
export APP_ENV=production
syftbox init  # Initialize SyftBox
python -m uvicorn src.app.main:app
```

#### Development Mode
```bash
# Uses mock SyftBox client
export APP_ENV=development
python -m uvicorn src.app.main:app --reload
```

#### Testing Mode
```bash
# Automated test environment
export APP_ENV=testing
pytest
```

---

## 6. Permission System

### 6.1 How Permissions Work

The permission system uses **`.syftperm` files** stored alongside resources:

```json
{
  "rules": [
    {
      "id": "rule-123",
      "user": "alice@example.com",
      "path": "*",
      "permissions": ["READ", "WRITE"],
      "allow": true,
      "priority": 0,
      "created_date": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 6.2 Permission Types

1. **READ**: 
   - View file metadata
   - Download file content
   - List files (if applied to directory)

2. **WRITE**:
   - Modify existing files
   - Update file metadata
   - Cannot create new files

3. **CREATE**:
   - Add new files to directories
   - Typically combined with WRITE

4. **ADMIN**:
   - All above permissions
   - Manage other users' permissions
   - Delete files

### 6.3 Permission Resolution

Rules are evaluated in order:
1. Check user-specific rules first
2. Check wildcard rules (`user: "*"`)
3. Higher priority rules override lower ones
4. Owner always has implicit ADMIN access

### 6.4 Bulk Operations

Apply permissions to multiple files using patterns:
- `*.pdf` - All PDF files
- `reports/*.xlsx` - Excel files in reports folder
- `**/*.txt` - All text files recursively (with `recursive: true`)

---

## 7. Development Workflow

### 7.1 Setting Up Development Environment

#### Prerequisites
```bash
# Python 3.13+
python --version

# Install dependencies
pip install -e ".[dev,test]"

# For production mode only
pip install syft-core
```

#### Environment Setup
```bash
# Create .env file
cat > .env << EOF
APP_ENV=development
MAX_FILE_SIZE=10485760
EOF
```

### 7.2 Running the Application

#### Development Mode
```bash
# With auto-reload
export APP_ENV=development
python -m uvicorn src.app.main:app --reload --port 8000
```

#### Using Docker
```bash
# Development container
docker-compose -f ../../infrastructure/docker/docker-compose.yml up file-manager-api-dev

# Access at http://localhost:8001
```

### 7.3 Testing Strategy

#### Unit Tests
```bash
# Run specific test file
pytest tests/test_services/test_file_service.py -v

# Run with coverage
pytest --cov=src.app --cov-report=html
```

#### Integration Tests
```bash
# Run integration tests
pytest -m integration

# Test with real SyftBox
export APP_ENV=production
pytest tests/test_integration_syft_core.py
```

### 7.4 Debugging Tips

1. **Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Check File Paths**:
```python
from app.config import FILE_STORAGE_PATH, METADATA_PATH
print(f"Storage: {FILE_STORAGE_PATH}")
print(f"Metadata: {METADATA_PATH}")
```

3. **Verify SyftBox Status**:
```bash
syftbox status  # Check SyftBox configuration
ls ~/.syftbox/datasites/  # List available datasites
```

4. **Common Issues**:
- File not found: Check UUID in metadata matches storage
- Permission denied: Verify .syftperm file exists and is valid JSON
- SyftBox errors: Ensure `syftbox init` was run successfully

---

## 8. Code Examples & Tutorials

### 8.1 Basic File Upload

```python
import httpx

# Upload a file
with open("report.pdf", "rb") as f:
    files = {"file": ("report.pdf", f, "application/pdf")}
    response = httpx.post("http://localhost:8000/api/files/", files=files)
    
file_data = response.json()
file_id = file_data["id"]
syft_url = file_data["syft_url"]
print(f"File uploaded: {file_id}")
print(f"Syft URL: {syft_url}")
```

### 8.2 Managing Permissions

```python
# Grant read access to a colleague
permission_data = {
    "user": "colleague@example.com",
    "permissions": ["READ"]
}

response = httpx.post(
    f"http://localhost:8000/api/files/{file_id}/permissions",
    json=permission_data
)

# Apply bulk permissions to all CSV files
bulk_data = {
    "user": "analytics-team@example.com",
    "permissions": ["READ"],
    "path_pattern": "*.csv",
    "recursive": False
}

response = httpx.post(
    "http://localhost:8000/api/permissions/bulk",
    json=bulk_data
)
```

### 8.3 Building a File Browser

```python
async def list_user_files(client: httpx.AsyncClient):
    """List all files with their sharing status."""
    response = await client.get("/api/files/")
    files = response.json()["files"]
    
    for file in files:
        print(f"\n📄 {file['filename']} ({file['size']} bytes)")
        print(f"   ID: {file['id']}")
        print(f"   Uploaded: {file['upload_date']}")
        print(f"   Syft URL: {file['syft_url']}")
        
        if file.get('is_owner'):
            print("   Status: You own this file")
        
        if file.get('shared_with'):
            print(f"   Shared with: {', '.join(file['shared_with'])}")
```

### 8.4 Implementing File Sync

```python
import asyncio
from pathlib import Path

async def sync_directory(local_dir: Path, api_url: str):
    """Sync local directory with file manager API."""
    async with httpx.AsyncClient(base_url=api_url) as client:
        # Get current files in API
        response = await client.get("/api/files/")
        remote_files = {f["filename"]: f["id"] for f in response.json()["files"]}
        
        # Upload new or modified files
        for file_path in local_dir.glob("*"):
            if file_path.is_file():
                if file_path.name not in remote_files:
                    # Upload new file
                    print(f"Uploading {file_path.name}...")
                    with open(file_path, "rb") as f:
                        files = {"file": (file_path.name, f, "application/octet-stream")}
                        await client.post("/api/files/", files=files)
                else:
                    # Check if update needed (simplified - could use hash)
                    print(f"File {file_path.name} already exists")
```

### 8.5 Custom Permission Validator

```python
from app.services.permission_service import PermissionService

class CustomPermissionValidator:
    """Extended permission validation with business rules."""
    
    def __init__(self, permission_service: PermissionService):
        self.service = permission_service
    
    async def can_share_file(self, file_id: str, user: str) -> bool:
        """Check if user can share the file with others."""
        # Get current permissions
        perms = await self.service.get_permissions(file_id)
        
        # Only owner or ADMIN can share
        if perms.is_owner:
            return True
            
        for rule in perms.permissions:
            if rule.user == user and "ADMIN" in rule.permissions:
                return True
                
        return False
    
    async def validate_bulk_operation(self, pattern: str, user: str) -> bool:
        """Validate bulk permission operations."""
        # Prevent overly broad patterns
        dangerous_patterns = ["*", "**/*", "/*"]
        if pattern in dangerous_patterns:
            return False
            
        # Check user quota (example business rule)
        # ... implementation ...
        
        return True
```

---

## 9. Security Considerations

### 9.1 File Validation

The system implements multiple layers of validation:

#### Size Validation
- Default limit: 10MB (configurable)
- Checked before processing to prevent DoS
- Error: HTTP 413 Payload Too Large

#### Type Validation
- Whitelist approach for MIME types and extensions
- Both must match for acceptance
- Configurable in `config.py`

#### Filename Sanitization
```python
# From file_utils.py
- Path components removed (prevents traversal)
- Unicode normalized (NFKD)
- Special characters stripped
- Length limited to 100 chars
```

### 9.2 Path Traversal Protection

Multiple safeguards:
1. `os.path.basename()` strips directory components
2. Files stored with UUID prefix
3. All paths resolved to absolute before operations
4. Storage isolated per user datasite

### 9.3 Access Control

- **Ownership verification**: Check file location within user's datasite
- **Permission checks**: Every operation validates permissions
- **Default deny**: No implicit permissions except for owner
- **Audit trail**: Permission changes tracked with timestamps

### 9.4 Best Practices

1. **Never trust user input**:
   - Always validate file types
   - Sanitize all filenames
   - Check file sizes early

2. **Use UUIDs for storage**:
   - Prevents filename conflicts
   - Makes URLs unguessable
   - Enables safe concurrent uploads

3. **Implement rate limiting** (production):
   ```python
   from fastapi_limiter import FastAPILimiter
   
   @router.post("/files/", dependencies=[Depends(RateLimiter(times=10, minutes=1))])
   ```

4. **Add virus scanning** (production):
   ```python
   # Example integration point in file_service.py
   async def scan_file(file_path: Path) -> bool:
       # Integrate with ClamAV or similar
       pass
   ```

---

## 10. Troubleshooting Guide

### 10.1 Common Issues

#### "SyftBox not configured"
**Problem**: Application won't start in production mode
**Solution**:
```bash
# Install and initialize SyftBox
pip install syft-core
syftbox init
# Follow the prompts to configure
```

#### "File not found" after upload
**Problem**: File uploads successfully but can't be downloaded
**Possible causes**:
1. Metadata/storage mismatch
2. File permissions issue
3. Incorrect file path resolution

**Debug steps**:
```python
# Check metadata exists
ls /path/to/metadata/{file_id}.json

# Verify storage file
ls /path/to/storage/{file_id}_*

# Check permissions
cat /path/to/storage/.syftperm
```

#### "Permission denied" errors
**Problem**: User can't access files they should be able to
**Debug**:
1. Verify user email matches exactly (case-sensitive)
2. Check .syftperm file is valid JSON
3. Ensure permission rule has correct format
4. Verify file ownership

### 10.2 Performance Issues

#### Slow file listings
**Optimize by**:
1. Implement pagination in list endpoint
2. Add caching for metadata
3. Index files by upload date

#### Large file uploads timeout
**Solutions**:
1. Increase timeout settings
2. Implement chunked uploads
3. Use background tasks for processing

### 10.3 Development Environment Issues

#### Mock SyftBox not working
```python
# Verify environment variable
echo $APP_ENV  # Should be "development" or "testing"

# Check mock client initialization
from app.config import syft_client
print(type(syft_client))  # Should be MockSyftClient
```

#### Tests failing with path errors
```bash
# Clean test environment
rm -rf /tmp/syftbox_mock
rm -rf /tmp/test_*

# Run tests with verbose output
pytest -vvs tests/test_services/test_file_service.py
```

### 10.4 FAQ

**Q: Can I use this without SyftBox?**
A: Yes, use development mode with `APP_ENV=development`. Production requires SyftBox.

**Q: How do I increase file size limit?**
A: Set `MAX_FILE_SIZE` in .env or environment (value in bytes).

**Q: Can I add custom file types?**
A: Yes, modify `ALLOWED_EXTENSIONS` and `ALLOWED_MIME_TYPES` in config.py.

**Q: How do I backup files?**
A: Backup the entire datasite directory: `~/.syftbox/datasites/`

**Q: Can I migrate from development to production?**
A: Yes, copy files from `/tmp/syftbox_mock` to `~/.syftbox` after proper setup.

---

## Conclusion

The File Manager API provides a robust foundation for decentralized file management. Key takeaways:

1. **SyftBox integration** enables privacy-preserving file sharing
2. **Permission system** provides fine-grained access control
3. **RESTful design** makes integration straightforward
4. **Security features** protect against common vulnerabilities
5. **Flexible architecture** supports various deployment modes

For additional help:
- Check the test files for usage examples
- Review the API documentation at `/docs` when running
- Examine the source code for implementation details

Welcome to the File Manager API project! 🚀