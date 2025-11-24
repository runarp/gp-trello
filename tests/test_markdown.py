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
                'name': 'Test Checklist',
                'checkItems': [
                    {'name': 'Item 1', 'state': 'complete'},
                    {'name': 'Item 2', 'state': 'incomplete'},
                ],
            },
        ],
    }
    
    result = generate_markdown(card_data, 'Test List', 'Test Board', 'Test Workspace')
    
    assert '## Checklist: Test Checklist' in result
    assert '- [x] Item 1' in result
    assert '- [ ] Item 2' in result


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

