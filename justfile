# Default recipe to list available commands
default:
    @just --list

# Install project dependencies
install:
    uv sync

# Install development dependencies
install-dev:
    uv sync --all-extras

# Run tests
test:
    uv run pytest

# Run tests with coverage report
test-cov:
    uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# Run tests in watch mode
test-watch:
    uv run pytest-watch

# Run linter
lint:
    uv run ruff check .

# Format code
format:
    uv run black .
    uv run ruff check --fix .

# Run type checker
type-check:
    uv run mypy app/

# Clean up generated files
clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -rf .coverage
    rm -rf .coverage.*
    rm -rf htmlcov
    rm -rf coverage.xml
    rm -rf .pytest_cache
    rm -rf .mypy_cache
    rm -rf .ruff_cache
    rm -rf .uv_cache

# Run the application
run:
    uv run python -m app.main

# Build Docker images
docker-build:
    docker build --target development -t toy-project:dev .
    docker build --target production -t toy-project:prod .

# Run development server in Docker
docker-dev:
    docker-compose up app-dev

# Run production server in Docker
docker-prod:
    docker-compose -f docker-compose.prod.yml up -d

# Run tests in Docker
docker-test:
    docker-compose run --rm test

# Stop all Docker containers
docker-down:
    docker-compose down
    docker-compose -f docker-compose.prod.yml down

# Show Docker logs
docker-logs service="app-dev":
    docker-compose logs -f {{service}}

# Shell into Docker container
docker-shell service="app-dev":
    docker-compose exec {{service}} /bin/bash

# Full development setup
setup:
    uv sync --all-extras
    @echo "Development environment ready!"
    @echo "Run 'just test' to run tests"
    @echo "Run 'just run' to start the server"

# Run all checks (lint, type-check, test)
check:
    uv run ruff check .
    uv run mypy app/
    uv run pytest
    @echo "All checks passed!"

# Build and run production Docker
deploy: docker-build docker-prod
    @echo "Production deployment started!"
    @echo "Server running on http://localhost:80"

# Run the application with uvicorn (development mode)
dev:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the application with uvicorn (production mode)
serve:
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4