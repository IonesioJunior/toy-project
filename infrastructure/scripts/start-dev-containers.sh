#!/bin/bash

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOCKER_DIR="${SCRIPT_DIR}/../docker"
PROJECT_ROOT="${SCRIPT_DIR}/../.."

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print error and exit
error_exit() {
    print_color "$RED" "ERROR: $1"
    exit 1
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker daemon
check_docker_daemon() {
    if ! docker info >/dev/null 2>&1; then
        error_exit "Docker daemon is not running. Please start Docker and try again."
    fi
}

# Function to load .env file if it exists
load_env_file() {
    local env_file="${PROJECT_ROOT}/.env"
    if [ -f "$env_file" ]; then
        print_color "$BLUE" "Loading environment variables from .env file..."
        export $(grep -v '^#' "$env_file" | xargs)
    fi
}

# Function to validate environment variables
validate_env_vars() {
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        print_color "$YELLOW" "WARNING: OPENAI_API_KEY is not set."
        print_color "$YELLOW" "The LLM Chat service requires this to function properly."
        echo -n "Enter your OpenAI API key (or press Enter to skip): "
        read -r api_key
        if [ -n "$api_key" ]; then
            export OPENAI_API_KEY="$api_key"
        fi
    fi
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_color "$YELLOW" "⚠ Port $port is already in use"
        return 1
    fi
    return 0
}

# Function to check all required ports
check_ports() {
    local ports=(8001 8002 8003)
    local all_clear=true
    
    print_color "$BLUE" "Checking ports availability..."
    
    for port in "${ports[@]}"; do
        if ! check_port $port; then
            all_clear=false
        fi
    done
    
    if [ "$all_clear" = false ]; then
        print_color "$YELLOW" "Some ports are in use. Services may fail to start."
        echo -n "Continue anyway? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_color "$GREEN" "✓ All ports are available"
    fi
}

# Function to create necessary directories
create_directories() {
    print_color "$BLUE" "Creating necessary directories..."
    
    # Create ChromaDB directory for bot-knowledge
    mkdir -p "${PROJECT_ROOT}/projects/bot-knowledge/chroma_db"
    
    print_color "$GREEN" "✓ Directories created"
}

# Function to stop containers
stop_containers() {
    print_color "$YELLOW" "Stopping development containers..."
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE_CMD stop file-manager-api-dev bot-knowledge-dev llm-chat-dev
    print_color "$GREEN" "✓ Containers stopped"
}

# Function to show development tips
show_dev_tips() {
    print_color "$CYAN" "\n=== Development Tips ==="
    echo "• Hot reload is enabled - changes to source files will be reflected immediately"
    echo "• Python debugger can be attached to any service"
    echo "• Test endpoints using: curl http://localhost:800X/health"
    echo "• View API docs at: http://localhost:800X/docs (FastAPI services)"
    echo "• Database files are persisted in project directories"
}

# Main script starts here
print_color "$BLUE" "=== Starting Development Containers ==="
print_color "$BLUE" "Script directory: ${SCRIPT_DIR}"
print_color "$BLUE" "Docker directory: ${DOCKER_DIR}"

# Pre-flight checks
print_color "$YELLOW" "Running pre-flight checks..."

# Check Docker installation
if ! command_exists docker; then
    error_exit "Docker is not installed. Please install Docker from https://docs.docker.com/get-docker/"
fi
print_color "$GREEN" "✓ Docker is installed"

# Check Docker Compose installation and determine command
DOCKER_COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command_exists docker-compose; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    error_exit "Docker Compose is not installed. Please install Docker Compose from https://docs.docker.com/compose/install/"
fi
print_color "$GREEN" "✓ Docker Compose is installed (using: $DOCKER_COMPOSE_CMD)"

# Check Docker daemon
check_docker_daemon
print_color "$GREEN" "✓ Docker daemon is running"

# Check if docker-compose.yml exists
if [ ! -f "${DOCKER_DIR}/docker-compose.yml" ]; then
    error_exit "docker-compose.yml not found in ${DOCKER_DIR}"
fi
print_color "$GREEN" "✓ docker-compose.yml found"

# Check ports
check_ports

# Create necessary directories
create_directories

# Load environment variables
load_env_file
validate_env_vars

# Parse command line arguments
FOLLOW_LOGS=false
STOP_FIRST=false
BUILD_NO_CACHE=false
SERVICE_FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW_LOGS=true
            shift
            ;;
        -s|--stop)
            stop_containers
            exit 0
            ;;
        --stop-first)
            STOP_FIRST=true
            shift
            ;;
        --no-cache)
            BUILD_NO_CACHE=true
            shift
            ;;
        --service)
            SERVICE_FILTER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -f, --follow       Follow container logs after starting"
            echo "  -s, --stop         Stop development containers and exit"
            echo "  --stop-first       Stop containers before starting new ones"
            echo "  --no-cache         Build images without using cache"
            echo "  --service NAME     Start only a specific service"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Available services:"
            echo "  file-manager-api-dev"
            echo "  bot-knowledge-dev"
            echo "  llm-chat-dev"
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1. Use -h for help."
            ;;
    esac
done

# Stop containers first if requested
if [ "$STOP_FIRST" = true ]; then
    stop_containers
fi

# Change to docker directory
cd "$DOCKER_DIR" || error_exit "Failed to change to docker directory"

# Determine which services to start
if [ -n "$SERVICE_FILTER" ]; then
    SERVICES="$SERVICE_FILTER"
else
    SERVICES="file-manager-api-dev bot-knowledge-dev llm-chat-dev"
fi

# Build and start development containers
print_color "$YELLOW" "Building and starting development containers..."
print_color "$BLUE" "Services: $SERVICES"
print_color "$BLUE" "This may take a few minutes on first run..."

BUILD_ARGS=""
if [ "$BUILD_NO_CACHE" = true ]; then
    BUILD_ARGS="--no-cache"
fi

if $DOCKER_COMPOSE_CMD up -d --build $BUILD_ARGS $SERVICES; then
    print_color "$GREEN" "✓ Containers started successfully"
else
    error_exit "Failed to start containers. Check the logs with: $DOCKER_COMPOSE_CMD logs"
fi

# Display service information
print_color "$BLUE" "\n=== Development Services ==="
print_color "$GREEN" "File Manager API: http://localhost:8001"
print_color "$GREEN" "  - API Docs: http://localhost:8001/docs"
print_color "$GREEN" "  - Health: http://localhost:8001/health"
print_color "$GREEN" "\nBot Knowledge API: http://localhost:8002"
print_color "$GREEN" "  - API Docs: http://localhost:8002/docs"
print_color "$GREEN" "  - Health: http://localhost:8002/health"
print_color "$GREEN" "\nLLM Chat Interface: http://localhost:8003"
print_color "$GREEN" "  - Chat UI: http://localhost:8003/"
print_color "$GREEN" "  - Health: http://localhost:8003/health"

# Show development tips
show_dev_tips

# Display useful commands
print_color "$BLUE" "\n=== Useful Commands ==="
echo "View logs: $DOCKER_COMPOSE_CMD logs -f [service-name]"
echo "Stop all: ${SCRIPT_DIR}/start-dev-containers.sh --stop"
echo "Restart: $DOCKER_COMPOSE_CMD restart [service-name]"
echo "Shell access: $DOCKER_COMPOSE_CMD exec [service-name] /bin/bash"
echo "Run tests: $DOCKER_COMPOSE_CMD run [service-name] pytest"
echo "Status: $DOCKER_COMPOSE_CMD ps"

# Show volume information
print_color "$BLUE" "\n=== Volume Mounts ==="
echo "Source code is mounted for hot-reloading:"
echo "• File Manager API: ${PROJECT_ROOT}/projects/file-manager-api → /app"
echo "• Bot Knowledge: ${PROJECT_ROOT}/projects/bot-knowledge → /app"
echo "• LLM Chat: ${PROJECT_ROOT}/projects/llm-chat → /app"

# Follow logs if requested
if [ "$FOLLOW_LOGS" = true ]; then
    print_color "$YELLOW" "\nFollowing container logs (Ctrl+C to exit)..."
    $DOCKER_COMPOSE_CMD logs -f $SERVICES
fi

print_color "$GREEN" "\n✓ Development environment is ready!"
print_color "$CYAN" "Happy coding! 🚀"