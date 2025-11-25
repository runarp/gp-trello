"""Tests for configuration utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from trello_sync.utils.config import (
    ConfigError,
    get_board_config,
    get_obsidian_root,
    get_obsidian_root_path,
    load_config,
    resolve_path_template,
    validate_config,
)


def test_load_config_nonexistent(tmp_path: Path) -> None:
    """Test loading config from nonexistent file."""
    config_path = tmp_path / "nonexistent.yaml"
    config = load_config(config_path)
    assert config == {}


def test_load_config_valid(tmp_path: Path) -> None:
    """Test loading valid config file."""
    config_path = tmp_path / "trello-sync.yaml"
    config_data = {
        'obsidian_root': '/path/to/obsidian',
        'boards': [
            {'board_id': 'test123', 'enabled': True, 'target_path': 'path/{board}/{card}.md'},
        ],
    }
    config_path.write_text(yaml.dump(config_data), encoding='utf-8')
    
    config = load_config(config_path)
    assert config['obsidian_root'] == '/path/to/obsidian'
    assert len(config['boards']) == 1


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Test loading invalid YAML file."""
    config_path = tmp_path / "trello-sync.yaml"
    config_path.write_text("invalid: yaml: content: [", encoding='utf-8')
    
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(config_path)


def test_validate_config_valid() -> None:
    """Test validating valid config."""
    config = {
        'obsidian_root': '/path/to/obsidian',
        'boards': [
            {
                'board_id': 'test123',
                'enabled': True,
                'target_path': 'path/{org}/{board}/{column}/{card}.md',
            },
        ],
    }
    errors = validate_config(config)
    assert errors == []


def test_validate_config_missing_board_id() -> None:
    """Test validating config with missing board_id."""
    config = {
        'boards': [
            {'enabled': True},
        ],
    }
    errors = validate_config(config)
    assert any('board_id' in error for error in errors)


def test_validate_config_missing_template_vars() -> None:
    """Test validating config with missing template variables."""
    config = {
        'boards': [
            {
                'board_id': 'test123',
                'target_path': 'path/{board}.md',  # Missing {org}, {column}, {card}
            },
        ],
    }
    errors = validate_config(config)
    assert len(errors) > 0
    assert any('{org}' in error for error in errors)


def test_get_board_config_found() -> None:
    """Test getting board config that exists."""
    config = {
        'boards': [
            {'board_id': 'test123', 'enabled': True, 'target_path': 'path/{board}/{card}.md'},
            {'board_id': 'test456', 'enabled': False},
        ],
    }
    
    board_config = get_board_config('test123', config)
    assert board_config is not None
    assert board_config['board_id'] == 'test123'
    assert board_config['enabled'] is True


def test_get_board_config_disabled() -> None:
    """Test getting board config that is disabled."""
    config = {
        'boards': [
            {'board_id': 'test123', 'enabled': False},
        ],
    }
    
    board_config = get_board_config('test123', config)
    assert board_config is None


def test_get_board_config_not_found() -> None:
    """Test getting board config that doesn't exist."""
    config = {
        'boards': [
            {'board_id': 'test123', 'enabled': True},
        ],
    }
    
    board_config = get_board_config('nonexistent', config)
    assert board_config is None


def test_resolve_path_template() -> None:
    """Test resolving path template."""
    template = "path/{org}/{board}/{column}/{card}.md"
    variables = {
        'org': 'My Org',
        'board': 'My Board',
        'column': 'My Column',
        'card': 'My Card',
    }
    
    result = resolve_path_template(template, variables)
    assert result == "path/My Org/My Board/My Column/My Card.md"


def test_resolve_path_template_with_sanitize() -> None:
    """Test resolving path template with sanitization."""
    def sanitize(value: str) -> str:
        return value.lower().replace(' ', '-')
    
    template = "path/{org}/{board}.md"
    variables = {
        'org': 'My Org',
        'board': 'My Board',
    }
    
    result = resolve_path_template(template, variables, sanitize_func=sanitize)
    assert result == "path/my-org/my-board.md"


@patch('trello_sync.utils.config.os.getenv')
def test_get_obsidian_root_from_env(mock_getenv) -> None:
    """Test getting Obsidian root from environment variable."""
    mock_getenv.return_value = '/path/to/obsidian'
    
    root = get_obsidian_root()
    assert root == Path('/path/to/obsidian').expanduser().resolve()


@patch('trello_sync.utils.config.os.getenv')
def test_get_obsidian_root_not_set(mock_getenv) -> None:
    """Test getting Obsidian root when not set."""
    mock_getenv.return_value = None
    
    root = get_obsidian_root()
    assert root is None


def test_get_obsidian_root_path_from_config() -> None:
    """Test getting Obsidian root path from config."""
    config = {'obsidian_root': '/path/to/obsidian'}
    
    with patch('trello_sync.utils.config.load_config', return_value=config):
        root = get_obsidian_root_path()
        assert root == Path('/path/to/obsidian').expanduser().resolve()


@patch('trello_sync.utils.config.get_obsidian_root')
def test_get_obsidian_root_path_from_env(mock_get_obsidian) -> None:
    """Test getting Obsidian root path from environment."""
    mock_get_obsidian.return_value = Path('/path/to/obsidian')
    
    with patch('trello_sync.utils.config.load_config', return_value={}):
        root = get_obsidian_root_path()
        assert root == Path('/path/to/obsidian')


def test_get_obsidian_root_path_not_configured() -> None:
    """Test getting Obsidian root path when not configured."""
    with patch('trello_sync.utils.config.load_config', return_value={}):
        with patch('trello_sync.utils.config.get_obsidian_root', return_value=None):
            with pytest.raises(ConfigError, match="Obsidian root not configured"):
                get_obsidian_root_path()

