import pytest
from fastapi import status


class TestRootEndpoint:
    """Test cases for the root endpoint."""

    def test_read_root(self, client):
        """Test that root endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_root_response_content(self, client):
        """Test that root endpoint returns HTML with expected content."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        # Check that it's HTML
        assert "text/html" in response.headers["content-type"]
        # Could check for specific content if needed
        html_content = response.text
        assert html_content  # Ensure it's not empty


class TestHelloEndpoint:
    """Test cases for the hello endpoint."""

    def test_hello_with_name(self, client):
        """Test hello endpoint with a valid name."""
        name = "Alice"
        response = client.get(f"/hello/{name}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": f"Hello, {name}!"}

    def test_hello_with_special_characters(self, client):
        """Test hello endpoint with special characters in name."""
        name = "John-Doe"
        response = client.get(f"/hello/{name}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": f"Hello, {name}!"}

    def test_hello_with_numbers(self, client):
        """Test hello endpoint with numbers in name."""
        name = "User123"
        response = client.get(f"/hello/{name}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": f"Hello, {name}!"}

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Bob", "Hello, Bob!"),
            ("Jane", "Hello, Jane!"),
            ("Test", "Hello, Test!"),
        ],
    )
    def test_hello_multiple_names(self, client, name, expected):
        """Test hello endpoint with multiple different names."""
        response = client.get(f"/hello/{name}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": expected}
