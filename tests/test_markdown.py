"""Tests for markdown generation utilities."""

from trello_sync.utils.markdown import generate_markdown


def test_generate_markdown_basic() -> None:
    """Test basic markdown generation."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': 'Test description',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [],
        'comments': [],
        'checklists': [],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    assert '# Test Card' in result
    assert '## Description' in result
    assert 'Test description' in result
    assert 'trello_board_card_id: "test123"' in result
    assert 'board: "Test Board"' in result


def test_generate_markdown_with_checklist() -> None:
    """Test markdown generation with checklist."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [],
        'comments': [],
        'checklists': [
            {
                'id': 'checklist_id_123',
                'name': 'Test Checklist',
                'checkItems': [
                    {'id': 'checkitem_id_1', 'name': 'Item 1', 'state': 'complete'},
                    {'id': 'checkitem_id_2', 'name': 'Item 2', 'state': 'incomplete'},
                ],
            },
        ],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    assert '## Checklist: Test Checklist' in result
    assert '- [x] Item 1' in result
    assert '- [ ] Item 2' in result
    # Verify new frontmatter fields
    assert 'trello_checklist_ids:' in result
    assert '"Test Checklist": "checklist_id_123"' in result
    assert 'trello_checkitem_ids:' in result
    assert '"Item 1": "checkitem_id_1"' in result
    assert '"Item 2": "checkitem_id_2"' in result
    assert 'sync_status:' in result
    assert 'synced' in result


def test_generate_markdown_with_attachments() -> None:
    """Test markdown generation with attachments."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [
            {'name': 'file.pdf', 'url': 'https://example.com/file.pdf', 'isUpload': True, 'bytes': 1024},
            {'name': 'Link', 'url': 'https://example.com', 'isUpload': False},
        ],
        'comments': [],
        'checklists': [],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    assert '## Attachments' in result
    assert '### Files' in result
    assert '### Links' in result
    assert '[file.pdf]' in result
    assert '[Link]' in result


def test_generate_markdown_with_comments() -> None:
    """Test markdown generation with comments and comment IDs."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [],
        'comments': [
            {
                'id': 'comment_id_123',
                'type': 'commentCard',
                'date': '2024-01-21T10:00:00Z',
                'memberCreator': {'fullName': 'Test User', 'username': 'testuser'},
                'data': {'text': 'This is a test comment'},
            },
        ],
        'checklists': [],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    assert '## Comments' in result
    assert '#### Comment by Test User' in result
    assert 'This is a test comment' in result
    # Verify comment IDs in frontmatter
    assert 'trello_comment_ids:' in result
    assert 'id: "comment_id_123"' in result
    assert 'author: "Test User"' in result


def test_generate_markdown_with_list_and_board_ids() -> None:
    """Test markdown generation with list and board IDs."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [],
        'comments': [],
        'checklists': [],
    }
    
    result = generate_markdown(
        card_data,
        'Test List',
        'Test Board',
        'Test Workspace',
        list_id='list_id_123',
        board_id='board_id_456'
    )
    
    assert 'trello_list_id: "list_id_123"' in result
    assert 'trello_board_id: "board_id_456"' in result


def test_generate_markdown_sync_status_fields() -> None:
    """Test that sync status fields are included in frontmatter."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'labels': [],
        'members': [],
        'attachments': [],
        'comments': [],
        'checklists': [],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    # Verify sync status fields are present
    assert 'sync_status:' in result
    assert 'synced' in result
    # last_synced should not be present (None values are filtered out)


def test_generate_markdown_trello_ui_metadata() -> None:
    """Test that Trello UI metadata fields are included in frontmatter."""
    card_data = {
        'id': 'test123',
        'name': 'Test Card',
        'url': 'https://trello.com/c/test123',
        'shortUrl': 'https://trello.com/c/abc123',
        'idShort': 1621,
        'desc': '',
        'dateCreated': '2024-01-20T12:00:00Z',
        'dateLastActivity': '2024-01-21T12:00:00Z',
        'subscribed': True,
        'closed': False,
        'due': '2024-01-25T12:00:00Z',
        'dueComplete': False,
        'start': '2024-01-22T12:00:00Z',
        'pos': 16384,
        'labels': [
            {'name': 'Important', 'color': 'red', 'id': 'label_id_1'},
            {'name': 'Bug', 'color': 'orange', 'id': 'label_id_2'},
            {'name': 'No Color Label', 'id': 'label_id_3'},
        ],
        'cover': {
            'color': 'blue',
            'brightness': 'light',
            'size': 'normal',
        },
        'members': [
            {'fullName': 'John Doe', 'username': 'johndoe', 'id': 'member_id_1', 'initials': 'JD'},
            {'fullName': 'Jane Smith', 'username': 'janesmith', 'id': 'member_id_2'},
        ],
        'attachments': [],
        'comments': [],
        'checklists': [],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    # Verify new metadata fields
    assert 'subscribed: true' in result
    assert 'closed: false' in result
    assert 'idShort: 1621' in result
    assert 'shortUrl:' in result
    assert 'dueComplete: false' in result
    assert 'start:' in result
    assert 'pos: 16384' in result
    
    # Verify enhanced labels with colors
    assert 'labels:' in result
    assert 'name: "Important"' in result
    assert 'color: "red"' in result
    assert 'name: "Bug"' in result
    assert 'color: "orange"' in result
    assert 'name: "No Color Label"' in result
    
    # Verify enhanced members (assigned to)
    assert 'members:' in result
    assert 'fullName: "John Doe"' in result
    assert 'username: "johndoe"' in result
    assert 'id: "member_id_1"' in result
    assert 'initials: "JD"' in result
    assert 'fullName: "Jane Smith"' in result
    assert 'username: "janesmith"' in result
    
    # Verify cover information
    assert 'cover:' in result
    assert 'color: "blue"' in result
    assert 'brightness: "light"' in result
    assert 'size: "normal"' in result

