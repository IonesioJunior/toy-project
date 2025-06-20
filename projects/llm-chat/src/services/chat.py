from typing import Dict, Optional, AsyncIterator
from datetime import datetime, timedelta
import asyncio
from uuid import uuid4
import logging

from src.models.chat import ChatSession, ChatMessage
from src.services.openai_client import OpenAIService
from src.core.config import get_settings
from src.core.exceptions import SessionNotFoundException


logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat sessions and conversations."""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.openai_service = OpenAIService()
        self.settings = get_settings()
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_sessions())
    
    async def get_or_create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_accessed = datetime.utcnow()
            return session
        
        # Create new session
        new_session_id = session_id or str(uuid4())
        session = ChatSession(session_id=new_session_id)
        self.sessions[new_session_id] = session
        logger.info(f"Created new session: {new_session_id}")
        return session
    
    async def process_message_stream(
        self, 
        session_id: str, 
        user_message: str
    ) -> AsyncIterator[str]:
        """Process user message and return streaming response."""
        try:
            # Get or create session
            session = await self.get_or_create_session(session_id)
            
            # Add user message to history
            session.add_message("user", user_message)
            
            # Get messages for OpenAI
            messages = session.get_openai_messages()
            
            # Track the full response for history
            full_response = ""
            
            # Stream response from OpenAI
            async for chunk in self.openai_service.create_chat_completion_stream(messages):
                full_response += chunk
                yield chunk
            
            # Add assistant response to history
            session.add_message("assistant", full_response)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            yield "An internal error occurred."
    
    async def clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            sanitized_session_id = session_id.replace('\r\n', '').replace('\n', '')
            logger.info(f"Cleared session: {sanitized_session_id}")
        else:
            raise SessionNotFoundException(f"Session {session_id} not found")
    
    async def _cleanup_old_sessions(self) -> None:
        """Background task to clean up old sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                cutoff_time = datetime.utcnow() - timedelta(
                    minutes=self.settings.session_timeout_minutes
                )
                
                sessions_to_remove = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if session.last_accessed < cutoff_time
                ]
                
                for session_id in sessions_to_remove:
                    del self.sessions[session_id]
                    logger.info(f"Cleaned up old session: {session_id}")
                    
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")


# Global instance
chat_service = ChatService()