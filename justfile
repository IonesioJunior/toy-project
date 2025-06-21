# Default recipe to list available commands
default:
    @just --list

# Install dependencies for all or specific project
install project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv sync
    else
        cd projects/{{project}} && uv sync
    fi

# Install development dependencies for all or specific project
install-dev project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv sync --all-extras
    else
        cd projects/{{project}} && uv sync --all-extras
    fi

# Run tests for all or specific project
test project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run pytest
    else
        cd projects/{{project}} && uv run pytest
    fi

# Run tests with coverage report for all or specific project
test-cov project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run pytest --cov=projects --cov-report=term-missing --cov-report=html
    else
        cd projects/{{project}} && uv run pytest --cov=src --cov-report=term-missing --cov-report=html
    fi

# Run tests in watch mode for all or specific project
test-watch project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run pytest-watch
    else
        cd projects/{{project}} && uv run pytest-watch
    fi

# Run linter for all or specific project
lint project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run ruff check .
    else
        cd projects/{{project}} && uv run ruff check .
    fi

# Format code for all or specific project
format project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run black .
        uv run ruff check --fix .
    else
        cd projects/{{project}} && uv run black .
        cd projects/{{project}} && uv run ruff check --fix .
    fi

# Run type checker for all or specific project
type-check project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        # Run mypy for each project separately to avoid duplicate module issues
        for proj in projects/*/; do
            if [ -d "$proj/src" ]; then
                proj_name=$(basename "$proj")
                echo "Type checking $proj_name..."
                cd "$proj" && uv run mypy src/ || exit 1
                cd ../..
            fi
        done
    else
        cd projects/{{project}} && uv run mypy src/
    fi

# Clean up generated files
clean project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
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
    else
        cd projects/{{project}} && \
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
    fi

# Run a specific project
run project:
    cd projects/{{project}} && uv run python -m src.main

# Build Docker images for all or specific project
docker-build project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        # Build base images
        docker build --target development -t toy-monorepo:dev-base -f docker/Dockerfile.base .
        docker build --target production -t toy-monorepo:prod-base -f docker/Dockerfile.base .
        # Build all project images
        for proj in projects/*/; do
            if [ -f "$proj/docker/Dockerfile" ]; then
                proj_name=$(basename "$proj")
                docker build --target development -t toy-monorepo:$proj_name-dev -f "$proj/docker/Dockerfile" .
                docker build --target production -t toy-monorepo:$proj_name-prod -f "$proj/docker/Dockerfile" .
            fi
        done
    else
        # Build specific project image
        docker build --target development -t toy-monorepo:{{project}}-dev -f projects/{{project}}/docker/Dockerfile .
        docker build --target production -t toy-monorepo:{{project}}-prod -f projects/{{project}}/docker/Dockerfile .
    fi

# Run development server in Docker for specific project
docker-dev project:
    docker compose -f docker/docker-compose.yml up {{project}}-dev

# Run production server in Docker for specific project
docker-prod project:
    docker compose -f docker/docker-compose.prod.yml up -d {{project}}

# Run tests in Docker for all or specific project
docker-test project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        docker compose -f docker/docker-compose.yml run --rm test-all
    else
        docker compose -f docker/docker-compose.yml run --rm test-{{project}}
    fi

# Stop all Docker containers
docker-down:
    docker compose -f docker/docker-compose.yml down
    docker compose -f docker/docker-compose.prod.yml down

# Show Docker logs for specific service
docker-logs service:
    docker compose -f docker/docker-compose.yml logs -f {{service}}

# Shell into Docker container for specific service
docker-shell service:
    docker compose -f docker/docker-compose.yml exec {{service}} /bin/bash

# Full development setup
setup project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv sync --all-extras
        @echo "Monorepo development environment ready!"
        @echo "Run 'just test' to run all tests"
        @echo "Run 'just test <project>' to run tests for a specific project"
        @echo "Run 'just run <project>' to start a specific project"
    else
        cd projects/{{project}} && uv sync --all-extras
        @echo "{{project}} development environment ready!"
        @echo "Run 'just test {{project}}' to run tests"
        @echo "Run 'just run {{project}}' to start the server"
    fi

# Run all checks (lint, type-check, test) for all or specific project
check project="all":
    #!/usr/bin/env bash
    if [ "{{project}}" = "all" ]; then
        uv run ruff check .
        uv run mypy projects/
        uv run pytest
        @echo "All checks passed!"
    else
        cd projects/{{project}} && \
        uv run ruff check . && \
        uv run mypy src/ && \
        uv run pytest
        @echo "All checks passed for {{project}}!"
    fi

# Build and run production Docker for specific project
deploy project: (docker-build project) (docker-prod project)
    @echo "{{project}} production deployment started!"

# Run a project with uvicorn (development mode)
dev project:
    cd projects/{{project}} && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run a project with uvicorn (production mode)
serve project:
    cd projects/{{project}} && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Workspace-level UV commands
# Update all dependencies
update-deps:
    uv lock --upgrade

# Show dependency tree
deps-tree:
    uv tree

# Add a dependency to workspace
add-dep package:
    uv add {{package}}

# Add a development dependency to workspace
add-dev-dep package:
    uv add --dev {{package}}

# Add a dependency to specific project
add-project-dep project package:
    cd projects/{{project}} && uv add {{package}}

# Create a new project in the monorepo
new-project name:
    #!/usr/bin/env bash
    mkdir -p projects/{{name}}/src
    mkdir -p projects/{{name}}/tests
    touch projects/{{name}}/src/__init__.py
    touch projects/{{name}}/src/main.py
    touch projects/{{name}}/tests/__init__.py
    touch projects/{{name}}/tests/test_main.py
    touch projects/{{name}}/README.md
    echo "[project]" > projects/{{name}}/pyproject.toml
    echo "name = \"{{name}}\"" >> projects/{{name}}/pyproject.toml
    echo "version = \"0.1.0\"" >> projects/{{name}}/pyproject.toml
    echo "" >> projects/{{name}}/pyproject.toml
    echo "[tool.uv.sources]" >> projects/{{name}}/pyproject.toml
    echo "New project '{{name}}' created in projects/{{name}}"

# List all projects
list-projects:
    @echo "Available projects:"
    @for dir in projects/*/; do echo "  - $(basename "$dir")"; done

# Run pre-commit hooks
pre-commit:
    pre-commit run --all-files

# Install pre-commit hooks
install-hooks:
    pre-commit install