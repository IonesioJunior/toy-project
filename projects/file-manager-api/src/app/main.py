import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings, syft_client
from app.routes import files, permissions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    # Startup
    if not syft_client:
        raise RuntimeError(
            "SyftBox is not properly configured. "
            "Please run 'syftbox init' before starting the application."
        )
    print(f"SyftBox verified. User: {syft_client.email} (ENV: {settings.APP_ENV})")

    yield

    # Shutdown (if needed)
    pass


app = FastAPI(
    title="File Management API",
    description="A FastAPI application for file management with SyftBox integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates
templates = Jinja2Templates(directory="src/app/templates")

# Mount static files
if os.path.exists("src/app/static"):
    app.mount("/static", StaticFiles(directory="src/app/static"), name="static")


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """Health check endpoint that verifies syft_core status."""
    if not syft_client:
        raise HTTPException(status_code=503, detail="SyftBox not available")
    return {
        "status": "healthy",
        "syftbox_user": syft_client.email,
        "storage_configured": True,
    }


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "max_file_size": settings.MAX_FILE_SIZE,
            "max_file_size_mb": settings.MAX_FILE_SIZE // (1024 * 1024),
            "allowed_extensions": list(settings.ALLOWED_EXTENSIONS),
        },
    )


@app.get("/hello/{name}")
def read_item(name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}


# Include routers
app.include_router(files.router, prefix=settings.API_PREFIX)
app.include_router(permissions.router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
