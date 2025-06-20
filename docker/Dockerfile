# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml README.md uv.lock ./
COPY app ./app

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen


# Development stage
FROM python:3.13-slim as development

WORKDIR /app

# Install uv and development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Create non-root user (same UID as host user ubuntu)
RUN useradd -m -u 1000 appuser

# Copy project files and set ownership
COPY --chown=appuser:appuser . .

# Ensure the /app directory itself is owned by appuser
RUN chown appuser:appuser /app

# Create virtual environment and install all dependencies
RUN mkdir -p /app/.venv && chown -R appuser:appuser /app/.venv
USER appuser
RUN uv venv || true
RUN . .venv/bin/activate && uv sync --all-extras

# Expose port
EXPOSE 8000

# Run with hot reload using uv
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Production stage
FROM python:3.13-slim as production

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application
COPY --chown=appuser:appuser app ./app

# Create files directory
RUN mkdir -p /app/files && chown appuser:appuser /app/files

# Set environment to use virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]