#!/usr/bin/env python3
"""Main module for llm-chat."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import logging
import uvicorn

from src.api.routes import chat
from src.core.config import get_settings
from src.services.chat import chat_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting up LLM Chat Application...")
    # Start background cleanup task
    await chat_service.start_cleanup_task()
    yield
    logger.info("Shutting down LLM Chat Application...")


# Create FastAPI app
app = FastAPI(
    title="LLM Chat Application",
    description="A chat application powered by OpenAI GPT-4 Mini",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="src/templates")

# Include routers
app.include_router(chat.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse(
        "chat.html", 
        {"request": request}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "LLM Chat Application"}


def main():
    """Run the application."""
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )


if __name__ == "__main__":
    main()