#!/usr/bin/env python3
"""Main module for bot-knowledge - FastAPI ChromaDB Vector Database API."""

import uvicorn
from app.config import settings


def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info" if not settings.debug_mode else "debug"
    )


if __name__ == "__main__":
    main()