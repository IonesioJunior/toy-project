#!/bin/bash

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Function to check service health
check_service_health() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    print_color "$BLUE" "Checking health of ${service_name}..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "${url}" >/dev/null 2>&1; then
            print_color "$GREEN" "✓ ${service_name} is healthy"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_color "$YELLOW" "⚠ ${service_name} health check timed out (service may still be starting)"
    return 1
}

# Function to stop containers
stop_containers() {
    print_color "$YELLOW" "Stopping production containers..."
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE_CMD stop file-manager-api-prod bot-knowledge-prod llm-chat-prod
    print_color "$GREEN" "✓ Containers stopped"
}

# Main script starts here
print_color "$BLUE" "=== Starting Production Containers ==="
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

# Load environment variables
load_env_file
validate_env_vars

# Parse command line arguments
FOLLOW_LOGS=false
STOP_FIRST=false

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
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -f, --follow     Follow container logs after starting"
            echo "  -s, --stop       Stop production containers and exit"
            echo "  --stop-first     Stop containers before starting new ones"
            echo "  -h, --help       Show this help message"
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

# Build and start production containers
print_color "$YELLOW" "Building and starting production containers..."
print_color "$BLUE" "This may take a few minutes on first run..."

# Start containers one by one with a small delay to avoid port conflicts
SERVICES=("file-manager-api-prod" "bot-knowledge-prod" "llm-chat-prod")
for service in "${SERVICES[@]}"; do
    print_color "$BLUE" "Starting ${service}..."
    if ! $DOCKER_COMPOSE_CMD up -d --build "$service"; then
        print_color "$RED" "Failed to start ${service}"
        print_color "$YELLOW" "Checking logs for ${service}:"
        $DOCKER_COMPOSE_CMD logs "$service" | tail -20
        error_exit "Failed to start containers. Check the logs with: $DOCKER_COMPOSE_CMD logs"
    fi
    sleep 2  # Small delay between services
done

print_color "$GREEN" "✓ All containers started successfully"

# Display service information
print_color "$BLUE" "\n=== Production Services ==="
print_color "$GREEN" "File Manager API: http://localhost:8080"
print_color "$GREEN" "Bot Knowledge API: http://localhost:8091"
print_color "$GREEN" "LLM Chat Interface: http://localhost:8082"

# Check service health
print_color "$BLUE" "\n=== Checking Service Health ==="
check_service_health "File Manager API" "http://localhost:8080/health"
check_service_health "Bot Knowledge API" "http://localhost:8091/health"
check_service_health "LLM Chat Interface" "http://localhost:8082/health"

# Display useful commands
print_color "$BLUE" "\n=== Useful Commands ==="
echo "View logs: $DOCKER_COMPOSE_CMD logs -f [service-name]"
echo "Stop all: ${SCRIPT_DIR}/start-prod-containers.sh --stop"
echo "Restart: $DOCKER_COMPOSE_CMD restart [service-name]"
echo "Status: $DOCKER_COMPOSE_CMD ps"

# Follow logs if requested
if [ "$FOLLOW_LOGS" = true ]; then
    print_color "$YELLOW" "\nFollowing container logs (Ctrl+C to exit)..."
    $DOCKER_COMPOSE_CMD logs -f file-manager-api-prod bot-knowledge-prod llm-chat-prod
fi

print_color "$GREEN" "\n✓ Production environment is ready!"