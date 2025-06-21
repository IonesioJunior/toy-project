import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import chroma_client
from .routes import documents_router, health_router
from .services.vector_service import VectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug_mode else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"ChromaDB persist directory: {settings.chroma_persist_directory}")

    # Verify ChromaDB connection
    health = chroma_client.heartbeat()
    if health.get("status") == "healthy":
        logger.info("ChromaDB connection established successfully")

        # Initialize VectorService to trigger embedding model download
        logger.info("Initializing vector service and embedding model...")
        VectorService()
        logger.info("Vector service initialized successfully")
    else:
        logger.warning("ChromaDB connection unhealthy at startup")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app: FastAPI = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A RESTful API for managing vector documents using ChromaDB",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(documents_router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info" if not settings.debug_mode else "debug",
    )
