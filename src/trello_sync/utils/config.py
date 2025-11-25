"""Configuration utilities for Trello sync."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE_NAME = 'trello-sync.yaml'


class ConfigError(Exception):
    """Configuration error."""

    pass


def get_obsidian_root() -> Path | None:
    """Get Obsidian root path from environment or config.

    Returns:
        Path to Obsidian root, or None if not set.
    """
    obsidian_root = os.getenv('OBSIDIAN_ROOT')
    if obsidian_root:
        return Path(obsidian_root).expanduser().resolve()
    return None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load and parse YAML configuration file.

    Args:
        config_path: Optional path to config file. Defaults to trello-sync.yaml in project root.

    Returns:
        Configuration dictionary.

    Raises:
        ConfigError: If config file is invalid or cannot be read.
    """
    if config_path is None:
        # Look for config in current directory or project root
        current_dir = Path.cwd()
        config_path = current_dir / CONFIG_FILE_NAME
        if not config_path.exists():
            # Try parent directories up to 3 levels
            for parent in current_dir.parents[:3]:
                candidate = parent / CONFIG_FILE_NAME
                if candidate.exists():
                    config_path = candidate
                    break

    if not config_path.exists():
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e
    except Exception as e:
        raise ConfigError(f"Error reading config file: {e}") from e


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration structure.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        List of validation error messages. Empty list if valid.
    """
    errors: list[str] = []

    if not isinstance(config, dict):
        errors.append("Config must be a dictionary")
        return errors

    # Validate boards list
    if 'boards' in config:
        if not isinstance(config['boards'], list):
            errors.append("'boards' must be a list")
        else:
            for i, board in enumerate(config['boards']):
                if not isinstance(board, dict):
                    errors.append(f"Board {i} must be a dictionary")
                    continue

                if 'board_id' not in board:
                    errors.append(f"Board {i} missing required field 'board_id'")

                if 'enabled' in board and not isinstance(board['enabled'], bool):
                    errors.append(f"Board {i} 'enabled' must be a boolean")

                if 'target_path' in board:
                    if not isinstance(board['target_path'], str):
                        errors.append(f"Board {i} 'target_path' must be a string")
                    # Check for required template variables
                    required_vars = ['{org}', '{board}', '{column}', '{card}']
                    for var in required_vars:
                        if var not in board['target_path']:
                            errors.append(
                                f"Board {i} 'target_path' must contain {var}"
                            )

    # Validate obsidian_root if present
    if 'obsidian_root' in config and config['obsidian_root'] is not None:
        if not isinstance(config['obsidian_root'], str):
            errors.append("'obsidian_root' must be a string or null")

    # Validate default_assets_folder if present
    if 'default_assets_folder' in config:
        if not isinstance(config['default_assets_folder'], str):
            errors.append("'default_assets_folder' must be a string")

    return errors


def get_board_config(board_id: str, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Get board-specific configuration.

    Args:
        board_id: The Trello board ID.
        config: Optional configuration dictionary. If not provided, loads from file.

    Returns:
        Board configuration dictionary, or None if not found or disabled.
    """
    if config is None:
        config = load_config()

    boards = config.get('boards', [])
    for board_config in boards:
        if board_config.get('board_id') == board_id:
            # Check if enabled (defaults to True if not specified)
            if not board_config.get('enabled', True):
                return None
            return board_config

    return None


def resolve_path_template(
    template: str,
    variables: dict[str, str],
    sanitize_func: Callable[[str], str] | None = None,
) -> str:
    """Resolve path template with variable substitution.

    Args:
        template: Path template with {variable} placeholders.
        variables: Dictionary of variable names (without braces) to values.
        sanitize_func: Optional function to sanitize variable values.

    Returns:
        Resolved path string.
    """
    result = template
    for var_name, var_value in variables.items():
        # Sanitize if function provided
        if sanitize_func:
            var_value = sanitize_func(var_value)
        # Replace {var_name} with value
        result = result.replace(f'{{{var_name}}}', var_value)
    return result


def get_obsidian_root_path(config: dict[str, Any] | None = None) -> Path:
    """Get Obsidian root path, resolving from config or environment.

    Args:
        config: Optional configuration dictionary.

    Returns:
        Path to Obsidian root.

    Raises:
        ConfigError: If Obsidian root is not configured.
    """
    if config is None:
        config = load_config()

    # Check config first
    obsidian_root = config.get('obsidian_root')
    if obsidian_root:
        return Path(obsidian_root).expanduser().resolve()

    # Check environment variable
    obsidian_root = get_obsidian_root()
    if obsidian_root:
        return obsidian_root

    raise ConfigError(
        "Obsidian root not configured. Set OBSIDIAN_ROOT environment variable "
        "or 'obsidian_root' in trello-sync.yaml"
    )

