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


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to trello-sync.yaml with proper formatting.

    Args:
        config: Configuration dictionary to save.
    """
    config_path = get_config_path()
    
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        # Write header comments
        f.write("# Trello Sync Configuration\n")
        f.write("# Copy this file to trello-sync.yaml and configure your boards\n\n")
        f.write("# Global settings\n")
        
        # Write global settings
        if 'obsidian_root' in config and config['obsidian_root']:
            f.write(f"obsidian_root: {config['obsidian_root']}\n")
        if 'default_assets_folder' in config:
            f.write(f"default_assets_folder: {config['default_assets_folder']}\n")
        
        f.write("\n# Board mappings\n")
        f.write("# Available settings for each board:\n")
        f.write("#   board_id: (required) Trello board ID\n")
        f.write("#   board_name: (optional) Board name for reference\n")
        f.write("#   org: (optional) Organization/workspace name for reference\n")
        f.write("#   enabled: (required) true/false to enable/disable syncing\n")
        f.write("#   target_path: (required) Path template for card files\n")
        f.write("#   assets_folder: (optional) Override default assets folder\n")
        f.write("#   workspace_name: (optional) Workspace name for {org} substitution\n")
        f.write("#\n")
        f.write("# Path template variables:\n")
        f.write("#   {org}   - Workspace/organization name (sanitized)\n")
        f.write("#   {board} - Board name (sanitized)\n")
        f.write("#   {column} - List/column name (sanitized)\n")
        f.write("#   {card}  - Card name (sanitized, without .md extension)\n")
        f.write("boards:\n")
        
        # Write board entries with proper indentation
        boards = config.get('boards', []) or []
        for board_config in boards:
            f.write("  - board_id: ")
            f.write(f'"{board_config["board_id"]}"\n')
            
            if 'board_name' in board_config and board_config['board_name']:
                f.write(f'    board_name: "{board_config["board_name"]}"\n')
            
            if 'org' in board_config and board_config['org']:
                f.write(f'    org: "{board_config["org"]}"\n')
            
            f.write(f'    enabled: {str(board_config.get("enabled", False)).lower()}\n')
            
            if 'target_path' in board_config:
                f.write(f'    target_path: "{board_config["target_path"]}"\n')
            
            if 'assets_folder' in board_config and board_config['assets_folder']:
                f.write(f'    assets_folder: "{board_config["assets_folder"]}"\n')
            
            # Always include workspace_name, even if empty
            workspace_name = board_config.get('workspace_name', '')
            if workspace_name:
                f.write(f'    workspace_name: "{workspace_name}"\n')
            else:
                f.write('    workspace_name: ""\n')
            
            f.write("\n")


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

