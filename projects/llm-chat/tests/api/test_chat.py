import json
from unittest.mock import AsyncMock, patch


class TestChatAPI:
    @patch("src.api.routes.chat.chat_service")
    def test_chat_endpoint_streaming(self, mock_chat_service, client):
        """Test chat endpoint with streaming response."""
        # Mock the chat service
        mock_session = AsyncMock()
        mock_session.session_id = "test-session-123"
        mock_chat_service.get_or_create_session = AsyncMock(return_value=mock_session)

        # Mock streaming response
        async def mock_stream(session_id, message, file_ids=None):
            yield "Hello"
            yield " from"
            yield " AI!"

        mock_chat_service.process_message_stream = mock_stream

        # Make request
        response = client.post(
            "/api/chat/",
            json={"message": "Test message"},
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE response
        lines = response.text.strip().split("\n\n")

        # First event should be session ID
        session_data = json.loads(lines[0].replace("data: ", ""))
        assert session_data["type"] == "session"
        assert session_data["session_id"] == "test-session-123"

        # Check content events
        content_parts = []
        for line in lines[1:-1]:  # Skip session and done events
            if line.startswith("data: "):
                data = json.loads(line.replace("data: ", ""))
                if data["type"] == "content":
                    content_parts.append(data["content"])

        assert "".join(content_parts) == "Hello from AI!"

        # Last event should be done
        done_data = json.loads(lines[-1].replace("data: ", ""))
        assert done_data["type"] == "done"

    @patch("src.api.routes.chat.chat_service")
    def test_clear_history_success(self, mock_chat_service, client):
        """Test clearing chat history."""
        mock_chat_service.clear_session = AsyncMock()

        # Set cookie for session
        client.cookies.set("session_id", "test-session")

        response = client.delete("/api/chat/history")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "message": "Chat history cleared",
        }

        mock_chat_service.clear_session.assert_called_once_with("test-session")

    def test_clear_history_no_session(self, client):
        """Test clearing history without session."""
        response = client.delete("/api/chat/history")

        assert response.status_code == 400
        assert response.json()["detail"] == "No session found"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "LLM Chat Application",
        }

    def test_root_page(self, client):
        """Test root page returns HTML."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Chat with AI Assistant" in response.text
