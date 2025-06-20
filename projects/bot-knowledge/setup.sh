#!/bin/bash

echo "FastAPI ChromaDB API Setup"
echo "========================="

# Create necessary directories
echo "Creating directories..."
mkdir -p chroma_db

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
else
    echo ".env file already exists"
fi

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Run tests
echo "Running tests..."
pytest

echo ""
echo "Setup complete! You can now run the application with:"
echo "  python -m src.main"
echo ""
echo "Or using Docker:"
echo "  docker build -f Dockerfile -t fastapi-chromadb ."
echo "  docker run -p 8000:8000 -v \$(pwd)/chroma_db:/app/chroma_db fastapi-chromadb"
echo ""
echo "Or using docker-compose from infrastructure directory:"
echo "  cd ../../infrastructure/docker"
echo "  docker-compose up bot-knowledge-dev"
echo ""
echo "API documentation will be available at:"
echo "  http://localhost:8000/docs"