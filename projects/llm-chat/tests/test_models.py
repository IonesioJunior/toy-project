import pytest
from datetime import datetime
from uuid import UUID

from src.models.chat import ChatMessage, ChatRequest, ChatSession


class TestChatModels:
    def test_chat_message_creation(self):
        """Test ChatMessage model creation."""
        message = ChatMessage(
            role="user",
            content="Hello, world!"
        )
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert isinstance(message.id, UUID)
        assert isinstance(message.timestamp, datetime)
    
    def test_chat_request_validation(self):
        """Test ChatRequest validation."""
        # Valid request
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        
        # Empty message should fail
        with pytest.raises(ValueError):
            ChatRequest(message="")
    
    def test_chat_session_add_message(self):
        """Test adding messages to chat session."""
        session = ChatSession(session_id="test-session")
        
        # Add messages
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"
        assert session.messages[1].role == "assistant"
        assert session.messages[1].content == "Hi there!"
    
    def test_chat_session_max_history(self):
        """Test that chat session maintains max history length."""
        from unittest.mock import patch
        
        session = ChatSession(session_id="test-session")
        
        # Mock settings to have max_history_length of 3
        with patch('src.core.config.get_settings') as mock_settings:
            mock_settings.return_value.max_history_length = 3
            
            # Add 5 messages
            for i in range(5):
                session.add_message("user", f"Message {i}")
            
            # Should only have last 3 messages
            assert len(session.messages) == 3
            assert session.messages[0].content == "Message 2"
            assert session.messages[2].content == "Message 4"
    
    def test_get_openai_messages(self):
        """Test converting messages to OpenAI format."""
        session = ChatSession(session_id="test-session")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        
        openai_messages = session.get_openai_messages()
        
        assert len(openai_messages) == 2
        assert openai_messages[0] == {"role": "user", "content": "Hello"}
        assert openai_messages[1] == {"role": "assistant", "content": "Hi!"}