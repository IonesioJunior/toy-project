import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.chat import ChatService
from src.models.chat import ChatSession
from src.core.exceptions import SessionNotFoundException


@pytest.mark.asyncio
class TestChatService:
    
    @patch('src.services.chat.OpenAIService')
    async def test_get_or_create_session_new(self, mock_openai):
        """Test creating a new session."""
        service = ChatService()
        
        session = await service.get_or_create_session()
        
        assert isinstance(session, ChatSession)
        assert session.session_id in service.sessions
        assert len(session.messages) == 0
    
    @patch('src.services.chat.OpenAIService')
    async def test_get_or_create_session_existing(self, mock_openai):
        """Test getting an existing session."""
        service = ChatService()
        
        # Create a session first
        session1 = await service.get_or_create_session("test-session")
        
        # Get the same session
        session2 = await service.get_or_create_session("test-session")
        
        assert session1.session_id == session2.session_id
        assert session1 is session2
    
    @patch('src.services.chat.OpenAIService')
    async def test_process_message_stream(self, mock_openai_class):
        """Test processing a message with streaming."""
        # Mock OpenAI service
        mock_openai = AsyncMock()
        mock_openai_class.return_value = mock_openai
        
        async def mock_stream(messages):
            yield "Hello"
            yield " world!"
        
        mock_openai.create_chat_completion_stream = mock_stream
        
        service = ChatService()
        
        # Process message
        chunks = []
        async for chunk in service.process_message_stream("session-123", "Hi there"):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " world!"]
        
        # Check session was created and messages added
        session = service.sessions["session-123"]
        assert len(session.messages) == 2
        assert session.messages[0].content == "Hi there"
        assert session.messages[0].role == "user"
        assert session.messages[1].content == "Hello world!"
        assert session.messages[1].role == "assistant"
    
    @patch('src.services.chat.OpenAIService')
    async def test_clear_session(self, mock_openai):
        """Test clearing a session."""
        service = ChatService()
        
        # Create a session
        session = await service.get_or_create_session("test-session")
        assert "test-session" in service.sessions
        
        # Clear it
        await service.clear_session("test-session")
        assert "test-session" not in service.sessions
    
    @patch('src.services.chat.OpenAIService')
    async def test_clear_nonexistent_session(self, mock_openai):
        """Test clearing a non-existent session raises exception."""
        service = ChatService()
        
        with pytest.raises(SessionNotFoundException):
            await service.clear_session("non-existent")