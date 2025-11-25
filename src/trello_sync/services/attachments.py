"""Attachment download and management service."""

import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

# Image extensions that should be rendered inline
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}


def is_image_file(filename: str | None, mime_type: str | None = None) -> bool:
    """Check if a file is an image based on extension or MIME type.

    Args:
        filename: File name or path.
        mime_type: Optional MIME type.

    Returns:
        True if file is an image, False otherwise.
    """
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return True

    if mime_type:
        return mime_type.startswith('image/')

    return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename safe for filesystem.
    """
    # Remove path components
    filename = Path(filename).name

    # Replace problematic characters
    filename = filename.replace(' ', '-')
    filename = ''.join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in filename)

    # Remove multiple underscores/hyphens
    while '--' in filename:
        filename = filename.replace('--', '-')
    while '__' in filename:
        filename = filename.replace('__', '_')

    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:200 - len(ext) - 1] + '.' + ext if ext else name[:200]

    return filename or 'attachment'


def get_unique_filename(target_dir: Path, filename: str) -> Path:
    """Get a unique filename in target directory, appending counter if needed.

    Args:
        target_dir: Target directory.
        filename: Desired filename.

    Returns:
        Path to unique filename.
    """
    target_path = target_dir / filename
    if not target_path.exists():
        return target_path

    # Append counter
    stem = target_path.stem
    suffix = target_path.suffix
    counter = 1
    while True:
        new_filename = f"{stem}_{counter}{suffix}"
        new_path = target_dir / new_filename
        if not new_path.exists():
            return new_path
        counter += 1
        if counter > 1000:  # Safety limit
            raise ValueError(f"Could not find unique filename for {filename}")


def download_attachment(
    attachment_data: dict[str, Any],
    target_path: Path,
    api_key: str,
    token: str,
) -> Path:
    """Download attachment from Trello to target path.

    Args:
        attachment_data: Trello attachment dictionary.
        target_path: Target file path.
        api_key: Trello API key.
        token: Trello API token.

    Returns:
        Path to downloaded file.

    Raises:
        requests.HTTPError: If download fails.
        IOError: If file cannot be written.
    """
    url = attachment_data.get('url')
    if not url:
        raise ValueError("Attachment has no URL")

    # Ensure target directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Download file
    params = {'key': api_key, 'token': token}
    response = requests.get(url, params=params, stream=True, timeout=30)
    response.raise_for_status()

    # Write to file
    with open(target_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return target_path


def get_asset_path(
    card_path: Path,
    attachment_name: str,
    assets_folder: Path,
) -> tuple[Path, str]:
    """Calculate asset path and relative path from card to asset.

    Args:
        card_path: Path to the card markdown file.
        attachment_name: Name of the attachment file.
        assets_folder: Base assets folder path.

    Returns:
        Tuple of (absolute asset path, relative path from card to asset).
    """
    # Sanitize attachment name
    sanitized_name = sanitize_filename(attachment_name)

    # Get unique filename in assets folder
    asset_path = get_unique_filename(assets_folder, sanitized_name)

    # Calculate relative path from card to asset
    try:
        relative_path = Path(asset_path).relative_to(card_path.parent)
        relative_str = str(relative_path).replace('\\', '/')
    except ValueError:
        # If paths are on different drives, use absolute path
        relative_str = str(asset_path)

    return asset_path, relative_str


def process_attachments(
    attachments: list[dict[str, Any]],
    card_path: Path,
    assets_folder: Path,
    api_key: str,
    token: str,
) -> list[dict[str, Any]]:
    """Process attachments: download files and prepare metadata.

    Args:
        attachments: List of Trello attachment dictionaries.
        card_path: Path to the card markdown file.
        assets_folder: Base assets folder for storing attachments.
        api_key: Trello API key.
        token: Trello API token.

    Returns:
        List of processed attachment dictionaries with local_path and is_image fields.
    """
    processed: list[dict[str, Any]] = []

    for attachment in attachments:
        # Only process uploaded files, not links
        if not attachment.get('isUpload', False):
            processed.append(attachment)
            continue

        attachment_name = attachment.get('name', 'untitled')
        mime_type = attachment.get('mimeType', '')
        url = attachment.get('url', '')

        if not url:
            processed.append(attachment)
            continue

        try:
            # Calculate asset path
            asset_path, relative_path = get_asset_path(
                card_path,
                attachment_name,
                assets_folder,
            )

            # Download attachment
            download_attachment(attachment, asset_path, api_key, token)

            # Determine if it's an image
            is_image = is_image_file(attachment_name, mime_type)

            # Create processed attachment dict
            processed_attachment = attachment.copy()
            processed_attachment['local_path'] = relative_path
            processed_attachment['is_image'] = is_image
            processed_attachment['asset_path'] = str(asset_path)

            processed.append(processed_attachment)

        except Exception as e:
            # Log error but continue with other attachments
            # Store error in attachment dict for markdown generation
            processed_attachment = attachment.copy()
            processed_attachment['download_error'] = str(e)
            processed.append(processed_attachment)

    return processed

