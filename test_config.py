#!/usr/bin/env python3
"""Test script to verify configuration works in test mode."""

import os
import sys

# Set test environment
os.environ["APP_ENV"] = "testing"

# Add project to path
sys.path.insert(0, "projects/llm-chat")

try:
    from src.core.config import get_settings

    settings = get_settings()
    print("✅ Settings loaded successfully!")
    print(f"API Key: {settings.openai_api_key}")
    print(f"Model: {settings.openai_model}")
    print(f"App Name: {settings.app_name}")

    # Test OpenAI service
    from src.services.openai_client import OpenAIService

    openai_service = OpenAIService()
    print("✅ OpenAI service initialized successfully!")
    print(f"Client: {openai_service.client}")

    # Test chat service
    from src.services.chat import ChatService

    chat_service = ChatService()
    print("✅ Chat service initialized successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
