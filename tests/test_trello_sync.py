"""Tests for TrelloSync service."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture

from trello_sync.services.trello_sync import TrelloSync, get_credentials


def test_get_credentials_success(monkeypatch: "MonkeyPatch") -> None:
    """Test successful credential retrieval."""
    monkeypatch.setenv('TRELLO_API_KEY', 'test_key')
    monkeypatch.setenv('TRELLO_TOKEN', 'test_token')
    
    api_key, token = get_credentials()
    assert api_key == 'test_key'
    assert token == 'test_token'


def test_get_credentials_missing_key(monkeypatch: "MonkeyPatch") -> None:
    """Test credential retrieval with missing API key."""
    monkeypatch.delenv('TRELLO_API_KEY', raising=False)
    monkeypatch.setenv('TRELLO_TOKEN', 'test_token')
    
    with pytest.raises(ValueError, match="TRELLO_API_KEY"):
        get_credentials()


def test_get_credentials_missing_token(monkeypatch: "MonkeyPatch") -> None:
    """Test credential retrieval with missing token."""
    monkeypatch.setenv('TRELLO_API_KEY', 'test_key')
    monkeypatch.delenv('TRELLO_TOKEN', raising=False)
    monkeypatch.delenv('TRELLO_API_TOKEN', raising=False)
    
    with pytest.raises(ValueError, match="TRELLO_TOKEN"):
        get_credentials()


def test_get_credentials_uses_api_token(monkeypatch: "MonkeyPatch") -> None:
    """Test credential retrieval uses TRELLO_API_TOKEN as fallback."""
    monkeypatch.setenv('TRELLO_API_KEY', 'test_key')
    monkeypatch.delenv('TRELLO_TOKEN', raising=False)
    monkeypatch.setenv('TRELLO_API_TOKEN', 'test_api_token')
    
    api_key, token = get_credentials()
    assert api_key == 'test_key'
    assert token == 'test_api_token'


@patch('trello_sync.services.trello_sync.get_credentials')
def test_trello_sync_init(mock_get_creds: MagicMock) -> None:
    """Test TrelloSync initialization."""
    mock_get_creds.return_value = ('test_key', 'test_token')
    
    sync = TrelloSync()
    
    assert sync.api_key == 'test_key'
    assert sync.token == 'test_token'
    assert sync.base_url == 'https://api.trello.com/1'


@patch('trello_sync.services.trello_sync.get_credentials')
def test_trello_sync_request(mock_get_creds: MagicMock, mocker: "MockerFixture") -> None:
    """Test TrelloSync API request."""
    mock_get_creds.return_value = ('test_key', 'test_token')
    mock_response = MagicMock()
    mock_response.json.return_value = {'id': '123', 'name': 'Test'}
    mock_response.raise_for_status = MagicMock()
    
    mock_session = mocker.patch('trello_sync.services.trello_sync.requests.Session')
    mock_session_instance = MagicMock()
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance
    
    sync = TrelloSync()
    result = sync._request('GET', 'test/endpoint', {'param': 'value'})
    
    assert result == {'id': '123', 'name': 'Test'}
    mock_session_instance.request.assert_called_once()
    call_args = mock_session_instance.request.call_args
    assert call_args[0][0] == 'GET'
    assert 'key' in call_args[1]['params']
    assert 'token' in call_args[1]['params']


@patch('trello_sync.services.trello_sync.get_credentials')
def test_should_sync_card_new_file(mock_get_creds: MagicMock, tmp_path: "pytest.TempPathFactory") -> None:
    """Test should_sync_card for new file."""
    mock_get_creds.return_value = ('test_key', 'test_token')
    
    sync = TrelloSync()
    card_path = tmp_path / "nonexistent.md"
    
    assert sync.should_sync_card(card_path, "2024-01-20T12:00:00Z") is True


@patch('trello_sync.services.trello_sync.get_credentials')
def test_should_sync_card_older_file(mock_get_creds: MagicMock, tmp_path: "pytest.TempPathFactory") -> None:
    """Test should_sync_card for older file."""
    from datetime import datetime
    
    mock_get_creds.return_value = ('test_key', 'test_token')
    
    sync = TrelloSync()
    card_path = tmp_path / "existing.md"
    card_path.write_text("content")
    
    # Set file modification time to be older than card update
    old_time = datetime(2020, 1, 1, 12, 0, 0).timestamp()
    card_path.touch()
    import os
    os.utime(card_path, (old_time, old_time))
    
    # File is older than card update (2025 is in the future)
    assert sync.should_sync_card(card_path, "2025-01-20T12:00:00Z") is True


@patch('trello_sync.services.trello_sync.get_credentials')
def test_should_sync_card_newer_file(mock_get_creds: MagicMock, tmp_path: "pytest.TempPathFactory") -> None:
    """Test should_sync_card for newer file."""
    mock_get_creds.return_value = ('test_key', 'test_token')
    
    sync = TrelloSync()
    card_path = tmp_path / "existing.md"
    card_path.write_text("content")
    
    # File is newer than card update (should not sync)
    assert sync.should_sync_card(card_path, "2020-01-20T12:00:00Z") is False

