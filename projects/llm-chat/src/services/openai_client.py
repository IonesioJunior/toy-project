import logging
import os
from typing import AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionChunk
from openai.types.chat.chat_completion import ChatCompletion
from openai._streaming import AsyncStream

from src.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model: str = settings.openai_model
        self.chunk_size: int = settings.stream_chunk_size
        self.client: Optional[AsyncOpenAI] = None

        # Initialize client only if not in test mode
        if os.getenv("APP_ENV") != "testing":
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def create_chat_completion_stream(
        self, messages: List[ChatCompletionMessageParam]
    ) -> AsyncIterator[str]:
        """Create a streaming chat completion."""
        # Return mock response in test mode
        if os.getenv("APP_ENV") == "testing":
            yield "This is a test response from the mock OpenAI service."
            return

        # Check if client is initialized
        if self.client is None:
            logger.error("OpenAI client not initialized")
            yield "Error: OpenAI client not initialized"
            return

        try:
            # When stream=True, create() returns AsyncStream[ChatCompletionChunk]
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            yield f"Error: {str(e)}"

    async def create_chat_completion(self, messages: List[ChatCompletionMessageParam]) -> str:
        """Create a non-streaming chat completion."""
        # Return mock response in test mode
        if os.getenv("APP_ENV") == "testing":
            return "This is a test response from the mock OpenAI service."

        # Check if client is initialized
        if self.client is None:
            logger.error("OpenAI client not initialized")
            raise ValueError("OpenAI client not initialized")

        try:
            # When stream=False (default), create() returns ChatCompletion
            response = await self.client.chat.completions.create(
                model=self.model, 
                messages=messages, 
                temperature=0.7, 
                max_tokens=2000
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
