#!/usr/bin/env python3
"""Tests for main module."""

import pytest
from src.main import main


def test_main(capsys):
    """Test main function output."""
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello, World from project-three!\n"