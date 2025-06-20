import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = Field(default="FastAPI ChromaDB API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug_mode: bool = Field(default=False, description="Debug mode flag")
    
    # ChromaDB settings
    chroma_persist_directory: str = Field(
        default="./chroma_db", 
        description="Directory to persist ChromaDB data"
    )
    chroma_collection_name: str = Field(
        default="documents", 
        description="Default collection name"
    )
    
    # API settings
    api_prefix: str = Field(default="/api/v1", description="API route prefix")
    max_page_size: int = Field(default=100, description="Maximum page size for pagination")
    default_page_size: int = Field(default=10, description="Default page size for pagination")
    
    # CORS settings
    cors_allowed_origins: list[str] = Field(
        default=["*"], 
        description="Allowed CORS origins"
    )
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload on code changes")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def ensure_directories(self):
        """Ensure required directories exist"""
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)


# Create settings instance
settings = Settings()
settings.ensure_directories()