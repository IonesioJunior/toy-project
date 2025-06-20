# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files from monorepo root and project
COPY pyproject.toml uv.lock ./
COPY projects/file-manager-api/pyproject.toml ./projects/file-manager-api/
COPY projects/file-manager-api/README.md ./projects/file-manager-api/
COPY projects/file-manager-api/src ./projects/file-manager-api/src

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Change to project directory for dependency installation
WORKDIR /app/projects/file-manager-api
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

# Copy entire monorepo and set ownership
COPY --chown=appuser:appuser . .

# Ensure the /app directory itself is owned by appuser
RUN chown appuser:appuser /app

# Create virtual environment and install all dependencies
WORKDIR /app/projects/file-manager-api
RUN mkdir -p /app/projects/file-manager-api/.venv && chown -R appuser:appuser /app/projects/file-manager-api/.venv
USER appuser
RUN uv venv || true
RUN . .venv/bin/activate && uv sync --all-extras

# Expose port
EXPOSE 8000

# Run with hot reload using uv - update module path
CMD [".venv/bin/uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Production stage
FROM python:3.13-slim as production

WORKDIR /app/projects/file-manager-api

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application from monorepo structure
COPY --chown=appuser:appuser projects/file-manager-api/src ./src

# Create files directory
RUN mkdir -p /app/projects/file-manager-api/files && chown appuser:appuser /app/projects/file-manager-api/files

# Set environment to use virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run with production settings - update module path
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]