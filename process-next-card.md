# Process Next Card - Workflow

This is a repeatable workflow to sync one card at a time.

## Step 1: Check Current Status
```bash
node scripts/check-sync-status.js
```

## Step 2: Get Cards from a List
Use MCP tool to get cards from a list:
- `mcp_trello-admin_get_cards_in_list` with listId

## Step 3: For Each Card, Check if File Exists
The file path format is: `data/gp-family-office/{list-sanitized}/{card-name-sanitized}.md`

Example:
- List: "Current Tasks" → `current-tasks`
- Card: "Change Current Sockets..." → `change-current-sockets-to-sockets-with-ethernet-in-ils-office.md`
- Full path: `data/gp-family-office/current-tasks/change-current-sockets-to-sockets-with-ethernet-in-ils-office.md`

## Step 4: If File Doesn't Exist, Fetch Full Details
For each unsynced card, fetch:
1. `mcp_trello-admin_get_card` - Get card details
2. `mcp_trello-admin_get_comments` - Get comments
3. `mcp_trello-admin_get_attachments` - Get attachments
4. `mcp_trello-admin_get_card_labels` - Get labels
5. `mcp_trello-admin_get_card_members` - Get members
6. If card has checklists: `mcp_trello-admin_get_checklist` for each checklist

## Step 5: Generate Markdown File
Use the Python CLI tool (`python -m trello_sync.cli sync <board-id>`) or create the markdown file following the format of existing cards.

## Step 6: Verify
```bash
node scripts/check-sync-status.js
```

## Repeat
Go back to Step 2 and process the next card.

---

## Quick Reference: List IDs

- **Incoming**: `5c3764a8d43bd4641e5c7a23`
- **Prioritized Projects**: `5c35aeba09b35f8e481c887a`
- **Current Tasks**: `5c35aec26af9622bb204e353`
- **Waiting**: `5c3c1c2ebd58431b938aa5de`
- **Completed**: `5c35af47065f670f2e488769`
- **On Ice**: `601bf9f4fa018241e0bd50ed`

## Board ID
- **GP Family Office**: `5c35aeade878c43a9134927a`

