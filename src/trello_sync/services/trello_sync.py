"""Trello API service for syncing boards to local markdown files."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from trello_sync.services.attachments import (
    download_attachment,
    get_asset_path,
    get_relative_asset_path,
    get_unique_filename,
    is_image_file,
)
from trello_sync.utils.config import (
    ConfigError,
    get_board_config,
    get_obsidian_root,
    load_config,
    resolve_path_template,
)
from trello_sync.utils.formatting import sanitize_file_name
from trello_sync.utils.markdown import generate_markdown

TRELLO_BASE_URL = 'https://api.trello.com/1'


def get_credentials() -> tuple[str, str]:
    """Get Trello credentials from environment.

    Returns:
        Tuple of (api_key, token).

    Raises:
        ValueError: If credentials are not found in environment.
    """
    api_key = os.getenv('TRELLO_API_KEY')
    token = os.getenv('TRELLO_TOKEN') or os.getenv('TRELLO_API_TOKEN')
    if not api_key or not token:
        raise ValueError(
            "TRELLO_API_KEY and TRELLO_TOKEN (or TRELLO_API_TOKEN) must be set in .env file"
        )
    return api_key, token


class TrelloSync:
    """Main sync class for Trello operations."""

    def __init__(self) -> None:
        """Initialize TrelloSync with credentials and session."""
        self.api_key, self.token = get_credentials()
        self.base_url = TRELLO_BASE_URL
        self.session = requests.Session()

    def _request(self, method: str, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make API request to Trello.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Optional query parameters.

        Returns:
            JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        url = f"{self.base_url}/{endpoint}"
        auth_params: dict[str, Any] = {
            'key': self.api_key,
            'token': self.token
        }
        if params:
            auth_params.update(params)
        
        response = self.session.request(method, url, params=auth_params)
        response.raise_for_status()
        return response.json()

    def get_boards(self) -> list[dict[str, Any]]:
        """Get all boards accessible to the authenticated user.

        Returns:
            List of board dictionaries.
        """
        return self._request('GET', 'members/me/boards', {'filter': 'all'})

    def get_board(self, board_id: str) -> dict[str, Any]:
        """Get board details.

        Args:
            board_id: The ID of the board to retrieve.

        Returns:
            Board dictionary with details.
        """
        return self._request('GET', f'boards/{board_id}')

    def get_board_lists(self, board_id: str) -> list[dict[str, Any]]:
        """Get all lists on a board.

        Args:
            board_id: The ID of the board.

        Returns:
            List of list dictionaries.
        """
        return self._request('GET', f'boards/{board_id}/lists', {'filter': 'all'})

    def get_cards_in_list(self, list_id: str) -> list[dict[str, Any]]:
        """Get all cards in a list.

        Args:
            list_id: The ID of the list.

        Returns:
            List of card dictionaries.
        """
        return self._request('GET', f'lists/{list_id}/cards')

    def get_card(self, card_id: str) -> dict[str, Any]:
        """Get full card details.

        Args:
            card_id: The ID of the card to retrieve.

        Returns:
            Card dictionary with all details.
        """
        params = {
            'fields': 'all',
            'members': 'true',
            'member_fields': 'fullName,username',
            'checklists': 'all',
            'checklist_fields': 'all',
            'attachments': 'true',
            'actions': 'commentCard'
        }
        return self._request('GET', f'cards/{card_id}', params)

    def get_card_comments(self, card_id: str) -> list[dict[str, Any]]:
        """Get comments for a card.

        Args:
            card_id: The ID of the card.

        Returns:
            List of comment action dictionaries.
        """
        return self._request('GET', f'cards/{card_id}/actions', {'filter': 'commentCard'})

    def get_card_attachments(self, card_id: str) -> list[dict[str, Any]]:
        """Get attachments for a card.

        Args:
            card_id: The ID of the card.

        Returns:
            List of attachment dictionaries.
        """
        return self._request('GET', f'cards/{card_id}/attachments')

    def get_card_labels(self, card_id: str) -> list[dict[str, Any]]:
        """Get labels for a card.

        Args:
            card_id: The ID of the card.

        Returns:
            List of label dictionaries.
        """
        return self._request('GET', f'cards/{card_id}/labels')

    def get_card_members(self, card_id: str) -> list[dict[str, Any]]:
        """Get members assigned to a card.

        Args:
            card_id: The ID of the card.

        Returns:
            List of member dictionaries.
        """
        return self._request('GET', f'cards/{card_id}/members', {'fields': 'fullName,username'})

    def get_card_checklists(self, card_id: str) -> list[dict[str, Any]]:
        """Get checklists for a card.

        Args:
            card_id: The ID of the card.

        Returns:
            List of checklist dictionaries.
        """
        return self._request('GET', f'cards/{card_id}/checklists', {'checkItems': 'all'})

    def should_sync_card(self, card_path: Path, card_updated: str | None) -> bool:
        """Check if card should be synced based on file modification time.

        Args:
            card_path: Path to the local card file.
            card_updated: ISO format date string of last card update.

        Returns:
            True if card should be synced, False otherwise.
        """
        if not card_path.exists():
            return True
        
        file_mtime = datetime.fromtimestamp(card_path.stat().st_mtime)
        
        # Parse card updated time
        if isinstance(card_updated, str):
            try:
                card_updated_dt = datetime.fromisoformat(card_updated.replace('Z', '+00:00'))
                # Remove timezone for comparison
                card_updated_dt = card_updated_dt.replace(tzinfo=None)
            except (ValueError, AttributeError):
                return True  # If we can't parse, sync it
        else:
            return True
        
        # Sync if card is newer than file
        return card_updated_dt > file_mtime

    def sync_board(
        self,
        board_id: str,
        board_name: str | None = None,
        workspace_name: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Sync a board to local files.

        Args:
            board_id: The ID of the board to sync.
            board_name: Optional board name (will fetch if not provided).
            workspace_name: Optional workspace name (will fetch if not provided).
            dry_run: If True, show what would be synced without making changes.

        Returns:
            Dictionary with sync statistics: total_cards, synced_cards, skipped_cards.

        Raises:
            ConfigError: If board is not configured and configuration is required.
        """
        # Check if board is configured
        board_config = get_board_config(board_id)
        
        if not board_config:
            # Board not configured - skip it
            return {
                'total_cards': 0,
                'synced_cards': 0,
                'skipped_cards': 0,
            }
        
        if not board_config.get('enabled', True):
            # Board is disabled - skip it
            return {
                'total_cards': 0,
                'synced_cards': 0,
                'skipped_cards': 0,
            }
        
        # Get board and workspace info
        if not board_name:
            board_data = self.get_board(board_id)
            board_name = board_data['name']
        
        if not workspace_name:
            board_data = self.get_board(board_id)
            workspace_name = board_data.get('organization', {}).get('displayName', '')
            # Use config workspace_name if provided
            if board_config.get('workspace_name'):
                workspace_name = board_config['workspace_name']
        
        # Get Obsidian root and resolve paths
        try:
            obsidian_root = get_obsidian_root()
        except ConfigError:
            raise ConfigError(
                f"Board {board_id} is configured but OBSIDIAN_ROOT is not set. "
                "Set it as an environment variable or in trello-sync.yaml"
            )
        
        # Get target path template
        target_path_template = board_config.get('target_path', '20_tasks/Trello/{org}/{board}/{column}/{card}.md')
        
        # Get assets folder template
        assets_template = board_config.get('assets_folder')
        if not assets_template:
            global_config = load_config()
            assets_template = global_config.get('default_assets_folder', '.local_assets/Trello')
        
        # Get lists
        lists = self.get_board_lists(board_id)
        
        total_cards = 0
        synced_cards = 0
        skipped_cards = 0
        
        for list_data in lists:
            list_name = list_data['name']
            list_id = list_data['id']
            
            # Get cards in list
            cards = self.get_cards_in_list(list_id)
            
            for card in cards:
                total_cards += 1
                card_id = card['id']
                card_name = card['name']
                card_updated = card.get('dateLastActivity')
                
                # Resolve path template
                path_vars = {
                    'org': sanitize_file_name(workspace_name or 'unknown'),
                    'board': sanitize_file_name(board_name),
                    'column': sanitize_file_name(list_name),
                    'card': sanitize_file_name(card_name),
                }
                
                resolved_path = resolve_path_template(target_path_template, path_vars)
                card_path = obsidian_root / resolved_path
                
                # Check if we should sync
                if not self.should_sync_card(card_path, card_updated):
                    skipped_cards += 1
                    continue
                
                if dry_run:
                    synced_cards += 1
                    continue
                
                # Get full card details
                try:
                    full_card = self.get_card(card_id)
                    
                    # Get additional data
                    comments = self.get_card_comments(card_id)
                    attachments = self.get_card_attachments(card_id)
                    labels = self.get_card_labels(card_id)
                    members = self.get_card_members(card_id)
                    checklists = self.get_card_checklists(card_id)
                    
                    # Merge data - store as actions for comment processing
                    full_card['actions'] = comments  # Comments come as actions
                    full_card['attachments'] = attachments
                    full_card['labels'] = labels
                    full_card['members'] = members
                    full_card['checklists'] = checklists
                    # Also store as comments for compatibility
                    full_card['comments'] = comments
                    
                    # Download attachments and prepare asset paths
                    downloaded_attachments: dict[str, dict[str, Any]] = {}
                    
                    # Resolve assets folder path
                    assets_vars = {
                        'org': sanitize_file_name(workspace_name or 'unknown'),
                        'board': sanitize_file_name(board_name),
                    }
                    resolved_assets_template = resolve_path_template(assets_template, assets_vars)
                    assets_folder = obsidian_root / resolved_assets_template
                    
                    for attachment in attachments:
                        # Only download file attachments (not links)
                        if attachment.get('isUpload', False):
                            attachment_name = attachment.get('name', 'untitled')
                            attachment_url = attachment.get('url', '')
                            
                            if attachment_url:
                                try:
                                    # Calculate asset path
                                    asset_path = get_asset_path(card_path, attachment_name, assets_folder)
                                    asset_path = get_unique_filename(assets_folder, asset_path.name)
                                    
                                    # Download attachment
                                    download_attachment(
                                        attachment,
                                        asset_path,
                                        self.api_key,
                                        self.token,
                                    )
                                    
                                    # Get relative path for markdown
                                    relative_path = get_relative_asset_path(card_path, asset_path)
                                    
                                    # Store info for markdown generation
                                    downloaded_attachments[attachment.get('id', '')] = {
                                        'local_path': relative_path,
                                        'is_image': is_image_file(attachment_name, attachment.get('mimeType')),
                                        'original_url': attachment_url,
                                        'name': attachment_name,
                                    }
                                except Exception as e:
                                    # Log warning but continue
                                    print(f"Warning: Failed to download attachment {attachment_name}: {e}")
                    
                    # Generate markdown with attachment info
                    markdown_content = generate_markdown(
                        full_card,
                        list_name,
                        board_name,
                        workspace_name,
                        list_id=list_id,
                        board_id=board_id,
                        downloaded_attachments=downloaded_attachments,
                    )
                    
                    # Create directory and write file
                    card_path.parent.mkdir(parents=True, exist_ok=True)
                    card_path.write_text(markdown_content, encoding='utf-8')
                    synced_cards += 1
                    
                except Exception:
                    # Error handling is done at CLI level
                    raise
        
        return {
            'total_cards': total_cards,
            'synced_cards': synced_cards,
            'skipped_cards': skipped_cards,
        }

