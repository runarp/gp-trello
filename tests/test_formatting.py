"""Tests for formatting utility functions."""

import pytest

from trello_sync.utils.formatting import (
    format_bytes,
    format_date,
    format_iso_date,
    sanitize_file_name,
)


def test_sanitize_file_name() -> None:
    """Test sanitize_file_name function."""
    assert sanitize_file_name("Test Card Name") == "test-card-name"
    assert sanitize_file_name("Test@Card#Name!") == "testcardname"
    assert sanitize_file_name("Test  Card   Name") == "test-card-name"
    assert sanitize_file_name("") == "untitled"
    assert sanitize_file_name(None) == "untitled"
    assert sanitize_file_name("   ") == "untitled"
    assert sanitize_file_name("a" * 150) == "a" * 100


def test_format_iso_date() -> None:
    """Test format_iso_date function."""
    assert format_iso_date("2024-01-20T12:00:00Z") == "2024-01-20T12:00:00Z"
    assert format_iso_date("2024-01-20T12:00:00+00:00") == "2024-01-20T12:00:00Z"
    assert format_iso_date(None) is None
    assert format_iso_date("") is None
    assert format_iso_date("invalid") == "invalid"


def test_format_date() -> None:
    """Test format_date function."""
    result = format_date("2024-01-20T12:00:00Z")
    assert "Jan 20, 2024" in result
    assert format_date(None) == ""
    assert format_date("") == ""
    assert format_date("invalid") == "invalid"


def test_format_bytes() -> None:
    """Test format_bytes function."""
    assert format_bytes(0) == ""
    assert format_bytes(None) == ""
    assert format_bytes(512) == "512.0 Bytes"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1048576) == "1.0 MB"
    assert format_bytes(1073741824) == "1.0 GB"

