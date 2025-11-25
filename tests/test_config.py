"""Tests for configuration utilities."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from trello_sync.utils.config import (
    ConfigError,
    get_board_config,
    get_config_path,
    get_obsidian_root,
    load_config,
    resolve_path_template,
    save_config,
    validate_config,
)


def test_resolve_path_template() -> None:
    """Test path template resolution."""
    template = "20_tasks/Trello/{org}/{board}/{column}/{card}.md"
    variables = {
        'org': 'test-org',
        'board': 'test-board',
        'column': 'test-column',
        'card': 'test-card',
    }
    
    result = resolve_path_template(template, variables)
    assert result == "20_tasks/Trello/test-org/test-board/test-column/test-card.md"


def test_load_config_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config when file doesn't exist."""
    monkeypatch.chdir(tmp_path)
    
    config = load_config()
    
    assert config['obsidian_root'] is None
    assert config['default_assets_folder'] == '.local_assets/Trello'
    assert config['boards'] == []


def test_load_config_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config from existing file."""
    monkeypatch.chdir(tmp_path)
    
    config_data = {
        'obsidian_root': '/test/obsidian',
        'default_assets_folder': '.test_assets',
        'boards': [
            {
                'board_id': 'board123',
                'enabled': True,
                'target_path': 'test/{board}/{card}.md',
            }
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    config = load_config()
    
    assert config['obsidian_root'] == '/test/obsidian'
    assert config['default_assets_folder'] == '.test_assets'
    assert len(config['boards']) == 1
    assert config['boards'][0]['board_id'] == 'board123'


def test_get_board_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting board configuration."""
    monkeypatch.chdir(tmp_path)
    
    config_data = {
        'boards': [
            {
                'board_id': 'board123',
                'enabled': True,
                'target_path': 'test/{board}/{card}.md',
            },
            {
                'board_id': 'board456',
                'enabled': False,
            },
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    board_config = get_board_config('board123')
    assert board_config is not None
    assert board_config['board_id'] == 'board123'
    assert board_config['enabled'] is True
    
    board_config = get_board_config('board456')
    assert board_config is not None
    assert board_config['enabled'] is False
    
    board_config = get_board_config('nonexistent')
    assert board_config is None


def test_get_obsidian_root_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting Obsidian root from environment variable."""
    monkeypatch.chdir(tmp_path)
    
    obsidian_path = tmp_path / 'obsidian'
    obsidian_path.mkdir()
    
    monkeypatch.setenv('OBSIDIAN_ROOT', str(obsidian_path))
    
    result = get_obsidian_root()
    assert result == obsidian_path


def test_get_obsidian_root_from_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting Obsidian root from config file."""
    monkeypatch.chdir(tmp_path)
    
    obsidian_path = tmp_path / 'obsidian'
    obsidian_path.mkdir()
    
    config_data = {
        'obsidian_root': str(obsidian_path),
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    result = get_obsidian_root()
    assert result == obsidian_path


def test_get_obsidian_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting Obsidian root when not configured."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('OBSIDIAN_ROOT', raising=False)
    
    with pytest.raises(ConfigError, match="OBSIDIAN_ROOT not set"):
        get_obsidian_root()


def test_get_obsidian_root_nonexistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting Obsidian root when path doesn't exist."""
    monkeypatch.chdir(tmp_path)
    
    nonexistent_path = tmp_path / 'nonexistent'
    monkeypatch.setenv('OBSIDIAN_ROOT', str(nonexistent_path))
    
    with pytest.raises(ConfigError, match="does not exist"):
        get_obsidian_root()


def test_validate_config_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validating valid configuration."""
    monkeypatch.chdir(tmp_path)
    
    config_data = {
        'boards': [
            {
                'board_id': 'board123',
                'target_path': 'test/{org}/{board}/{column}/{card}.md',
            }
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    errors = validate_config()
    assert len(errors) == 0


def test_validate_config_missing_variables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validating config with missing template variables."""
    monkeypatch.chdir(tmp_path)
    
    config_data = {
        'boards': [
            {
                'board_id': 'board123',
                'target_path': 'test/{org}/{board}.md',  # Missing {column} and {card}
            }
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    errors = validate_config()
    assert len(errors) > 0
    assert any('{column}' in error for error in errors)
    assert any('{card}' in error for error in errors)


def test_validate_config_missing_board_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test validating config with missing board_id."""
    monkeypatch.chdir(tmp_path)
    
    config_data = {
        'boards': [
            {
                'target_path': 'test/{org}/{board}/{column}/{card}.md',
            }
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    errors = validate_config()
    assert len(errors) > 0
    assert any('board_id' in error.lower() for error in errors)


def test_save_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test saving configuration with proper formatting."""
    monkeypatch.chdir(tmp_path)
    
    config = {
        'obsidian_root': '/test/obsidian',
        'default_assets_folder': '.test_assets',
        'boards': [
            {
                'board_id': 'board123',
                'board_name': 'Test Board',
                'org': 'Test Org',
                'enabled': True,
                'target_path': 'test/{org}/{board}/{column}/{card}.md',
                'workspace_name': 'Test Workspace',
            },
            {
                'board_id': 'board456',
                'board_name': 'Another Board',
                'enabled': False,
                'target_path': 'test/{org}/{board}/{column}/{card}.md',
                'workspace_name': '',
            },
        ],
    }
    
    save_config(config)
    
    # Verify file was created
    config_file = tmp_path / 'trello-sync.yaml'
    assert config_file.exists()
    
    # Load and verify
    saved_config = load_config()
    assert saved_config['obsidian_root'] == '/test/obsidian'
    assert saved_config['default_assets_folder'] == '.test_assets'
    assert len(saved_config['boards']) == 2
    
    # Verify first board
    board1 = saved_config['boards'][0]
    assert board1['board_id'] == 'board123'
    assert board1['board_name'] == 'Test Board'
    assert board1['org'] == 'Test Org'
    assert board1['enabled'] is True
    assert board1['workspace_name'] == 'Test Workspace'
    
    # Verify second board
    board2 = saved_config['boards'][1]
    assert board2['board_id'] == 'board456'
    assert board2['board_name'] == 'Another Board'
    assert board2['enabled'] is False
    assert board2['workspace_name'] == ''


def test_save_config_preserves_formatting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that save_config preserves existing board configurations."""
    monkeypatch.chdir(tmp_path)
    
    # Create initial config
    initial_config = {
        'obsidian_root': '/test/obsidian',
        'default_assets_folder': '.test_assets',
        'boards': [
            {
                'board_id': 'board123',
                'board_name': 'Test Board',
                'enabled': True,
                'target_path': 'custom/path/{org}/{board}/{column}/{card}.md',
                'assets_folder': 'custom/assets/{org}/{board}',
            },
        ],
    }
    
    save_config(initial_config)
    
    # Load and modify
    config = load_config()
    config['boards'][0]['board_name'] = 'Updated Board Name'
    
    # Save again
    save_config(config)
    
    # Verify custom settings were preserved
    saved_config = load_config()
    board = saved_config['boards'][0]
    assert board['board_name'] == 'Updated Board Name'
    assert board['enabled'] is True
    assert board['target_path'] == 'custom/path/{org}/{board}/{column}/{card}.md'
    assert board['assets_folder'] == 'custom/assets/{org}/{board}'

