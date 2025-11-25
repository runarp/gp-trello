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
    ext = Path(filename).suffix.lower()
    
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
    card_id: str | None = None,
    session: requests.Session | None = None,
) -> Path:
    """Download an attachment from Trello.

    Args:
        attachment_data: Attachment data from Trello API.
        target_path: Where to save the file.
        api_key: Trello API key.
        token: Trello API token.
        card_id: Optional card ID (used to construct API endpoint if URL fails).
        session: Optional requests session to use for authenticated requests.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.HTTPError: If the download fails.
        IOError: If the file cannot be written.
    """
    attachment_id = attachment_data.get('id')
    attachment_name = attachment_data.get('name', 'untitled')
    
    if not attachment_id:
        raise ValueError("Attachment data missing 'id' field")
    
    # Create parent directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try multiple approaches to download the attachment
    url = attachment_data.get('url', '')
    
    # Strategy 1: Use the attachment URL provided by Trello (if it has auth params, use as-is)
    # Strategy 2: Try API endpoint without filename
    # Strategy 3: Try API endpoint with filename
    
    from urllib.parse import urlparse, parse_qs, quote
    
    # First, try the provided URL if it exists
    if url:
        parsed = urlparse(url)
        existing_params = parse_qs(parsed.query)
        
        # If URL already has key/token, use it as-is (these are pre-authenticated URLs)
        if 'key' in existing_params and 'token' in existing_params:
            try:
                # Use session if provided, otherwise create new request
                if session:
                    response = session.get(url, stream=True, timeout=30)
                else:
                    response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
            except requests.HTTPError:
                # If pre-authenticated URL fails, try other methods
                url = None  # Mark as failed so we try alternatives
    
    # If URL approach didn't work or wasn't available, try API endpoints
    if not url or (url and 'key' not in parse_qs(urlparse(url).query)):
        # Try API endpoint without filename first (simpler, more reliable)
        if card_id:
            # Method 1: Try endpoint without filename
            api_url_no_filename = f"https://api.trello.com/1/cards/{card_id}/attachments/{attachment_id}"
            params = {'key': api_key, 'token': token}
            
            try:
                # Get attachment metadata first
                meta_response = requests.get(api_url_no_filename, params=params, timeout=30)
                meta_response.raise_for_status()
                attachment_meta = meta_response.json()
                
                # Get the download URL from metadata
                download_url = attachment_meta.get('url')
                if download_url:
                    # Use the URL from metadata (it should be pre-authenticated)
                    parsed = urlparse(download_url)
                    existing_params = parse_qs(parsed.query)
                    if session:
                        if 'key' in existing_params and 'token' in existing_params:
                            response = session.get(download_url, stream=True, timeout=30)
                        else:
                            response = session.get(download_url, params=params, stream=True, timeout=30)
                    else:
                        if 'key' in existing_params and 'token' in existing_params:
                            response = requests.get(download_url, stream=True, timeout=30)
                        else:
                            response = requests.get(download_url, params=params, stream=True, timeout=30)
                    response.raise_for_status()
                else:
                    raise ValueError("No download URL in attachment metadata")
            except (requests.HTTPError, ValueError, KeyError):
                # Method 2: Try direct download endpoint with filename
                encoded_filename = quote(attachment_name, safe='')
                api_url_with_filename = f"https://api.trello.com/1/cards/{card_id}/attachments/{attachment_id}/download/{encoded_filename}"
                try:
                    if session:
                        response = session.get(api_url_with_filename, params=params, stream=True, timeout=30)
                    else:
                        response = requests.get(api_url_with_filename, params=params, stream=True, timeout=30)
                    response.raise_for_status()
                except requests.HTTPError:
                    # Method 3: Try without encoding the filename
                    api_url_plain = f"https://api.trello.com/1/cards/{card_id}/attachments/{attachment_id}/download/{attachment_name}"
                    if session:
                        response = session.get(api_url_plain, params=params, stream=True, timeout=30)
                    else:
                        response = requests.get(api_url_plain, params=params, stream=True, timeout=30)
                    response.raise_for_status()
        else:
            # No card_id, must use URL
            if not url:
                raise ValueError("Attachment data missing 'url' field and card_id not provided")
            
            # Add auth params if not present
            parsed = urlparse(url)
            existing_params = parse_qs(parsed.query)
            if session:
                if 'key' not in existing_params or 'token' not in existing_params:
                    params = {'key': api_key, 'token': token}
                    response = session.get(url, params=params, stream=True, timeout=30)
                else:
                    response = session.get(url, stream=True, timeout=30)
            else:
                if 'key' not in existing_params or 'token' not in existing_params:
                    params = {'key': api_key, 'token': token}
                    response = requests.get(url, params=params, stream=True, timeout=30)
                else:
                    response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
    
    # Write file
    with open(target_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
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

