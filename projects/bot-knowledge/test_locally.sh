#!/bin/bash
# Test script to verify the fixes work locally

echo "Setting up test environment..."
export APP_ENV=testing
export CHROMA_TELEMETRY_DISABLED=1
export PYTHONUNBUFFERED=1

echo "Running pytest with verbose output..."
cd "$(dirname "$0")"
uv run pytest -vv -s tests/test_main.py

echo "Running all tests..."
uv run pytest -v