"""Formatting utility functions for file names and dates."""

from datetime import datetime


def sanitize_file_name(name: str | None) -> str:
    """Convert name to filesystem-safe name.

    Args:
        name: The name to sanitize.

    Returns:
        A sanitized filesystem-safe name, or 'untitled' if name is invalid.
    """
    if not name or not isinstance(name, str):
        return 'untitled'
    
    name = name.lower().strip()
    # Remove special chars except spaces and hyphens
    name = ''.join(c if c.isalnum() or c in (' ', '-') else '' for c in name)
    # Replace spaces with hyphens
    name = name.replace(' ', '-')
    # Replace multiple hyphens with single
    while '--' in name:
        name = name.replace('--', '-')
    # Remove leading/trailing hyphens
    name = name.strip('-')
    # Limit length
    name = name[:100] if len(name) > 100 else name
    return name or 'untitled'


def format_iso_date(date_str: str | None) -> str | None:
    """Format date to ISO 8601 format.

    Args:
        date_str: Date string to format, can be None.

    Returns:
        ISO 8601 formatted date string, or None if date_str is None or invalid.
    """
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.isoformat().replace('+00:00', 'Z')
    except (ValueError, AttributeError):
        return date_str


def format_date(date_str: str | None) -> str:
    """Format date for display.

    Args:
        date_str: Date string to format, can be None.

    Returns:
        Formatted date string in 'Mon DD, YYYY, HH:MM AM/PM' format,
        or empty string if date_str is None or invalid.
    """
    if not date_str:
        return ''
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y, %I:%M %p')
    except (ValueError, AttributeError):
        return date_str


def format_bytes(bytes_val: int | None) -> str:
    """Format bytes to human readable format.

    Args:
        bytes_val: Number of bytes to format, can be None.

    Returns:
        Human readable string (e.g., "1.5 MB"), or empty string if bytes_val is None.
    """
    if not bytes_val:
        return ''
    val = float(bytes_val)
    for unit in ['Bytes', 'KB', 'MB', 'GB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} TB"

