#!/usr/bin/env python3
"""Tests for main module."""

import pytest
from unittest.mock import patch, MagicMock


def test_main():
    """Test main function calls uvicorn correctly."""
    with patch('uvicorn.run') as mock_run:
        # Import here to avoid import-time side effects
        from src.main import main
        
        # Call main function
        main()
        
        # Verify uvicorn.run was called
        mock_run.assert_called_once()
        
        # Check the call arguments
        call_args = mock_run.call_args
        assert call_args[0][0] == "app.main:app"
        assert 'host' in call_args[1]
        assert 'port' in call_args[1]
        assert 'reload' in call_args[1]
        assert 'log_level' in call_args[1]