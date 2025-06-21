import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status

from ..config import settings
from ..database import chroma_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Check the health status of the API and its dependencies"""
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "FastAPI ChromaDB API",
        "version": settings.app_version,
        "checks": {},
    }

    # Check ChromaDB connection
    try:
        # heartbeat() returns a timestamp as int/float indicating the server is alive
        heartbeat_timestamp = chroma_client.heartbeat()
        health_status["checks"]["chromadb"] = {
            "status": "healthy",
            "heartbeat": heartbeat_timestamp,
        }
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {str(e)}")
        health_status["checks"]["chromadb"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    return health_status


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Check if the service is ready to accept requests"""
    try:
        # Verify ChromaDB is accessible
        # heartbeat() returns a timestamp if successful, raises exception if not
        chroma_client.heartbeat()
        return {"status": "ready", "message": "Service is ready to accept requests"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {"status": "not_ready", "message": str(e)}
