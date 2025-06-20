from fastapi import status


class TestIntegration:
    """Integration tests for the API."""

    def test_multiple_endpoint_calls(self, client):
        """Test making multiple calls to different endpoints."""
        # First call root
        response1 = client.get("/")
        assert response1.status_code == status.HTTP_200_OK

        # Then call hello endpoint
        response2 = client.get("/hello/IntegrationTest")
        assert response2.status_code == status.HTTP_200_OK
        assert "IntegrationTest" in response2.json()["message"]

    def test_invalid_endpoint(self, client):
        """Test that invalid endpoints return 404."""
        response = client.get("/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_api_consistency(self, client):
        """Test that API responses are consistent across multiple calls."""
        responses = []
        for _ in range(3):
            response = client.get("/hello/test")
            responses.append(response.json())

        # All responses should be identical
        assert all(r == responses[0] for r in responses)
