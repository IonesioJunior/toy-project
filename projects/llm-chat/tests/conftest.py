#!/usr/bin/env python3
"""Test configuration and fixtures."""

import os
import pytest

# Set test environment BEFORE any other imports
os.environ["APP_ENV"] = "testing"
os.environ["OPENAI_API_KEY"] = "test-key-not-used"

from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Environment already set above
    yield
    # Cleanup after tests
    os.environ.pop("OPENAI_API_KEY", None)


@pytest.fixture
def client():
    """Create test client with proper configuration."""
    # Import after setting environment variables
    from src.main import app
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI response for testing."""
    return "This is a test response from the mock OpenAI service."