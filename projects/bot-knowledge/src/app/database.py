import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
import logging
from .config import settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """Singleton ChromaDB client manager"""
    _instance: Optional['ChromaDBClient'] = None
    _client: Optional[chromadb.PersistentClient] = None
    
    def __new__(cls) -> 'ChromaDBClient':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB persistent client"""
        try:
            logger.info(f"Initializing ChromaDB client with persist directory: {settings.chroma_persist_directory}")
            
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=chroma_settings
            )
            
            logger.info("ChromaDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    @property
    def client(self) -> chromadb.PersistentClient:
        """Get the ChromaDB client instance"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def reset_database(self):
        """Reset the entire database (use with caution)"""
        try:
            self._client.reset()
            logger.info("ChromaDB database reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB: {str(e)}")
            raise
    
    def heartbeat(self) -> dict:
        """Check if ChromaDB is responsive"""
        try:
            result = self._client.heartbeat()
            return {"status": "healthy", "timestamp": result}
        except Exception as e:
            logger.error(f"ChromaDB heartbeat failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}


# Global instance
chroma_client = ChromaDBClient()