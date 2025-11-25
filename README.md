# GP Family Office Trello Sync

This repository contains a local mirror of the "GP Family Office" Trello board, synced to markdown files for AI discoverability and local access.

## Structure

### Default Structure (Unconfigured Boards)

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

### Obsidian Structure (Configured Boards)

When boards are configured in `trello-sync.yaml`, they sync to Obsidian-compatible paths:

```
[Obsidian-Root]/
├── 20_tasks/
│   └── Trello/
│       └── [Org]/
│           └── [Board]/
│               └── [Column]/
│                   └── [Card].md
└── .local_assets/
    └── Trello/
        └── [Org]/
            └── [Board]/
                └── [Attachment Files]
```

**Note:** Unconfigured boards are skipped. Only boards listed in `trello-sync.yaml` will be synced.

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
- **Attachments**:
  - **Images**: Rendered inline using `![filename](path)` syntax for Obsidian compatibility
  - **Files**: Linked as `[filename](path)` with original Trello URL as fallback
  - All attachments are downloaded to `.local_assets/Trello/` folder
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
# Note: Board must be configured in trello-sync.yaml
python -m trello_sync.cli sync <board-id>

# Dry run to see what would be synced
python -m trello_sync.cli sync <board-id> --dry-run

# Configuration management
python -m trello_sync.cli config                    # Show current config
python -m trello_sync.cli config-validate          # Validate config file
python -m trello_sync.cli config-add <board-id>    # Interactive config setup
```

### Features

- **One-way sync**: Downloads cards from Trello to local markdown files
- **Incremental sync**: Compares file modification time to card update time - only syncs changed cards
- **Configurable paths**: Map boards to custom directory structures (Obsidian-compatible)
- **Attachment downloads**: Automatically downloads file attachments to assets folder
- **Inline images**: Images are rendered inline in markdown for Obsidian compatibility
- **Extendable commands**: Easy to add new commands (e.g., `push`, `diff`, etc.)
- **Dry run mode**: Preview what would be synced without making changes

### Configuration

#### Credentials

The tool reads credentials from `.env` file:
- `TRELLO_API_KEY` - Your Trello API key
- `TRELLO_TOKEN` - Your Trello API token

The `.env` file is automatically loaded from the project root.

#### Board Mapping Configuration

Create a `trello-sync.yaml` file in the project root to configure board-to-folder mappings:

```yaml
# Global settings
obsidian_root: null  # Optional, defaults to OBSIDIAN_ROOT env var
default_assets_folder: ".local_assets/Trello"  # Relative to obsidian_root

# Board mappings
boards:
  - board_id: "your_board_id_here"
    enabled: true
    target_path: "20_tasks/Trello/{org}/{board}/{column}/{card}.md"
    assets_folder: ".local_assets/Trello/{org}/{board}"  # Optional override
    workspace_name: "Your Workspace Name"  # For path substitution
```

**Path Template Variables:**
- `{org}` - Workspace/organization name (sanitized)
- `{board}` - Board name (sanitized)
- `{column}` - List/column name (sanitized)
- `{card}` - Card name (sanitized, without .md extension)

**Obsidian Root:**
- Set via `OBSIDIAN_ROOT` environment variable (recommended)
- Or set `obsidian_root` in `trello-sync.yaml`
- Config file value overrides environment variable

**Note:** Only boards listed in the configuration will be synced. Unconfigured boards are skipped.

#### Configuration Commands

```bash
# Show current configuration
trello-sync config

# Validate configuration file
trello-sync config-validate

# Interactive config addition for a board
trello-sync config-add <board-id>
```

## Related Documentation

- `.cursor/rules/trello-structure.mdc` - Directory structure and card format
- `.cursor/rules/trello-sync.mdc` - Sync workflow
- `.cursor/rules/trello-utilities.mdc` - Utility functions
- `.cursor/rules/trello-indexes.mdc` - Index file formats

