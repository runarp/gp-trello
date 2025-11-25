"""Tests for config-init CLI command."""

import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from trello_sync.cli.commands import cli


def test_config_init_new_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config-init creates new file when none exists."""
    monkeypatch.chdir(tmp_path)
    
    # Mock Trello API responses
    mock_boards = [
        {'id': 'board1', 'name': 'Board 1'},
        {'id': 'board2', 'name': 'Board 2'},
    ]
    
    mock_board_details = [
        {
            'id': 'board1',
            'name': 'Board 1',
            'organization': {'displayName': 'Org 1'},
        },
        {
            'id': 'board2',
            'name': 'Board 2',
            'organization': None,
        },
    ]
    
    with patch('trello_sync.cli.commands.TrelloSync') as mock_sync_class:
        mock_sync = MagicMock()
        mock_sync.get_boards.return_value = mock_boards
        mock_sync.get_board.side_effect = mock_board_details
        mock_sync_class.return_value = mock_sync
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config-init'])
        
        assert result.exit_code == 0
        assert 'Creating new configuration file' in result.output
        assert 'Found 2 accessible boards' in result.output
        
        # Check file was created
        config_file = tmp_path / 'trello-sync.yaml'
        assert config_file.exists()
        
        # Check config content
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['boards']) == 2
        assert config['boards'][0]['board_id'] == 'board1'
        assert config['boards'][0]['board_name'] == 'Board 1'
        assert config['boards'][0]['org'] == 'Org 1'
        assert config['boards'][0]['enabled'] is False
        assert config['boards'][1]['board_id'] == 'board2'
        assert config['boards'][1]['org'] == ''


def test_config_init_updates_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config-init updates existing file, adding missing boards and removing deleted ones."""
    monkeypatch.chdir(tmp_path)
    
    # Create existing config file
    existing_config = {
        'obsidian_root': '/test/obsidian',
        'default_assets_folder': '.test_assets',
        'boards': [
            {
                'board_id': 'board1',
                'board_name': 'Board 1',
                'enabled': True,
                'target_path': 'custom/path/{org}/{board}/{column}/{card}.md',
                'org': 'Old Org',
            },
            {
                'board_id': 'board2',
                'board_name': 'Board 2',
                'enabled': False,
                'target_path': '20_tasks/Trello/{org}/{board}/{column}/{card}.md',
            },
            {
                'board_id': 'deleted_board',
                'board_name': 'Deleted Board',
                'enabled': True,
            },
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(existing_config, f)
    
    # Mock Trello API - board1 and board2 exist, deleted_board doesn't
    mock_boards = [
        {'id': 'board1', 'name': 'Board 1 Updated'},
        {'id': 'board2', 'name': 'Board 2'},
        {'id': 'board3', 'name': 'New Board 3'},
    ]
    
    mock_board_details = {
        'board1': {
            'id': 'board1',
            'name': 'Board 1 Updated',
            'organization': {'displayName': 'New Org'},
        },
        'board2': {
            'id': 'board2',
            'name': 'Board 2',
            'organization': None,
        },
        'board3': {
            'id': 'board3',
            'name': 'New Board 3',
            'organization': {'displayName': 'Org 3'},
        },
    }
    
    def get_board_side_effect(board_id: str) -> dict:
        return mock_board_details[board_id]
    
    with patch('trello_sync.cli.commands.TrelloSync') as mock_sync_class:
        mock_sync = MagicMock()
        mock_sync.get_boards.return_value = mock_boards
        mock_sync.get_board.side_effect = get_board_side_effect
        mock_sync_class.return_value = mock_sync
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config-init'])
        
        assert result.exit_code == 0
        assert 'Existing boards in config: 3' in result.output
        assert 'Boards to add: 1' in result.output
        assert 'Boards to remove: 1' in result.output
        
        # Check config was updated
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        board_ids = {b['board_id'] for b in config['boards']}
        assert 'board1' in board_ids
        assert 'board2' in board_ids
        assert 'board3' in board_ids
        assert 'deleted_board' not in board_ids
        
        # Check board1 settings were preserved
        board1 = next(b for b in config['boards'] if b['board_id'] == 'board1')
        assert board1['enabled'] is True
        assert board1['target_path'] == 'custom/path/{org}/{board}/{column}/{card}.md'
        assert board1['board_name'] == 'Board 1 Updated'  # Updated name
        assert board1['org'] == 'New Org'  # Updated org
        
        # Check board2 settings were preserved
        board2 = next(b for b in config['boards'] if b['board_id'] == 'board2')
        assert board2['enabled'] is False
        
        # Check new board was added
        board3 = next(b for b in config['boards'] if b['board_id'] == 'board3')
        assert board3['board_name'] == 'New Board 3'
        assert board3['org'] == 'Org 3'
        assert board3['enabled'] is False  # Default for new boards


def test_config_init_force_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config-init --force overwrites existing file."""
    monkeypatch.chdir(tmp_path)
    
    # Create existing config file
    existing_config = {
        'boards': [
            {
                'board_id': 'old_board',
                'board_name': 'Old Board',
                'enabled': True,
            },
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(existing_config, f)
    
    # Mock Trello API
    mock_boards = [
        {'id': 'new_board', 'name': 'New Board'},
    ]
    
    mock_board_details = {
        'new_board': {
            'id': 'new_board',
            'name': 'New Board',
            'organization': None,
        },
    }
    
    with patch('trello_sync.cli.commands.TrelloSync') as mock_sync_class:
        mock_sync = MagicMock()
        mock_sync.get_boards.return_value = mock_boards
        mock_sync.get_board.return_value = mock_board_details['new_board']
        mock_sync_class.return_value = mock_sync
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config-init', '--force'])
        
        assert result.exit_code == 0
        assert 'Creating new configuration file' in result.output
        
        # Check old board was removed
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['boards']) == 1
        assert config['boards'][0]['board_id'] == 'new_board'


def test_config_init_preserves_custom_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config-init preserves custom settings like assets_folder."""
    monkeypatch.chdir(tmp_path)
    
    # Create existing config with custom settings
    existing_config = {
        'boards': [
            {
                'board_id': 'board1',
                'board_name': 'Board 1',
                'enabled': True,
                'target_path': 'custom/path/{org}/{board}/{column}/{card}.md',
                'assets_folder': 'custom/assets/{org}/{board}',
                'org': 'My Org',
            },
        ],
    }
    
    config_file = tmp_path / 'trello-sync.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(existing_config, f)
    
    # Mock Trello API
    mock_boards = [
        {'id': 'board1', 'name': 'Board 1'},
    ]
    
    mock_board_details = {
        'board1': {
            'id': 'board1',
            'name': 'Board 1',
            'organization': {'displayName': 'My Org'},
        },
    }
    
    with patch('trello_sync.cli.commands.TrelloSync') as mock_sync_class:
        mock_sync = MagicMock()
        mock_sync.get_boards.return_value = mock_boards
        mock_sync.get_board.return_value = mock_board_details['board1']
        mock_sync_class.return_value = mock_sync
        
        runner = CliRunner()
        result = runner.invoke(cli, ['config-init'])
        
        assert result.exit_code == 0
        
        # Check custom settings were preserved
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        board1 = config['boards'][0]
        assert board1['enabled'] is True
        assert board1['target_path'] == 'custom/path/{org}/{board}/{column}/{card}.md'
        assert board1['assets_folder'] == 'custom/assets/{org}/{board}'

