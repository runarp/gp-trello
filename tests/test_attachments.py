"""Tests for attachment download service."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from trello_sync.services.attachments import (
    download_attachment,
    get_asset_path,
    get_unique_filename,
    is_image_file,
    process_attachments,
    sanitize_filename,
)


def test_is_image_file_by_extension() -> None:
    """Test image detection by file extension."""
    assert is_image_file('image.png') is True
    assert is_image_file('photo.jpg') is True
    assert is_image_file('document.pdf') is False


def test_is_image_file_by_mime_type() -> None:
    """Test image detection by MIME type."""
    assert is_image_file('file', 'image/png') is True
    assert is_image_file('file', 'application/pdf') is False


def test_sanitize_filename() -> None:
    """Test filename sanitization."""
    assert sanitize_filename('test file.pdf') == 'test-file.pdf'
    assert sanitize_filename('file@#$name.png') == 'file___name.png'
    assert sanitize_filename('/path/to/file.txt') == 'file.txt'


def test_get_unique_filename_new_file(tmp_path: Path) -> None:
    """Test getting unique filename for new file."""
    target_dir = tmp_path / "assets"
    target_dir.mkdir()
    
    filename = get_unique_filename(target_dir, "test.pdf")
    assert filename == target_dir / "test.pdf"


def test_get_unique_filename_existing_file(tmp_path: Path) -> None:
    """Test getting unique filename when file exists."""
    target_dir = tmp_path / "assets"
    target_dir.mkdir()
    (target_dir / "test.pdf").touch()
    
    filename = get_unique_filename(target_dir, "test.pdf")
    assert filename == target_dir / "test_1.pdf"


@patch('trello_sync.services.attachments.requests.get')
def test_download_attachment_success(mock_get, tmp_path: Path) -> None:
    """Test successful attachment download."""
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b'file content']
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    attachment = {'url': 'https://trello.com/attachments/test.pdf'}
    target_path = tmp_path / "test.pdf"
    
    result = download_attachment(attachment, target_path, 'api_key', 'token')
    
    assert result == target_path
    assert target_path.exists()
    assert target_path.read_bytes() == b'file content'
    mock_get.assert_called_once()


def test_get_asset_path(tmp_path: Path) -> None:
    """Test calculating asset path and relative path."""
    card_path = tmp_path / "cards" / "card.md"
    card_path.parent.mkdir(parents=True)
    assets_folder = tmp_path / "assets"
    assets_folder.mkdir()
    
    asset_path, relative_path = get_asset_path(card_path, "image.png", assets_folder)
    
    assert asset_path == assets_folder / "image.png"
    # Relative path should be relative to card's parent directory
    assert relative_path.startswith("../") or relative_path == "assets/image.png"


@patch('trello_sync.services.attachments.download_attachment')
def test_process_attachments_file(mock_download, tmp_path: Path) -> None:
    """Test processing file attachments."""
    card_path = tmp_path / "card.md"
    assets_folder = tmp_path / "assets"
    assets_folder.mkdir()
    
    attachments = [
        {
            'name': 'test.pdf',
            'url': 'https://trello.com/attachments/test.pdf',
            'isUpload': True,
            'mimeType': 'application/pdf',
        },
    ]
    
    mock_download.return_value = assets_folder / "test.pdf"
    
    processed = process_attachments(attachments, card_path, assets_folder, 'api_key', 'token')
    
    assert len(processed) == 1
    assert processed[0]['local_path'] is not None
    assert processed[0]['is_image'] is False
    mock_download.assert_called_once()


@patch('trello_sync.services.attachments.download_attachment')
def test_process_attachments_image(mock_download, tmp_path: Path) -> None:
    """Test processing image attachments."""
    card_path = tmp_path / "card.md"
    assets_folder = tmp_path / "assets"
    assets_folder.mkdir()
    
    attachments = [
        {
            'name': 'image.png',
            'url': 'https://trello.com/attachments/image.png',
            'isUpload': True,
            'mimeType': 'image/png',
        },
    ]
    
    mock_download.return_value = assets_folder / "image.png"
    
    processed = process_attachments(attachments, card_path, assets_folder, 'api_key', 'token')
    
    assert len(processed) == 1
    assert processed[0]['is_image'] is True


def test_process_attachments_link(tmp_path: Path) -> None:
    """Test processing link attachments (not downloaded)."""
    card_path = tmp_path / "card.md"
    assets_folder = tmp_path / "assets"
    
    attachments = [
        {
            'name': 'External Link',
            'url': 'https://example.com',
            'isUpload': False,
        },
    ]
    
    processed = process_attachments(attachments, card_path, assets_folder, 'api_key', 'token')
    
    assert len(processed) == 1
    assert 'local_path' not in processed[0]
    assert 'is_image' not in processed[0]


@patch('trello_sync.services.attachments.download_attachment')
def test_process_attachments_download_error(mock_download, tmp_path: Path) -> None:
    """Test handling download errors."""
    card_path = tmp_path / "card.md"
    assets_folder = tmp_path / "assets"
    assets_folder.mkdir()
    
    attachments = [
        {
            'name': 'test.pdf',
            'url': 'https://trello.com/attachments/test.pdf',
            'isUpload': True,
        },
    ]
    
    mock_download.side_effect = Exception("Download failed")
    
    processed = process_attachments(attachments, card_path, assets_folder, 'api_key', 'token')
    
    assert len(processed) == 1
    assert 'download_error' in processed[0]
    assert processed[0]['download_error'] == "Download failed"

