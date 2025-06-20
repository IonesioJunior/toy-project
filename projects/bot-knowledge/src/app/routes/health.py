from fastapi import APIRouter, status
from typing import Dict, Any
import logging
from datetime import datetime

from ..database import chroma_client
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Check the health status of the API and its dependencies"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "FastAPI ChromaDB API",
        "version": settings.app_version,
        "checks": {}
    }
    
    # Check ChromaDB connection
    try:
        chroma_health = chroma_client.heartbeat()
        health_status["checks"]["chromadb"] = chroma_health
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {str(e)}")
        health_status["checks"]["chromadb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Check if the service is ready to accept requests"""
    try:
        # Verify ChromaDB is accessible
        chroma_health = chroma_client.heartbeat()
        if chroma_health.get("status") == "healthy":
            return {"status": "ready", "message": "Service is ready to accept requests"}
        else:
            return {"status": "not_ready", "message": "ChromaDB is not healthy"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {"status": "not_ready", "message": str(e)}