"""Trello API service for syncing boards to local markdown files."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

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
        """
        if not board_name:
            board_data = self.get_board(board_id)
            board_name = board_data['name']
        
        if not workspace_name:
            board_data = self.get_board(board_id)
            workspace_name = board_data.get('organization', {}).get('displayName', '')
        
        # Default to data/ folder from project root
        data_dir = Path('data')
        board_dir = data_dir / sanitize_file_name(board_name)
        board_dir.mkdir(parents=True, exist_ok=True)
        
        # Get lists
        lists = self.get_board_lists(board_id)
        
        total_cards = 0
        synced_cards = 0
        skipped_cards = 0
        
        for list_data in lists:
            list_name = list_data['name']
            list_id = list_data['id']
            list_dir = board_dir / sanitize_file_name(list_name)
            list_dir.mkdir(parents=True, exist_ok=True)
            
            # Get cards in list
            cards = self.get_cards_in_list(list_id)
            
            for card in cards:
                total_cards += 1
                card_id = card['id']
                card_name = card['name']
                card_updated = card.get('dateLastActivity')
                
                card_filename = sanitize_file_name(card_name) + '.md'
                card_path = list_dir / card_filename
                
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
                    
                    # Generate markdown
                    markdown_content = generate_markdown(
                        full_card,
                        list_name,
                        board_name,
                        workspace_name
                    )
                    
                    # Write file
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

