from openai import AsyncOpenAI
from typing import AsyncIterator, List, Dict
import logging
import os
from src.core.config import get_settings


logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        settings = get_settings()
        self.model = settings.openai_model
        self.chunk_size = settings.stream_chunk_size
        
        # Initialize client only if not in test mode
        if os.getenv("APP_ENV") == "testing":
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def create_chat_completion_stream(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncIterator[str]:
        """Create a streaming chat completion."""
        # Return mock response in test mode
        if os.getenv("APP_ENV") == "testing":
            yield "This is a test response from the mock OpenAI service."
            return
            
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def create_chat_completion(
        self, 
        messages: List[Dict[str, str]]
    ) -> str:
        """Create a non-streaming chat completion."""
        # Return mock response in test mode
        if os.getenv("APP_ENV") == "testing":
            return "This is a test response from the mock OpenAI service."
            
        try:
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