"""Configuration utilities for Trello sync."""

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when there's an error with configuration."""

    pass


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to trello-sync.yaml in the project root.
    """
    # Look for config in current directory or parent directories
    current = Path.cwd()
    for path in [current, current.parent]:
        config_file = path / 'trello-sync.yaml'
        if config_file.exists():
            return config_file
    # Default to current directory
    return current / 'trello-sync.yaml'


def load_config() -> dict[str, Any]:
    """Load configuration from trello-sync.yaml.

    Returns:
        Configuration dictionary.

    Raises:
        ConfigError: If config file is invalid or missing required fields.
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return {
            'obsidian_root': None,
            'default_assets_folder': '.local_assets/Trello',
            'boards': [],
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        raise ConfigError(f"Error reading config file: {e}")
    
    # Set defaults
    config.setdefault('obsidian_root', None)
    config.setdefault('default_assets_folder', '.local_assets/Trello')
    config.setdefault('boards', [])
    
    return config


def get_obsidian_root() -> Path:
    """Get the Obsidian root path.

    Returns:
        Path to Obsidian root directory.

    Raises:
        ConfigError: If obsidian_root is not configured.
    """
    config = load_config()
    
    # Check environment variable first
    obsidian_root = os.getenv('OBSIDIAN_ROOT')
    
    # Override with config if present
    if config.get('obsidian_root'):
        obsidian_root = config['obsidian_root']
    
    if not obsidian_root:
        raise ConfigError(
            "OBSIDIAN_ROOT not set. Set it as an environment variable or in trello-sync.yaml"
        )
    
    obsidian_path = Path(obsidian_root).expanduser()
    
    if not obsidian_path.exists():
        raise ConfigError(f"Obsidian root path does not exist: {obsidian_path}")
    
    if not obsidian_path.is_dir():
        raise ConfigError(f"Obsidian root path is not a directory: {obsidian_path}")
    
    return obsidian_path


def get_board_config(board_id: str) -> dict[str, Any] | None:
    """Get configuration for a specific board.

    Args:
        board_id: The Trello board ID.

    Returns:
        Board configuration dictionary, or None if not configured.
    """
    config = load_config()
    
    for board_config in config.get('boards', []):
        if board_config.get('board_id') == board_id:
            return board_config
    
    return None


def resolve_path_template(template: str, variables: dict[str, str]) -> str:
    """Resolve a path template with variable substitution.

    Args:
        template: Path template with {variable} placeholders.
        variables: Dictionary of variable names to values.

    Returns:
        Resolved path string.
    """
    result = template
    for key, value in variables.items():
        result = result.replace(f'{{{key}}}', value)
    return result


def validate_config() -> list[str]:
    """Validate configuration file.

    Returns:
        List of error messages (empty if valid).
    """
    errors: list[str] = []
    
    try:
        config = load_config()
    except ConfigError as e:
        return [str(e)]
    
    # Validate board configurations
    boards = config.get('boards', [])
    if not isinstance(boards, list):
        errors.append("'boards' must be a list")
        return errors
    
    for i, board_config in enumerate(boards):
        if not isinstance(board_config, dict):
            errors.append(f"Board config at index {i} must be a dictionary")
            continue
        
        if 'board_id' not in board_config:
            errors.append(f"Board config at index {i} missing 'board_id'")
        
        if 'target_path' in board_config:
            template = board_config['target_path']
            required_vars = ['org', 'board', 'column', 'card']
            for var in required_vars:
                if f'{{{var}}}' not in template:
                    errors.append(
                        f"Board {board_config.get('board_id', 'unknown')} target_path "
                        f"missing required variable: {{{var}}}"
                    )
    
    return errors

