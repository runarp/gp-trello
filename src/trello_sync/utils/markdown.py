"""Markdown generation utilities for Trello cards."""

import json
from typing import Any

from trello_sync.utils.formatting import (
    format_bytes,
    format_date,
    format_iso_date,
)


def generate_markdown(
    card_data: dict[str, Any],
    list_name: str,
    board_name: str,
    workspace_name: str,
) -> str:
    """Generate markdown content from card data.

    Args:
        card_data: Dictionary containing Trello card data.
        list_name: Name of the list containing the card.
        board_name: Name of the board containing the card.
        workspace_name: Name of the workspace containing the board.

    Returns:
        Complete markdown content as a string with frontmatter and body.
    """
    # Frontmatter
    frontmatter = {
        'trello_board_card_id': card_data.get('id', ''),
        'board': board_name,
        'url': card_data.get('url', ''),
        'workspace': workspace_name,
        'created': format_iso_date(card_data.get('dateCreated')),
        'updated': format_iso_date(card_data.get('dateLastActivity')),
        'list': list_name,
        'labels': [l.get('name', '') for l in card_data.get('labels', [])],
        'members': [m.get('fullName', '') for m in card_data.get('members', [])],
        'due-date': format_iso_date(card_data.get('due')),
        'attachments-count': len(card_data.get('attachments', [])),
        'comments-count': len(card_data.get('comments', card_data.get('actions', [])))
    }
    
    # Remove None values
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
    
    # Build frontmatter YAML
    yaml_lines = ['---']
    for key, value in frontmatter.items():
        if isinstance(value, list):
            yaml_lines.append(f"{key}: {json.dumps(value)}")
        elif isinstance(value, str):
            # Escape special YAML characters
            value = value.replace('"', '\\"')
            yaml_lines.append(f'{key}: "{value}"')
        else:
            yaml_lines.append(f'{key}: {value}')
    yaml_lines.append('---')
    yaml_lines.append('')
    
    # Body
    body_lines = [f"# {card_data.get('name', 'Untitled')}", '']
    
    # Description
    desc = card_data.get('desc', '').strip()
    if desc:
        body_lines.append('## Description')
        body_lines.append('')
        body_lines.append(desc)
        body_lines.append('')
    
    # Checklists
    checklists = card_data.get('checklists', [])
    if checklists:
        for checklist in checklists:
            checklist_name = checklist.get('name', 'Untitled Checklist')
            body_lines.append(f'## Checklist: {checklist_name}')
            body_lines.append('')
            checkitems = checklist.get('checkItems', [])
            for item in checkitems:
                state = 'x' if item.get('state') == 'complete' else ' '
                name = item.get('name', '')
                body_lines.append(f'- [{state}] {name}')
            body_lines.append('')
    
    # Attachments
    attachments = card_data.get('attachments', [])
    if attachments:
        files = [a for a in attachments if a.get('isUpload', False)]
        links = [a for a in attachments if not a.get('isUpload', False)]
        
        body_lines.append('## Attachments')
        body_lines.append('')
        
        if files:
            body_lines.append('### Files')
            for att in files:
                name = att.get('name', 'Untitled')
                url = att.get('url', '')
                bytes_val = att.get('bytes')
                date = format_date(att.get('date', ''))
                size_str = f" ({format_bytes(bytes_val)}, added {date})" if bytes_val else f" (added {date})" if date else ""
                body_lines.append(f'- [{name}]({url}){size_str}')
            body_lines.append('')
        
        if links:
            body_lines.append('### Links')
            for att in links:
                name = att.get('name', 'Untitled')
                url = att.get('url', '')
                date = format_date(att.get('date', ''))
                date_str = f" (added {date})" if date else ""
                body_lines.append(f'- [{name}]({url}){date_str}')
            body_lines.append('')
    
    # Comments - handle both direct comments array and actions array
    comments = card_data.get('comments', [])
    if not comments:
        # Try to get from actions if comments not directly available
        actions = card_data.get('actions', [])
        comments = [a for a in actions if a.get('type') == 'commentCard']
    
    if comments:
        body_lines.append('## Comments')
        body_lines.append('')
        for comment in comments:
            member = comment.get('memberCreator', {})
            if not member:
                member = comment.get('member', {})
            full_name = member.get('fullName', member.get('username', 'Unknown'))
            date = format_date(comment.get('date', ''))
            text = comment.get('data', {}).get('text', '')
            if not text:
                text = comment.get('text', '')
            
            body_lines.append(f'#### Comment by {full_name}')
            body_lines.append(f'**Date:** {date}')
            body_lines.append('')
            body_lines.append(text)
            body_lines.append('')
            body_lines.append('---')
            body_lines.append('')
    
    # Combine
    content = '\n'.join(yaml_lines) + '\n'.join(body_lines)
    return content

