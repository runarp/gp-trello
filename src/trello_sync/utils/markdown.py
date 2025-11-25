"""Markdown generation utilities for Trello cards."""

import hashlib
import json
from datetime import datetime
from typing import Any

from trello_sync.utils.formatting import (
    format_bytes,
    format_date,
    format_iso_date,
)


def _format_yaml_key(key: str) -> str:
    """Format a YAML key, quoting if necessary.
    
    Args:
        key: The key to format.
        
    Returns:
        Formatted key string.
    """
    key_str = str(key)
    # Quote if contains spaces, colons, or special characters
    if ' ' in key_str or ':' in key_str or '"' in key_str or not key_str.replace('_', '').replace('-', '').isalnum():
        return json.dumps(key_str)
    return key_str


def _format_yaml_value(key: str, value: Any, indent: int = 0) -> list[str]:
    """Format a YAML value, handling nested structures.
    
    Args:
        key: The YAML key.
        value: The value to format.
        indent: Current indentation level.
        
    Returns:
        List of YAML lines for this key-value pair.
    """
    indent_str = '  ' * indent
    lines: list[str] = []
    
    if value is None:
        return []
    
    if isinstance(value, dict):
        if not value:
            lines.append(f'{indent_str}{key}: {{}}')
        else:
            lines.append(f'{indent_str}{key}:')
            for k, v in value.items():
                # Format the nested key properly
                k_str = _format_yaml_key(k)
                lines.extend(_format_yaml_value(k_str, v, indent + 1))
    elif isinstance(value, list):
        if not value:
            lines.append(f'{indent_str}{key}: []')
        else:
            # Check if it's a list of dicts (like comment IDs)
            if value and isinstance(value[0], dict):
                lines.append(f'{indent_str}{key}:')
                for item in value:
                    lines.append(f'{indent_str}  -')
                    for k, v in item.items():
                        k_str = _format_yaml_key(k)
                        lines.extend(_format_yaml_value(k_str, v, indent + 2))
            else:
                lines.append(f'{indent_str}{key}: {json.dumps(value)}')
    elif isinstance(value, str):
        # Escape special YAML characters
        escaped = value.replace('"', '\\"').replace('\n', '\\n')
        lines.append(f'{indent_str}{key}: "{escaped}"')
    elif isinstance(value, bool):
        lines.append(f'{indent_str}{key}: {str(value).lower()}')
    else:
        lines.append(f'{indent_str}{key}: {value}')
    
    return lines


def generate_markdown(
    card_data: dict[str, Any],
    list_name: str,
    board_name: str,
    workspace_name: str,
    list_id: str | None = None,
    board_id: str | None = None,
    downloaded_attachments: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generate markdown content from card data.

    Args:
        card_data: Dictionary containing Trello card data.
        list_name: Name of the list containing the card.
        board_name: Name of the board containing the card.
        workspace_name: Name of the workspace containing the board.
        list_id: Optional ID of the list containing the card.
        board_id: Optional ID of the board containing the card.
        downloaded_attachments: Optional dict mapping attachment IDs to local path info.

    Returns:
        Complete markdown content as a string with frontmatter and body.
    """
    if downloaded_attachments is None:
        downloaded_attachments = {}
    # Extract checklist and checkitem IDs
    checklists = card_data.get('checklists', [])
    checklist_ids: dict[str, str] = {}
    checkitem_ids: dict[str, dict[str, str]] = {}
    
    for checklist in checklists:
        checklist_name = checklist.get('name', 'Untitled Checklist')
        checklist_id = checklist.get('id', '')
        if checklist_id:
            checklist_ids[checklist_name] = checklist_id
        
        checkitems = checklist.get('checkItems', [])
        if checkitems:
            checkitem_ids[checklist_name] = {}
            for item in checkitems:
                item_name = item.get('name', '')
                item_id = item.get('id', '')
                if item_id and item_name:
                    checkitem_ids[checklist_name][item_name] = item_id
    
    # Extract comment IDs
    comments = card_data.get('comments', [])
    if not comments:
        actions = card_data.get('actions', [])
        comments = [a for a in actions if a.get('type') == 'commentCard']
    
    comment_ids: list[dict[str, str]] = []
    for comment in comments:
        comment_id = comment.get('id', '')
        if comment_id:
            member = comment.get('memberCreator', {}) or comment.get('member', {})
            author = member.get('fullName', member.get('username', 'Unknown'))
            date = comment.get('date', '')
            text = comment.get('data', {}).get('text', '') or comment.get('text', '')
            
            # Create a simple hash of content for matching
            content_hash = hashlib.md5(text.encode()).hexdigest()[:8] if text else ''
            
            comment_ids.append({
                'id': comment_id,
                'author': author,
                'date': date,
                'content_hash': content_hash,
            })
    
    # Extract labels with color information (trello-tags)
    labels_data = card_data.get('labels', [])
    labels: list[dict[str, Any]] = []
    for label in labels_data:
        label_info: dict[str, Any] = {
            'name': label.get('name', ''),
        }
        if label.get('color'):
            label_info['color'] = label.get('color')
        if label.get('id'):
            label_info['id'] = label.get('id')
        labels.append(label_info)
    
    # Extract members with full information (assigned to)
    members_data = card_data.get('members', [])
    members: list[dict[str, Any]] = []
    for member in members_data:
        member_info: dict[str, Any] = {
            'fullName': member.get('fullName', ''),
        }
        if member.get('username'):
            member_info['username'] = member.get('username')
        if member.get('id'):
            member_info['id'] = member.get('id')
        if member.get('initials'):
            member_info['initials'] = member.get('initials')
        members.append(member_info)
    
    # Extract cover information if present
    cover = card_data.get('cover')
    cover_info: dict[str, Any] | None = None
    if cover:
        cover_info = {}
        if cover.get('color'):
            cover_info['color'] = cover.get('color')
        if cover.get('brightness'):
            cover_info['brightness'] = cover.get('brightness')
        if cover.get('size'):
            cover_info['size'] = cover.get('size')
        if cover.get('idAttachment'):
            cover_info['idAttachment'] = cover.get('idAttachment')
        if cover.get('url'):
            cover_info['url'] = cover.get('url')
        if not cover_info:
            cover_info = None
    
    # Frontmatter
    frontmatter: dict[str, Any] = {
        'trello_board_card_id': card_data.get('id', ''),
        'board': board_name,
        'url': card_data.get('url', ''),
        'workspace': workspace_name,
        'created': format_iso_date(card_data.get('dateCreated')),
        'updated': format_iso_date(card_data.get('dateLastActivity')),
        'list': list_name,
        'labels': labels,
        'members': members,
        'due-date': format_iso_date(card_data.get('due')),
        'attachments-count': len(card_data.get('attachments', [])),
        'comments-count': len(comments),
        # Additional Trello UI metadata
        'subscribed': card_data.get('subscribed', False),
        'closed': card_data.get('closed', False),
        'idShort': card_data.get('idShort'),
        'shortUrl': card_data.get('shortUrl'),
        'dueComplete': card_data.get('dueComplete', False),
        'start': format_iso_date(card_data.get('start')),
        'pos': card_data.get('pos'),
    }
    
    # Add cover if present
    if cover_info:
        frontmatter['cover'] = cover_info
    
    # Add Phase 2 frontmatter fields
    if checklist_ids:
        frontmatter['trello_checklist_ids'] = checklist_ids
    if checkitem_ids:
        frontmatter['trello_checkitem_ids'] = checkitem_ids
    if comment_ids:
        frontmatter['trello_comment_ids'] = comment_ids
    
    # Add sync status fields (default to synced for new cards)
    frontmatter['last_synced'] = None  # Will be set when local → Trello sync happens
    frontmatter['sync_status'] = 'synced'  # Default status for cards synced from Trello
    
    # Add optional IDs if provided
    if list_id:
        frontmatter['trello_list_id'] = list_id
    if board_id:
        frontmatter['trello_board_id'] = board_id
    
    # Remove None values (but keep empty dicts/lists for structure)
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
    
    # Build frontmatter YAML with proper formatting for nested structures
    yaml_lines = ['---']
    for key, value in frontmatter.items():
        if isinstance(value, (dict, list)) and not isinstance(value, str):
            # Use custom formatter for nested structures
            lines = _format_yaml_value(key, value, indent=0)
            yaml_lines.extend(lines)
        elif isinstance(value, str):
            # Escape special YAML characters
            escaped = value.replace('"', '\\"')
            yaml_lines.append(f'{key}: "{escaped}"')
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
        # Separate into images, files, and links
        image_attachments: list[dict[str, Any]] = []
        file_attachments: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
        
        for att in attachments:
            if not att.get('isUpload', False):
                links.append(att)
            else:
                att_id = att.get('id', '')
                if att_id in downloaded_attachments:
                    att_info = downloaded_attachments[att_id]
                    if att_info.get('is_image', False):
                        image_attachments.append({**att, '_local_info': att_info})
                    else:
                        file_attachments.append({**att, '_local_info': att_info})
                else:
                    # Fallback: treat as file if not downloaded
                    file_attachments.append(att)
        
        body_lines.append('## Attachments')
        body_lines.append('')
        
        # Images (inline)
        if image_attachments:
            body_lines.append('### Images')
            for att in image_attachments:
                name = att.get('name', 'Untitled')
                local_info = att.get('_local_info')
                
                if local_info:
                    local_path = local_info.get('local_path', '')
                    original_url = local_info.get('original_url', att.get('url', ''))
                    # Inline image syntax for Obsidian
                    body_lines.append(f'![{name}]({local_path})')
                    if original_url:
                        body_lines.append(f'*Original: [{name}]({original_url})*')
                else:
                    # Fallback to original URL
                    url = att.get('url', '')
                    body_lines.append(f'![{name}]({url})')
                body_lines.append('')
        
        # Files (links)
        if file_attachments:
            body_lines.append('### Files')
            for att in file_attachments:
                name = att.get('name', 'Untitled')
                local_info = att.get('_local_info')
                bytes_val = att.get('bytes')
                date = format_date(att.get('date', ''))
                
                if local_info:
                    local_path = local_info.get('local_path', '')
                    original_url = local_info.get('original_url', att.get('url', ''))
                    size_str = f" ({format_bytes(bytes_val)}, added {date})" if bytes_val else f" (added {date})" if date else ""
                    body_lines.append(f'- [{name}]({local_path}){size_str}')
                    if original_url:
                        body_lines.append(f'  Original: [{name}]({original_url})')
                else:
                    # Fallback to original URL
                    url = att.get('url', '')
                    size_str = f" ({format_bytes(bytes_val)}, added {date})" if bytes_val else f" (added {date})" if date else ""
                    body_lines.append(f'- [{name}]({url}){size_str}')
            body_lines.append('')
        
        # Links
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
    # (comments variable already extracted above for frontmatter)
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

