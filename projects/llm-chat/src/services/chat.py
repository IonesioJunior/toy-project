import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional, cast
from uuid import uuid4

from openai.types.chat import ChatCompletionMessageParam

from src.core.config import get_settings
from src.core.exceptions import ExternalServiceError, SessionNotFoundError
from src.models.chat import ChatSession
from src.services.file_manager_client import file_manager_client
from src.services.openai_client import OpenAIService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat sessions and conversations."""

    def __init__(self) -> None:
        self.sessions: Dict[str, ChatSession] = {}
        self.openai_service = OpenAIService()
        self.settings = get_settings()
        self._cleanup_task: Optional[asyncio.Task[None]] = None

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_sessions())

    async def get_or_create_session(
        self, session_id: Optional[str] = None
    ) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_accessed = datetime.now(timezone.utc)
            return session

        # Create new session
        new_session_id = session_id or str(uuid4())
        session = ChatSession(session_id=new_session_id)
        self.sessions[new_session_id] = session
        sanitized_session_id = new_session_id.replace("\r\n", "").replace("\n", "")
        logger.info(f"Created new session: {sanitized_session_id}")
        return session

    async def process_message_stream(
        self, session_id: str, user_message: str, file_ids: Optional[List[str]] = None
    ) -> AsyncIterator[str]:
        """Process user message and return streaming response."""
        try:
            # Get or create session
            session = await self.get_or_create_session(session_id)

            # Build the enhanced message with file context if provided
            enhanced_message = await self._build_message_with_context(
                user_message, file_ids
            )

            # Add user message to history (store original message, not enhanced)
            session.add_message("user", user_message)

            # Get messages for OpenAI
            messages = session.get_openai_messages()

            # If we have file context, replace the last user message with
            # enhanced version
            if enhanced_message != user_message and messages:
                messages[-1]["content"] = enhanced_message
            
            # Convert to ChatCompletionMessageParam type
            typed_messages: List[ChatCompletionMessageParam] = [
                cast(ChatCompletionMessageParam, {"role": msg["role"], "content": msg["content"]})
                for msg in messages
            ]

            # Track the full response for history
            full_response = ""

            # Stream response from OpenAI
            async for chunk in self.openai_service.create_chat_completion_stream(
                typed_messages
            ):
                full_response += chunk
                yield chunk

            # Add assistant response to history
            session.add_message("assistant", full_response)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            yield "An internal error occurred."

    async def _build_message_with_context(
        self, user_message: str, file_ids: Optional[List[str]] = None
    ) -> str:
        """
        Build enhanced message with file context using the specified template format.

        Args:
            user_message: The user's original message
            file_ids: Optional list of file IDs to include as context

        Returns:
            Enhanced message with context or original message if no files
        """
        if not file_ids:
            return user_message

        try:
            # Fetch file contents
            file_contents = await file_manager_client.get_multiple_files_content(
                file_ids
            )

            if not file_contents:
                logger.warning("No file contents retrieved, using original message")
                return user_message

            # Build context section
            context_parts = []
            for file_id, content in file_contents.items():
                # Try to get filename from file list (optional enhancement)
                context_parts.append(f"File ID: {file_id}\n{content}")

            context_text = "\n\n---\n\n".join(context_parts)

            # Build enhanced message using the template format
            enhanced_message = f"""<user_question>
{user_message}
</user_question>

<context>
{context_text}
</context>"""

            logger.info(
                f"Enhanced message with {len(file_contents)} file(s) as context"
            )
            return enhanced_message

        except ExternalServiceError as e:
            logger.error(f"Failed to fetch file contents: {str(e)}")
            # Fall back to original message if file fetching fails
            return user_message
        except Exception as e:
            logger.error(f"Unexpected error building context: {str(e)}")
            return user_message

    async def clear_session(self, session_id: str) -> None:
        """Clear a specific session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            sanitized_session_id = session_id.replace("\r\n", "").replace("\n", "")
            logger.info(f"Cleared session: {sanitized_session_id}")
        else:
            raise SessionNotFoundError(f"Session {session_id} not found")

    async def _cleanup_old_sessions(self) -> None:
        """Background task to clean up old sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                cutoff_time = datetime.now(timezone.utc) - timedelta(
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
