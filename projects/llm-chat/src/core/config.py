from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # Application Configuration
    app_name: str = "LLM Chat Application"
    debug: bool = False
    
    # Session Configuration
    max_history_length: int = 25
    session_timeout_minutes: int = 60
    
    # Streaming Configuration
    stream_chunk_size: int = 512
    
    class Config:
        env_file = ".env"
    
    def model_post_init(self, __context) -> None:
        """Validate settings after initialization."""
        # Only require API key when not in test environment
        if os.getenv("APP_ENV") != "testing" and not self.openai_api_key:
            raise ValueError("openai_api_key is required when not in test mode")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()