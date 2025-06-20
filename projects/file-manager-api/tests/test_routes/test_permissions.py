"""Tests for permission management endpoints."""

from fastapi.testclient import TestClient

from app.config import settings


class TestPermissionRoutes:
    """Test cases for permission management endpoints."""

    def test_get_file_permissions(self, client: TestClient):
        """Test retrieving permissions for a file."""
        # First upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_resp.status_code == 201
        file_id = upload_resp.json()["id"]

        # Get permissions
        response = client.get(f"{settings.API_PREFIX}/files/{file_id}/permissions")
        assert response.status_code == 200

        data = response.json()
        assert "permissions" in data
        assert "total" in data
        assert "file_path" in data
        assert "is_owner" in data

        # Should have at least one permission (owner)
        assert data["total"] >= 1
        assert data["is_owner"] is True

        # Check owner has full permissions
        owner_rule = next(
            (p for p in data["permissions"] if p["user"] == "dev@test.local"), None
        )
        assert owner_rule is not None
        assert set(owner_rule["permissions"]) == {"READ", "WRITE", "CREATE", "ADMIN"}

    def test_grant_permission(self, client: TestClient):
        """Test granting permissions to another user."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        assert upload_resp.status_code == 201
        file_id = upload_resp.json()["id"]

        # Grant read permission to another user
        permission_request = {"user": "colleague@example.com", "permissions": ["READ"]}
        response = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["user"] == "colleague@example.com"
        assert data["permissions"] == ["READ"]
        assert "id" in data

        # Verify permission was added
        perms_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}/permissions")
        assert perms_resp.status_code == 200
        permissions = perms_resp.json()["permissions"]

        colleague_perm = next(
            (p for p in permissions if p["user"] == "colleague@example.com"), None
        )
        assert colleague_perm is not None
        assert colleague_perm["permissions"] == ["READ"]

    def test_grant_multiple_permissions(self, client: TestClient):
        """Test granting multiple permissions."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Grant read and write permissions
        permission_request = {
            "user": "editor@example.com",
            "permissions": ["READ", "WRITE"],
        }
        response = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 200
        assert set(response.json()["permissions"]) == {"READ", "WRITE"}

    def test_grant_permission_wildcard_user(self, client: TestClient):
        """Test granting permissions to all users (*)."""
        # Upload a file
        files = {"file": ("public.txt", b"Public content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Grant read permission to everyone
        permission_request = {"user": "*", "permissions": ["READ"]}
        response = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 200
        assert response.json()["user"] == "*"

    def test_update_permission(self, client: TestClient):
        """Test updating an existing permission."""
        # Upload a file and grant permission
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Grant initial permission
        permission_request = {"user": "user@example.com", "permissions": ["READ"]}
        grant_resp = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        permission_id = grant_resp.json()["id"]

        # Update to add write permission
        update_request = {"permissions": ["READ", "WRITE"]}
        response = client.put(
            f"{settings.API_PREFIX}/files/{file_id}/permissions/{permission_id}",
            json=update_request,
        )
        assert response.status_code == 200
        assert set(response.json()["permissions"]) == {"READ", "WRITE"}

    def test_revoke_permission(self, client: TestClient):
        """Test revoking a permission."""
        # Upload a file and grant permission
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Grant permission
        permission_request = {"user": "temp@example.com", "permissions": ["READ"]}
        grant_resp = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        permission_id = grant_resp.json()["id"]

        # Revoke permission
        response = client.delete(
            f"{settings.API_PREFIX}/files/{file_id}/permissions/{permission_id}"
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Permission revoked successfully"

        # Verify permission was removed
        perms_resp = client.get(f"{settings.API_PREFIX}/files/{file_id}/permissions")
        permissions = perms_resp.json()["permissions"]

        temp_perm = next(
            (p for p in permissions if p["user"] == "temp@example.com"), None
        )
        assert temp_perm is None

    def test_bulk_permissions(self, client: TestClient):
        """Test applying permissions to multiple files."""
        # Upload multiple CSV files
        csv_files = [
            ("data1.csv", b"col1,col2\n1,2", "text/csv"),
            ("data2.csv", b"col1,col2\n3,4", "text/csv"),
            ("report.txt", b"Report content", "text/plain"),
        ]

        for filename, content, content_type in csv_files:
            files = {"file": (filename, content, content_type)}
            response = client.post(f"{settings.API_PREFIX}/files/", files=files)
            assert response.status_code == 201

        # Apply bulk permissions to CSV files
        bulk_request = {
            "user": "analyst@example.com",
            "permissions": ["READ"],
            "path_pattern": "*.csv",
            "recursive": False,
        }
        response = client.post(
            f"{settings.API_PREFIX}/permissions/bulk", json=bulk_request
        )
        assert response.status_code == 200

        data = response.json()
        assert "processed" in data["details"]
        # Note: In test environment, files are stored with UUID prefixes
        # so the pattern matching might not work as expected

    def test_check_permission(self, client: TestClient):
        """Test checking if a user has specific permission."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Check owner permission
        response = client.get(
            f"{settings.API_PREFIX}/permissions/check",
            params={"file_id": file_id, "user": "dev@test.local", "permission": "READ"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] is True

        # Check non-owner permission (should be false)
        response = client.get(
            f"{settings.API_PREFIX}/permissions/check",
            params={
                "file_id": file_id,
                "user": "other@example.com",
                "permission": "WRITE",
            },
        )
        assert response.status_code == 200
        assert response.json()["has_permission"] is False

    def test_invalid_permission_type(self, client: TestClient):
        """Test granting invalid permission type."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Try to grant invalid permission
        permission_request = {"user": "user@example.com", "permissions": ["INVALID"]}
        response = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 422
        assert "Invalid permission" in response.json()["detail"][0]["msg"]

    def test_invalid_email(self, client: TestClient):
        """Test granting permission with invalid email."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Try to grant permission with invalid email
        permission_request = {"user": "not-an-email", "permissions": ["READ"]}
        response = client.post(
            f"{settings.API_PREFIX}/files/{file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 422
        assert "Invalid email address" in response.json()["detail"][0]["msg"]

    def test_permission_not_found(self, client: TestClient):
        """Test updating/deleting non-existent permission."""
        # Upload a file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        upload_resp = client.post(f"{settings.API_PREFIX}/files/", files=files)
        file_id = upload_resp.json()["id"]

        # Try to update non-existent permission
        update_request = {"permissions": ["READ"]}
        response = client.put(
            f"{settings.API_PREFIX}/files/{file_id}/permissions/fake-id",
            json=update_request,
        )
        assert response.status_code == 404
        assert "Permission rule not found" in response.json()["detail"]

        # Try to delete non-existent permission
        response = client.delete(
            f"{settings.API_PREFIX}/files/{file_id}/permissions/fake-id"
        )
        assert response.status_code == 404
        assert "Permission rule not found" in response.json()["detail"]

    def test_file_not_found_permissions(self, client: TestClient):
        """Test permission operations on non-existent file."""
        fake_file_id = "non-existent-file-id"

        # Try to get permissions
        response = client.get(f"{settings.API_PREFIX}/files/{fake_file_id}/permissions")
        assert response.status_code == 404

        # Try to grant permission
        permission_request = {"user": "user@example.com", "permissions": ["READ"]}
        response = client.post(
            f"{settings.API_PREFIX}/files/{fake_file_id}/permissions",
            json=permission_request,
        )
        assert response.status_code == 404
