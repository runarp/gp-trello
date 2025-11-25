"""Tests for attachment download service."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from trello_sync.services.attachments import (
    download_attachment,
    get_asset_path,
    get_relative_asset_path,
    get_unique_filename,
    is_image_file,
    sanitize_filename,
)


def test_is_image_file_by_extension() -> None:
    """Test image detection by file extension."""
    assert is_image_file('test.jpg') is True
    assert is_image_file('test.png') is True
    assert is_image_file('test.gif') is True
    assert is_image_file('test.webp') is True
    assert is_image_file('test.svg') is True
    assert is_image_file('test.pdf') is False
    assert is_image_file('test.docx') is False


def test_is_image_file_by_mime_type() -> None:
    """Test image detection by MIME type."""
    assert is_image_file('test', 'image/jpeg') is True
    assert is_image_file('test', 'image/png') is True
    assert is_image_file('test', 'image/gif') is True
    assert is_image_file('test', 'application/pdf') is False


def test_sanitize_filename() -> None:
    """Test filename sanitization."""
    assert sanitize_filename('test file.jpg') == 'test-file.jpg'
    assert sanitize_filename('test@file#123.png') == 'testfile123.png'
    assert sanitize_filename('normal-file.pdf') == 'normal-file.pdf'
    assert sanitize_filename('UPPERCASE.JPG') == 'uppercase.jpg'


def test_get_unique_filename_new_file(tmp_path: Path) -> None:
    """Test getting unique filename for new file."""
    target_dir = tmp_path / 'assets'
    target_dir.mkdir()
    
    result = get_unique_filename(target_dir, 'test.jpg')
    assert result == target_dir / 'test.jpg'


def test_get_unique_filename_existing_file(tmp_path: Path) -> None:
    """Test getting unique filename when file exists."""
    target_dir = tmp_path / 'assets'
    target_dir.mkdir()
    
    # Create existing file
    existing_file = target_dir / 'test.jpg'
    existing_file.write_text('content')
    
    result = get_unique_filename(target_dir, 'test.jpg')
    assert result == target_dir / 'test_1.jpg'
    
    # Create another existing file
    existing_file_1 = target_dir / 'test_1.jpg'
    existing_file_1.write_text('content')
    
    result = get_unique_filename(target_dir, 'test.jpg')
    assert result == target_dir / 'test_2.jpg'


def test_get_asset_path(tmp_path: Path) -> None:
    """Test calculating asset path."""
    card_path = tmp_path / 'cards' / 'test-card.md'
    assets_folder = tmp_path / 'assets'
    
    result = get_asset_path(card_path, 'test-image.png', assets_folder)
    
    assert result.parent == assets_folder
    assert 'test-image' in result.name
    assert result.suffix == '.png'
    assert assets_folder.exists()


def test_get_relative_asset_path() -> None:
    """Test getting relative path from card to asset."""
    card_path = Path('/test/obsidian/20_tasks/Trello/org/board/column/card.md')
    asset_path = Path('/test/obsidian/.local_assets/Trello/org/board/image.png')
    
    result = get_relative_asset_path(card_path, asset_path)
    
    # Should be relative path with forward slashes
    assert '..' in result or '.local_assets' in result
    assert '\\' not in result  # No backslashes


@patch('trello_sync.services.attachments.requests.get')
def test_download_attachment_success(mock_get: MagicMock, tmp_path: Path) -> None:
    """Test successful attachment download."""
    # Mock response
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b'file content']
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    attachment_data = {
        'url': 'https://trello.com/attachments/test.jpg',
        'name': 'test.jpg',
    }
    
    target_path = tmp_path / 'downloaded.jpg'
    
    result = download_attachment(attachment_data, target_path, 'api_key', 'token')
    
    assert result == target_path
    assert target_path.exists()
    assert target_path.read_bytes() == b'file content'
    
    # Verify request was made with auth params
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args[1]
    assert 'key' in call_kwargs['params']
    assert 'token' in call_kwargs['params']


@patch('trello_sync.services.attachments.requests.get')
def test_download_attachment_http_error(mock_get: MagicMock, tmp_path: Path) -> None:
    """Test attachment download with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError('404 Not Found')
    mock_get.return_value = mock_response
    
    attachment_data = {
        'url': 'https://trello.com/attachments/test.jpg',
        'name': 'test.jpg',
    }
    
    target_path = tmp_path / 'downloaded.jpg'
    
    with pytest.raises(requests.HTTPError):
        download_attachment(attachment_data, target_path, 'api_key', 'token')
    
    assert not target_path.exists()


def test_download_attachment_missing_url(tmp_path: Path) -> None:
    """Test attachment download with missing URL."""
    attachment_data = {
        'name': 'test.jpg',
    }
    
    target_path = tmp_path / 'downloaded.jpg'
    
    with pytest.raises(ValueError, match="missing 'url'"):
        download_attachment(attachment_data, target_path, 'api_key', 'token')

