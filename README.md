# Toy Project Monorepo

A modern monorepo structure for managing multiple related projects with shared infrastructure and libraries.

## Overview

This monorepo contains multiple projects organized in a clean, scalable architecture:

- **File Manager API**: A FastAPI-based file management system with SyftBox integration
- **Bot Knowledge**: FastAPI ChromaDB Vector Database API
- **LLM Chat**: A FastAPI-based chat application powered by OpenAI's GPT-4 Mini

## Repository Structure

```
toy_project/
├── projects/                    # Individual projects
│   ├── file-manager-api/       # File management API service
│   ├── bot-knowledge/          # FastAPI ChromaDB Vector Database API
│   └── llm-chat/               # LLM Chat application
├── shared/                      # Shared code and utilities
│   ├── configs/                # Shared configuration files
│   ├── libs/                   # Shared libraries
│   │   ├── auth/              # Authentication library
│   │   ├── common/            # Common utilities
│   │   └── database/          # Database utilities
│   └── utils/                  # Shared utilities
│       ├── deployment/        # Deployment scripts
│       └── testing/           # Testing utilities
├── infrastructure/             # Infrastructure as code
│   ├── docker/                # Docker configurations
│   └── scripts/               # Infrastructure scripts
├── docs/                       # Documentation
├── justfile                    # Task automation
└── sonar-project.properties   # Code quality configuration
```

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- UV package manager (optional but recommended)
- Just task runner (optional but recommended)

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd toy_project
   ```

2. Set up the development environment:
   ```bash
   # Install dependencies for a specific project
   cd projects/file-manager-api
   pip install -e ".[dev,test]"
   ```

3. Run a specific project:
   ```bash
   # Using Docker
   docker-compose -f infrastructure/docker/docker-compose.yml up

   # Or directly with Python
   cd projects/file-manager-api
   python -m uvicorn src.app.main:app --reload
   ```

## Projects

### File Manager API
A comprehensive file management system with REST API, secure storage, and SyftBox integration. See [projects/file-manager-api/README.md](projects/file-manager-api/README.md) for details.

### Bot Knowledge
A FastAPI ChromaDB Vector Database API for document management and vector similarity search. See [projects/bot-knowledge/README.md](projects/bot-knowledge/README.md) for details.

### LLM Chat
FastAPI-based chat application with real-time streaming responses and session management - See [projects/llm-chat/README.md](projects/llm-chat/README.md)

## Development

### Common Tasks

Using the `justfile` for task automation:
```bash
# List available commands
just

# Run tests for all projects
just test-all

# Format code
just format

# Lint code
just lint
```

### Working with Individual Projects

Each project in the `projects/` directory is self-contained with its own:
- `pyproject.toml` for dependencies
- `src/` directory for source code
- `tests/` directory for tests
- `docker/` directory for containerization
- Project-specific README

### Shared Code

The `shared/` directory contains common code used across projects:
- **libs/**: Reusable libraries (auth, database, common utilities)
- **configs/**: Shared configuration files
- **utils/**: Deployment and testing utilities

## Infrastructure

### Docker Support

Multi-project Docker support is provided through:
- `infrastructure/docker/docker-compose.yml`: Development environment
- `infrastructure/docker/docker-compose.prod.yml`: Production environment
- Individual Dockerfiles in each project's `docker/` directory

### CI/CD

The repository includes GitHub Actions workflows for:
- Code quality checks (linting, type checking)
- Security scanning
- Automated testing
- Docker image building

## Contributing

1. Create a feature branch from `main`
2. Make your changes in the appropriate project directory
3. Ensure tests pass and code quality checks succeed
4. Submit a pull request with a clear description

## Code Quality

- **Linting**: Ruff for Python code style
- **Type Checking**: MyPy for static type analysis
- **Testing**: Pytest for unit and integration tests
- **Code Coverage**: Minimum 80% coverage requirement
- **Security**: CodeQL and dependency scanning

## License

[Your License Here]