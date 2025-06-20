from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # OpenAI Configuration
    openai_api_key: str
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()