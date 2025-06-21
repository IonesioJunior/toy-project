import logging
import os
from typing import Any, Dict, Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings

from .config import settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """Singleton ChromaDB client manager"""

    _instance: Optional["ChromaDBClient"] = None
    _client: Optional[ClientAPI] = None

    def __new__(cls) -> "ChromaDBClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Don't initialize client at construction time
        # This prevents issues during test imports
        pass

    def _initialize_client(self) -> None:
        """Initialize ChromaDB persistent client"""
        try:
            logger.info(
                f"Initializing ChromaDB client with persist directory: "
                f"{settings.chroma_persist_directory}"
            )

            # Check if we're in test environment
            is_testing = os.environ.get("APP_ENV") == "testing"

            chroma_settings = ChromaSettings(
                anonymized_telemetry=False, allow_reset=True, is_persistent=True
            )

            if is_testing:
                # Use in-memory client for tests to avoid file system issues
                logger.info("Using in-memory ChromaDB client for testing")
                self._client = chromadb.Client(settings=chroma_settings)
            else:
                self._client = chromadb.PersistentClient(
                    path=settings.chroma_persist_directory, settings=chroma_settings
                )

            logger.info("ChromaDB client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise

    @property
    def client(self) -> ClientAPI:
        """Get the ChromaDB client instance"""
        if self._client is None:
            self._initialize_client()
        assert self._client is not None, "ChromaDB client initialization failed"
        return self._client

    def reset_database(self) -> None:
        """Reset the entire database (use with caution)"""
        try:
            if self._client is not None:
                self._client.reset()
            else:
                raise RuntimeError("ChromaDB client not initialized")
            logger.info("ChromaDB database reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB: {str(e)}")
            raise

    def heartbeat(self) -> Dict[str, Any]:
        """Check if ChromaDB is responsive"""
        try:
            result = self.client.heartbeat()
            return {"status": "healthy", "timestamp": result}
        except Exception as e:
            logger.error(f"ChromaDB heartbeat failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}


# Global instance - lazy initialization
_chroma_client: Optional[ChromaDBClient] = None


def get_chroma_client() -> ChromaDBClient:
    """Get the global ChromaDB client instance"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaDBClient()
    return _chroma_client


# For backward compatibility
chroma_client = get_chroma_client()
