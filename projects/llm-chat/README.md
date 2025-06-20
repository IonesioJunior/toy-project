# LLM Chat Application

A FastAPI-based chat application powered by OpenAI's GPT-4 Mini model, featuring real-time streaming responses and session management.

## Overview

This application provides a web-based chat interface for interacting with OpenAI's GPT-4 Mini model. It features real-time streaming responses, conversation history management, and a clean, responsive UI built with Jinja2 templates.

## Features

- Real-time streaming chat responses using Server-Sent Events (SSE)
- Session-based conversation history (maintains last 25 messages)
- Clean and responsive web interface
- Automatic session management and cleanup
- RESTful API endpoints for chat operations
- Type-safe implementation with Pydantic models
- Comprehensive error handling and logging

## Prerequisites

- Python 3.13+
- OpenAI API key
- Dependencies listed in `pyproject.toml`

## Quick Start

### Setup

1. Clone the repository and navigate to the project directory:
```bash
cd projects/llm-chat
```

2. Create a `.env` file from the example:
```bash
cp .env.example .env
```

3. Add your OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

### Development
```bash
# Install dependencies
pip install -e ".[dev]"

# Run the application
python -m src.main
```

The application will be available at `http://localhost:8000`

### Using Docker

From the `infrastructure/docker` directory:

```bash
# Copy environment file
cp .env.example .env
# Edit .env and add your OpenAI API key

# Development mode
docker-compose up -d llm-chat-dev

# Production mode
docker-compose up -d llm-chat-prod

# Run tests
docker-compose run --rm llm-chat-test

# View logs
docker-compose logs -f llm-chat-dev

# Stop the application
docker-compose down
```

Or using Docker directly from the `llm-chat` directory:

```bash
# Build development image
docker build -t llm-chat-app .

# Build production image
docker build -f Dockerfile.prod -t llm-chat-app:prod .

# Run the container
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY="your-api-key-here" \
  --name llm-chat \
  llm-chat-app
```

## Project Structure

```
llm-chat/
├── src/
│   ├── api/
│   │   └── routes/        # API endpoints
│   │       └── chat.py    # Chat endpoints
│   ├── core/
│   │   ├── config.py      # Application configuration
│   │   └── exceptions.py  # Custom exceptions
│   ├── models/
│   │   └── chat.py        # Pydantic models
│   ├── services/
│   │   ├── chat.py        # Chat service logic
│   │   └── openai_client.py # OpenAI integration
│   ├── static/
│   │   ├── css/           # Stylesheets
│   │   └── js/            # JavaScript files
│   ├── templates/         # Jinja2 templates
│   └── main.py            # FastAPI application
├── tests/                 # Test suite
├── .env.example           # Environment variables template
└── pyproject.toml         # Project dependencies
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/ tests/
```

## Configuration

The application uses environment variables for configuration. See `.env.example` for available options:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: The model to use (default: gpt-4o-mini)
- `MAX_HISTORY_LENGTH`: Maximum messages to keep in history (default: 25)
- `SESSION_TIMEOUT_MINUTES`: Session timeout in minutes (default: 60)
- `DEBUG`: Enable debug mode (default: false)

## API Documentation

### Endpoints

#### POST /api/chat/
Stream a chat response for a user message.

**Request Body:**
```json
{
    "message": "Your message here",
    "session_id": "optional-session-id"
}
```

**Response:** Server-Sent Events stream

#### DELETE /api/chat/history
Clear the chat history for the current session.

**Response:**
```json
{
    "status": "success",
    "message": "Chat history cleared"
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "service": "LLM Chat Application"
}
```

## Contributing

Please refer to the main repository's contributing guidelines.

## License

See the main repository's license file.