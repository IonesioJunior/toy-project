"""
Performance tests for the Toy Project API using Locust.
"""

import json
import random
import string

from locust import HttpUser, between, task


class ToyProjectUser(HttpUser):
    """Simulates a user interacting with the Toy Project API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a user starts."""
        # You can add any setup logic here, like authentication
        self.test_file_ids = []

    @task(3)
    def check_health(self):
        """Health check endpoint - most frequent task."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status {response.status_code}")

    @task(2)
    def get_root(self):
        """Access the root endpoint."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Root endpoint failed with status {response.status_code}")

    @task(2)
    def list_files(self):
        """List files endpoint."""
        with self.client.get("/api/files", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"List files failed with status {response.status_code}")

    @task(1)
    def upload_file(self):
        """Simulate file upload."""
        # Generate random file content
        file_content = ''.join(random.choices(string.ascii_letters + string.digits, k=1024))
        file_name = f"test_file_{random.randint(1000, 9999)}.txt"

        files = {'file': (file_name, file_content, 'text/plain')}

        with self.client.post("/api/files/upload", files=files, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'id' in data:
                        self.test_file_ids.append(data['id'])
                        response.success()
                    else:
                        response.failure("Upload response missing file ID")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response from upload")
            else:
                response.failure(f"File upload failed with status {response.status_code}")

    @task(2)
    def get_file_details(self):
        """Get details of a specific file."""
        if not self.test_file_ids:
            # If no files uploaded yet, skip this task
            return

        file_id = random.choice(self.test_file_ids)
        with self.client.get(f"/api/files/{file_id}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # File might have been deleted, remove from list
                self.test_file_ids.remove(file_id)
                response.success()  # Don't count 404 as failure in this case
            else:
                response.failure(f"Get file details failed with status {response.status_code}")

    @task(1)
    def check_permissions(self):
        """Check permissions endpoint."""
        if not self.test_file_ids:
            return

        file_id = random.choice(self.test_file_ids)
        with self.client.get(f"/api/permissions/{file_id}", catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Check permissions failed with status {response.status_code}")

    @task(1)
    def update_permissions(self):
        """Update file permissions."""
        if not self.test_file_ids:
            return

        file_id = random.choice(self.test_file_ids)
        permissions_data = {
            "read": random.choice([True, False]),
            "write": random.choice([True, False]),
            "delete": random.choice([True, False])
        }

        with self.client.put(
            f"/api/permissions/{file_id}",
            json=permissions_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Update permissions failed with status {response.status_code}")


class AdminUser(HttpUser):
    """Simulates an admin user with different behavior patterns."""

    wait_time = between(2, 5)  # Admins interact less frequently

    @task(1)
    def check_health(self):
        """Health check endpoint."""
        self.client.get("/health")

    @task(2)
    def admin_dashboard(self):
        """Simulate accessing an admin dashboard (root endpoint)."""
        self.client.get("/")

    @task(3)
    def review_all_files(self):
        """Admin reviewing all files."""
        with self.client.get("/api/files", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    files = response.json()
                    # Simulate admin checking each file
                    for file_data in files[:5]:  # Check first 5 files
                        if 'id' in file_data:
                            self.client.get(f"/api/files/{file_data['id']}")
                    response.success()
                except Exception:
                    response.failure("Failed to process files list")
            else:
                response.failure(f"List files failed with status {response.status_code}")


class APIStressTest(HttpUser):
    """Stress test specific endpoints."""

    wait_time = between(0.1, 0.5)  # Rapid fire requests

    @task(10)
    def health_spam(self):
        """Spam health endpoint."""
        self.client.get("/health")

    @task(5)
    def list_files_rapid(self):
        """Rapid file listing."""
        self.client.get("/api/files")

    @task(1)
    def upload_large_file(self):
        """Upload larger files for stress testing."""
        # Generate 10KB file
        file_content = ''.join(random.choices(string.ascii_letters + string.digits, k=10240))
        file_name = f"stress_test_{random.randint(1000, 9999)}.txt"

        files = {'file': (file_name, file_content, 'text/plain')}
        self.client.post("/api/files/upload", files=files)
