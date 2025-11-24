# GP Family Office Trello Sync

This repository contains a local mirror of the "GP Family Office" Trello board, synced to markdown files for AI discoverability and local access.

## Structure

```
data/
└── gp-family-office/
    ├── incoming/              # Incoming items
    ├── prioritized-projects/  # Prioritized projects
    ├── current-tasks/         # Current tasks
    ├── waiting/               # Waiting items
    ├── completed/             # Completed items
    └── on-ice/               # On ice items
```

All synced Trello boards are stored in the `data/` folder, organized by board name.

## Sync Status

- **Total Cards**: 35
- **Cards Synced**: 5 (incremental process)
- **Last Sync**: 2025-01-20

Run `node scripts/check-sync-status.js` to see current sync status.

## Index Files

- `.trello-index.json` - Master index of all boards and cards
- `data/gp-family-office/.index.json` - Board-specific index (to be created)
- `.trello-sync/last-sync.json` - Sync state tracking

## Card Format

Each card is stored as a markdown file with:
- YAML frontmatter containing metadata (Trello ID, board, URL, labels, members, etc.)
- Card title as H1 heading
- Description section
- Checklists (if any)
- Attachments (files and links)
- Comments with author and timestamp

## Sync Process

The sync process uses the MCP Trello Admin server to:
1. Fetch board details and lists
2. Fetch all cards from each list
3. Fetch full card details (comments, attachments, checklists, labels, members)
4. Generate markdown files following the structure defined in `.cursor/rules/trello-structure.mdc`
5. Create index files for AI discoverability

## Incremental Sync Process

The sync process is designed to be **repeatable and resumable** - process one card at a time, skipping cards that already have markdown files.

### Quick Workflow

1. **Check status**: `node scripts/check-sync-status.js` - See which cards are already synced
2. **Get cards from a list**: Use `mcp_trello-admin_get_cards_in_list` to get cards
3. **Check if file exists**: For each card, check if `data/gp-family-office/{list}/{card-name}.md` exists
4. **If missing, fetch details**:
   - `mcp_trello-admin_get_card` - Card details
   - `mcp_trello-admin_get_comments` - Comments
   - `mcp_trello-admin_get_attachments` - Attachments
   - `mcp_trello-admin_get_card_labels` - Labels
   - `mcp_trello-admin_get_card_members` - Members
   - `mcp_trello-admin_get_checklist` - Checklists (if any)
5. **Generate markdown**: Create the markdown file following the format of existing cards
6. **Verify**: Run `node scripts/check-sync-status.js` again

See `process-next-card.md` for detailed workflow and list IDs.

### Helper Scripts

- `scripts/check-sync-status.js` - Lists all synced cards (quick status check)
- `process-next-card.md` - Detailed workflow guide (MCP-based workflow)

## Python CLI Sync Tool

A Python CLI tool provides a convenient way to sync Trello boards locally.

### Installation

```bash
pip install -r requirements.txt
```

### Usage

The CLI can be run as a module or installed as a package:

```bash
# Run as a module (from project root)
python -m trello_sync.cli list-boards

# Or install the package and use the command
pip install -e .
trello-sync list-boards

# List all accessible boards
python -m trello_sync.cli list-boards

# Show board details and lists
python -m trello_sync.cli show-board <board-id>

# Sync a board (one-way: Trello → local files)
python -m trello_sync.cli sync <board-id>

# Dry run to see what would be synced
python -m trello_sync.cli sync <board-id> --dry-run

# Sync with optional board/workspace names
python -m trello_sync.cli sync <board-id> --board-name "My Board" --workspace-name "My Workspace"
```

### Features

- **One-way sync**: Downloads cards from Trello to local markdown files
- **Incremental sync**: Compares file modification time to card update time - only syncs changed cards
- **Default data folder**: All synced boards are stored in `data/` folder from project root
- **Extendable commands**: Easy to add new commands (e.g., `push`, `diff`, etc.)
- **Dry run mode**: Preview what would be synced without making changes

### Configuration

The tool reads credentials from `.env` file:
- `TRELLO_API_KEY` - Your Trello API key
- `TRELLO_TOKEN` - Your Trello API token

The `.env` file is automatically loaded from the project root.

## Related Documentation

- `.cursor/rules/trello-structure.mdc` - Directory structure and card format
- `.cursor/rules/trello-sync.mdc` - Sync workflow
- `.cursor/rules/trello-utilities.mdc` - Utility functions
- `.cursor/rules/trello-indexes.mdc` - Index file formats

