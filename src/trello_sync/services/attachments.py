"""Attachment download service for Trello cards."""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from trello_sync.utils.formatting import sanitize_file_name


def is_image_file(filename: str, mime_type: str | None = None) -> bool:
    """Check if a file is an image based on extension or MIME type.

    Args:
        filename: The filename to check.
        mime_type: Optional MIME type of the file.

    Returns:
        True if the file is an image, False otherwise.
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
    image_mime_types = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'image/svg+xml', 'image/bmp', 'image/x-icon', 'image/vnd.microsoft.icon'
    }
    
    # Check by extension
    ext = Path(filename).suffix.lower()
    if ext in image_extensions:
        return True
    
    # Check by MIME type
    if mime_type and mime_type.lower() in image_mime_types:
        return True
    
    return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for filesystem storage.

    Args:
        filename: The original filename.

    Returns:
        Sanitized filename safe for filesystem.
    """
    # Use the existing sanitize_file_name but preserve extension
    name = Path(filename).stem
    ext = Path(filename).suffix
    
    sanitized_name = sanitize_file_name(name)
    
    # Sanitize extension too
    sanitized_ext = ''.join(c if c.isalnum() or c in ('.', '-', '_') else '' for c in ext)
    
    return sanitized_name + sanitized_ext


def get_unique_filename(target_dir: Path, filename: str) -> Path:
    """Get a unique filename in the target directory.

    If the file already exists, append a counter.

    Args:
        target_dir: The target directory.
        filename: The desired filename.

    Returns:
        Path to a unique filename.
    """
    target_path = target_dir / filename
    
    if not target_path.exists():
        return target_path
    
    # File exists, append counter
    stem = target_path.stem
    ext = target_path.suffix
    counter = 1
    
    while True:
        new_filename = f"{stem}_{counter}{ext}"
        new_path = target_dir / new_filename
        if not new_path.exists():
            return new_path
        counter += 1


def download_attachment(
    attachment_data: dict[str, Any],
    target_path: Path,
    api_key: str,
    token: str,
) -> Path:
    """Download an attachment from Trello.

    Args:
        attachment_data: Attachment data from Trello API.
        target_path: Where to save the file.
        api_key: Trello API key.
        token: Trello API token.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.HTTPError: If the download fails.
        IOError: If the file cannot be written.
    """
    url = attachment_data.get('url')
    if not url:
        raise ValueError("Attachment data missing 'url' field")
    
    # Create parent directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download file
    params = {'key': api_key, 'token': token}
    response = requests.get(url, params=params, stream=True)
    response.raise_for_status()
    
    # Write file
    with open(target_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return target_path


def get_asset_path(
    card_path: Path,
    attachment_name: str,
    assets_folder: Path,
) -> Path:
    """Calculate the path for an attachment asset.

    Args:
        card_path: Path to the card markdown file.
        attachment_name: Name of the attachment file.
        assets_folder: Base assets folder path.

    Returns:
        Path where the attachment should be stored.
    """
    # Sanitize the attachment name
    sanitized_name = sanitize_filename(attachment_name)
    
    # Ensure assets folder exists
    assets_folder.mkdir(parents=True, exist_ok=True)
    
    # Return path in assets folder
    return assets_folder / sanitized_name


def get_relative_asset_path(card_path: Path, asset_path: Path) -> str:
    """Get relative path from card to asset for markdown links.

    Args:
        card_path: Path to the card markdown file.
        asset_path: Path to the asset file.

    Returns:
        Relative path string suitable for markdown.
    """
    try:
        # Get relative path
        relative = os.path.relpath(asset_path, card_path.parent)
        # Normalize path separators for markdown (use forward slashes)
        return relative.replace('\\', '/')
    except ValueError:
        # If paths are on different drives (Windows), return absolute path
        return str(asset_path)

