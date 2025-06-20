FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

# Copy application code
COPY src/ ./src/

# Create directory for ChromaDB persistence
RUN mkdir -p /app/chroma_db

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROMA_PERSIST_DIRECTORY=/app/chroma_db

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]