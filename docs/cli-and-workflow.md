# Trello Sync CLI Interface and Workflow Documentation

## Overview

The Trello Sync utility provides a command-line interface for continuously syncing Trello boards to local markdown files. It supports one-way synchronization (Trello → Local) with incremental updates, configurable directory structures, and attachment handling.

## Table of Contents

1. [CLI Interface](#cli-interface)
2. [Continuous Sync Workflow](#continuous-sync-workflow)
3. [Configuration Management](#configuration-management)
4. [Sync Process Details](#sync-process-details)
5. [Best Practices](#best-practices)

---

## CLI Interface

The CLI is built with Click and provides commands for managing boards, syncing cards, and configuring the sync process.

### Entry Point

The CLI can be invoked in two ways:

```bash
# As a Python module
python -m trello_sync.cli <command>

# As an installed package (after: pip install -e .)
trello-sync <command>
```

### Available Commands

#### 1. `sync` - Sync a Board to Local Files

Syncs a single Trello board to local markdown files based on configuration.

**Usage:**
```bash
trello-sync sync <board-id> [OPTIONS]
```

**Arguments:**
- `board-id` (required): The Trello board ID to sync

**Options:**
- `--board-name TEXT`: Board name (optional, will fetch if not provided)
- `--workspace-name TEXT`: Workspace name (optional, will fetch if not provided)
- `--dry-run`: Show what would be synced without making changes

**Examples:**
```bash
# Sync a board
trello-sync sync 5ded9c075c1e84205a177833

# Dry run to preview changes
trello-sync sync 5ded9c075c1e84205a177833 --dry-run

# Sync with explicit names
trello-sync sync 5ded9c075c1e84205a177833 \
  --board-name "My Board" \
  --workspace-name "My Workspace"
```

**Output:**
```
Syncing board: 5ded9c075c1e84205a177833

==================================================
Sync complete!
Total cards: 25
Synced: 8
Skipped: 17
```

**Behavior:**
- Only syncs boards that are configured in `trello-sync.yaml`
- Only syncs boards with `enabled: true`
- Performs incremental sync: compares file modification time with card update time
- Skips cards that haven't changed since last sync
- Downloads attachments and stores them in configured assets folder
- Generates markdown files with YAML frontmatter

---

#### 2. `list-boards` - List All Accessible Boards

Lists all Trello boards accessible to the authenticated user.

**Usage:**
```bash
trello-sync list-boards
```

**Output:**
```
Found 15 boards:

  5ded9c075c1e84205a177833  Boracay Projects                    (open)
  612f47d4da814d25c8947c28  z2 - Legal                          (open)
  6708adbfb99b16d3ecb154cc  GP Forever                         (closed)
  ...
```

**Use Cases:**
- Discover board IDs for configuration
- Verify authentication
- See all accessible boards (including closed ones)

---

#### 3. `show-board` - Show Board Details and Lists

Displays detailed information about a specific board, including all lists.

**Usage:**
```bash
trello-sync show-board <board-id>
```

**Arguments:**
- `board-id` (required): The Trello board ID

**Output:**
```
Board: GP Family Office
ID: 5ded9c075c1e84205a177833
URL: https://trello.com/b/5ded9c075c1e84205a177833

Lists (6):

  5f8a1b2c3d4e5f6a7b8c9d0e  Incoming
  5f8a1b2c3d4e5f6a7b8c9d0f  Prioritized Projects
  5f8a1b2c3d4e5f6a7b8c9d10  Current Tasks
  5f8a1b2c3d4e5f6a7b8c9d11  Waiting
  5f8a1b2c3d4e5f6a7b8c9d12  Completed
  5f8a1b2c3d4e5f6a7b8c9d13  On Ice (closed)
```

**Use Cases:**
- Get list IDs for path configuration
- Verify board structure
- Check board status and URL

---

#### 4. `config` - Show Current Configuration

Displays the current configuration from `trello-sync.yaml`.

**Usage:**
```bash
trello-sync config
```

**Output:**
```
Configuration file: /path/to/trello-sync.yaml
Exists: true

Obsidian Root: /Users/runar/Projects/runarp/GPkb
Default Assets Folder: .local_assets/Trello

Configured Boards: 3

  Board ID: 5ded9c075c1e84205a177833
    Status: enabled
    Target Path: 20_tasks/Trello/{org}/{board}/{column}/{card}.md
    Workspace: Family Office

  Board ID: 612f47d4da814d25c8947c28
    Status: disabled
    Target Path: 20_tasks/Trello/{org}/{board}/{column}/{card}.md
    Workspace: z2
```

**Use Cases:**
- Verify configuration is loaded correctly
- Check which boards are enabled/disabled
- See path templates and workspace mappings

---

#### 5. `config-init` - Initialize Configuration File

Initializes or updates `trello-sync.yaml` with all accessible Trello boards.

**Usage:**
```bash
trello-sync config-init [OPTIONS]
```

**Options:**
- `--force`: Overwrite existing configuration (use with caution)

**Behavior:**
- **If config exists and `--force` is not used:**
  - Adds missing boards (with `enabled: false` by default)
  - Removes boards that no longer exist in Trello
  - Preserves existing board settings (enabled, target_path, etc.)
  - Updates board names, org names, and workspace names from Trello

- **If config doesn't exist or `--force` is used:**
  - Creates new configuration file
  - Fetches all accessible boards
  - Sets all boards to `enabled: false` by default
  - Uses default path template: `20_tasks/Trello/{org}/{board}/{column}/{card}.md`

**Output:**
```
Fetching boards from Trello...
Found 15 accessible boards

Existing boards in config: 3
Boards to add: 12
Boards to remove: 0

Updated 3 existing board(s)
Added 12 new board(s)

✅ Configuration saved to /path/to/trello-sync.yaml
   Total boards: 15
```

**Use Cases:**
- Initial setup of configuration file
- Update configuration when new boards are added to Trello
- Refresh board names and organization information

---

#### 6. `config-add` - Add or Update Board Configuration

Adds or updates configuration for a specific board (interactive).

**Usage:**
```bash
trello-sync config-add <board-id> [OPTIONS]
```

**Arguments:**
- `board-id` (required): The Trello board ID to configure

**Options:**
- `--target-path TEXT`: Target path template (e.g., `"20_tasks/Trello/{org}/{board}/{column}/{card}.md"`)
- `--workspace-name TEXT`: Workspace name for path substitution
- `--assets-folder TEXT`: Assets folder template (optional)
- `--enabled / --disabled`: Enable or disable this board (default: enabled)

**Interactive Mode:**
If `--target-path` is not provided, the command will:
1. Fetch board details from Trello
2. Display board name and workspace
3. Suggest default path template
4. Prompt for target path template
5. Prompt for workspace name if not provided

**Examples:**
```bash
# Interactive mode
trello-sync config-add 5ded9c075c1e84205a177833

# Non-interactive mode
trello-sync config-add 5ded9c075c1e84205a177833 \
  --target-path "20_tasks/Trello/{org}/{board}/{column}/{card}.md" \
  --workspace-name "Family Office" \
  --enabled

# Disable a board
trello-sync config-add 5ded9c075c1e84205a177833 --disabled
```

**Use Cases:**
- Configure a new board
- Update path template for an existing board
- Enable or disable a board

---

#### 7. `config-update` - Update Configuration with All Boards

Updates `trello-sync.yaml` with all accessible Trello boards (similar to `config-init` but more focused on updates).

**Usage:**
```bash
trello-sync config-update [OPTIONS]
```

**Options:**
- `--dry-run`: Preview what would be updated without making changes

**Behavior:**
- Adds any boards that are missing from the configuration
- Removes boards that no longer exist in Trello
- Preserves existing board configurations (enabled, target_path, etc.)
- Updates board names, org names, and workspace names from Trello

**Output (dry-run):**
```
Fetching boards from Trello...
Found 15 boards in Trello

==================================================
DRY RUN - No changes will be made
==================================================

Boards to add: 2
Boards to update: 13
Boards to remove: 0

Boards that will be added:
  - New Board Name (5ded9c075c1e84205a177833)
  - Another Board (612f47d4da814d25c8947c28)

Run without --dry-run to apply changes.
```

**Use Cases:**
- Keep configuration in sync with Trello
- Update board metadata without losing custom settings
- Preview changes before applying

---

#### 8. `config-validate` - Validate Configuration File

Validates the configuration file for errors.

**Usage:**
```bash
trello-sync config-validate
```

**Output (success):**
```
✅ Configuration is valid!

Obsidian Root: /Users/runar/Projects/runarp/GPkb
  Exists: true
```

**Output (errors):**
```
Configuration validation failed:

  ❌ Board config at index 2 missing 'board_id'
  ❌ Board 5ded9c075c1e84205a177833 target_path missing required variable: {card}

Configuration is invalid
```

**Validation Checks:**
- YAML syntax is valid
- Required fields are present (`board_id`, `enabled`, `target_path`)
- Path templates contain required variables (`{org}`, `{board}`, `{column}`, `{card}`)
- Obsidian root path exists (if configured)

**Use Cases:**
- Verify configuration before syncing
- Debug configuration issues
- CI/CD validation

---

#### 9. `watching` - Generate Watching File

Generates a `watching.md` file listing all cards the authenticated user is watching (subscribed to) across all boards.

**Usage:**
```bash
trello-sync watching [OPTIONS]
```

**Options:**
- `--output, -o PATH`: Output file path (default: `watching.md` in project root)

**Output:**
Creates a markdown file with a table of watched cards:

```markdown
# Watching

Cards you are watching across all Trello boards.

| Card | Board | Short Link | Last Updated |
|------|-------|------------|--------------|
| [Card Name](path/to/card.md) | Board Name | [abc123](https://trello.com/c/abc123) | Jan 20, 2025 |
| [Another Card](path/to/another.md) | Board Name | [def456](https://trello.com/c/def456) | Jan 19, 2025 |
```

**Features:**
- Links to local card files (if they exist)
- Falls back to Trello short links if local file not found
- Sorted by last activity date (most recent first)
- Includes board name and short link for each card

**Use Cases:**
- Create a dashboard of cards you're watching
- Track important cards across multiple boards
- Generate a quick reference file

---

### Error Handling

All commands handle errors gracefully:

- **Missing credentials**: Clear error message directing to set `TRELLO_API_KEY` and `TRELLO_TOKEN`
- **Invalid board ID**: Error message with board ID
- **Configuration errors**: Validation errors with specific field names
- **Network errors**: HTTP error messages from Trello API
- **File system errors**: Permission and path errors

---

## Continuous Sync Workflow

### Overview

The Trello Sync utility is designed for **continuous, incremental synchronization** of Trello boards to local markdown files. The workflow supports:

1. **One-way sync**: Trello → Local (cards are downloaded, not uploaded)
2. **Incremental updates**: Only changed cards are synced
3. **Configurable structure**: Custom directory layouts per board
4. **Attachment handling**: Automatic download and organization
5. **Multiple boards**: Sync multiple boards with different configurations

### Workflow Architecture

```
┌─────────────┐
│   Trello    │
│    API      │
└──────┬──────┘
       │
       │ Fetch boards, lists, cards
       │
┌──────▼─────────────────────────────────────┐
│         TrelloSync Service                │
│  - Authentication                         │
│  - API requests                           │
│  - Data transformation                    │
└──────┬────────────────────────────────────┘
       │
       │ Process cards
       │
┌──────▼─────────────────────────────────────┐
│      Configuration System                  │
│  - Board configuration                    │
│  - Path templates                         │
│  - Enabled/disabled boards                │
└──────┬────────────────────────────────────┘
       │
       │ Resolve paths
       │
┌──────▼─────────────────────────────────────┐
│      File System                          │
│  - Markdown generation                    │
│  - Attachment download                    │
│  - Directory creation                     │
└───────────────────────────────────────────┘
```

### Sync Process Flow

#### Step 1: Configuration Loading

1. Load `trello-sync.yaml` from project root
2. Validate configuration
3. Get Obsidian root path (from config or `OBSIDIAN_ROOT` env var)
4. Filter boards to only those with `enabled: true`

#### Step 2: Board Processing

For each enabled board:

1. **Fetch board details** from Trello API
   - Board name
   - Organization/workspace name
   - Board metadata

2. **Resolve path templates**
   - Get `target_path` template from board config
   - Get `assets_folder` template (board-specific or default)
   - Prepare variable substitution context

3. **Fetch board lists**
   - Get all lists (including closed lists)
   - Filter to open lists (configurable)

#### Step 3: Card Processing

For each card in each list:

1. **Check if sync is needed**
   - Get card's `dateLastActivity` from Trello
   - Check if local file exists
   - Compare file modification time with card update time
   - Skip if file is newer than card update

2. **Fetch full card details** (if sync needed)
   - Card description
   - Comments
   - Attachments
   - Labels
   - Members
   - Checklists
   - Due dates
   - Custom fields

3. **Resolve file path**
   - Substitute path template variables:
     - `{org}` → Workspace name (sanitized)
     - `{board}` → Board name (sanitized)
     - `{column}` → List name (sanitized)
     - `{card}` → Card name (sanitized)
   - Resolve relative to Obsidian root

4. **Download attachments** (if any)
   - Filter to file attachments (not links)
   - Resolve assets folder path
   - Download files with sanitized names
   - Handle duplicate filenames (append counter)
   - Calculate relative paths for markdown

5. **Generate markdown**
   - Create YAML frontmatter with metadata
   - Format card description
   - Format checklists
   - Format attachments (images inline, files as links)
   - Format comments with author and timestamp
   - Format labels and members

6. **Write file**
   - Create parent directories if needed
   - Write markdown content to file
   - Update sync statistics

#### Step 4: Completion

1. **Report statistics**
   - Total cards processed
   - Cards synced
   - Cards skipped (unchanged)

2. **Error handling**
   - Continue processing other cards if one fails
   - Log errors for review
   - Return exit code based on success/failure

### Incremental Sync Logic

The sync process uses **file modification time comparison** to determine if a card needs syncing:

```python
def should_sync_card(card_path: Path, card_updated: str) -> bool:
    if not card_path.exists():
        return True  # File doesn't exist, sync it
    
    file_mtime = datetime.fromtimestamp(card_path.stat().st_mtime)
    card_updated_dt = datetime.fromisoformat(card_updated.replace('Z', '+00:00'))
    
    # Sync if card is newer than file
    return card_updated_dt > file_mtime
```

**Benefits:**
- Only processes changed cards
- Faster sync times
- Reduces API calls
- Preserves local modifications (one-way sync)

**Limitations:**
- Local file modifications are not synced back to Trello
- Manual file edits may be overwritten on next sync
- File system timezone differences may cause issues

### Path Template System

The path template system allows flexible directory structures:

**Template Variables:**
- `{org}` - Workspace/organization name (sanitized for filesystem)
- `{board}` - Board name (sanitized)
- `{column}` - List/column name (sanitized)
- `{card}` - Card name (sanitized, without .md extension)

**Example Templates:**
```yaml
# Flat structure by board
target_path: "Trello/{board}/{card}.md"

# Organized by workspace and board
target_path: "20_tasks/Trello/{org}/{board}/{column}/{card}.md"

# Custom structure
target_path: "Projects/{org}/{board}/Cards/{column}/{card}.md"
```

**Sanitization:**
- Removes invalid filesystem characters
- Replaces spaces with hyphens
- Handles special characters
- Ensures valid filenames

### Attachment Handling

Attachments are handled separately from card files:

1. **Download location**: Configured via `assets_folder` template
2. **File organization**: Grouped by workspace and board
3. **Image handling**: Rendered inline in markdown
4. **File handling**: Linked in markdown with metadata
5. **Link handling**: Preserved as external links

**Example structure:**
```
[Obsidian Root]/
├── 20_tasks/
│   └── Trello/
│       └── Family-Office/
│           └── GP-Family-Office/
│               └── Current-Tasks/
│                   └── repair-desk.md
└── .local_assets/
    └── Trello/
        └── Family-Office/
            └── GP-Family-Office/
                ├── screenshot.png
                └── document.pdf
```

### Continuous Sync Strategies

#### Strategy 1: Scheduled Sync (Cron/Systemd)

Run sync on a schedule:

```bash
# Cron example (every hour)
0 * * * * cd /path/to/project && trello-sync sync <board-id>
```

**Pros:**
- Automated
- Predictable
- Low resource usage

**Cons:**
- Not real-time
- Requires scheduling setup

#### Strategy 2: Manual Sync

Run sync when needed:

```bash
# Sync all enabled boards
for board_id in $(trello-sync config | grep "Board ID" | awk '{print $3}'); do
    trello-sync sync $board_id
done
```

**Pros:**
- Full control
- On-demand
- No scheduling needed

**Cons:**
- Manual intervention required
- Easy to forget

#### Strategy 3: Watch Mode (Future)

Automatically sync on file changes or time intervals:

```bash
# Watch for changes and sync (not yet implemented)
trello-sync watch --interval 300  # Sync every 5 minutes
```

**Pros:**
- Automated
- Near real-time
- Efficient

**Cons:**
- Requires background process
- More complex

### Multi-Board Sync Workflow

To sync multiple boards:

1. **Configure all boards** in `trello-sync.yaml`
2. **Enable desired boards** (`enabled: true`)
3. **Run sync for each board** (or create a script)

**Example script:**
```bash
#!/bin/bash
# sync-all-boards.sh

# Get all enabled board IDs from config
boards=$(yq eval '.boards[] | select(.enabled == true) | .board_id' trello-sync.yaml)

for board_id in $boards; do
    echo "Syncing board: $board_id"
    trello-sync sync "$board_id"
done
```

---

## Configuration Management

### Configuration File: `trello-sync.yaml`

Located in the project root, this YAML file controls all sync behavior.

**Structure:**
```yaml
# Global settings
obsidian_root: /path/to/obsidian/vault  # Optional, defaults to OBSIDIAN_ROOT env var
default_assets_folder: .local_assets/Trello  # Default assets folder template

# Board mappings
boards:
  - board_id: "5ded9c075c1e84205a177833"
    board_name: "GP Family Office"  # Optional, for reference
    org: "Family Office"  # Optional, organization/workspace name
    enabled: true  # Enable/disable syncing
    target_path: "20_tasks/Trello/{org}/{board}/{column}/{card}.md"
    assets_folder: ".local_assets/Trello/{org}/{board}"  # Optional override
    workspace_name: "Family Office"  # Deprecated, use 'org' instead
```

### Configuration Workflow

1. **Initial Setup**
   ```bash
   # Initialize configuration with all boards
   trello-sync config-init
   
   # Enable desired boards
   trello-sync config-add <board-id> --enabled
   ```

2. **Update Configuration**
   ```bash
   # Update with new boards from Trello
   trello-sync config-update
   
   # Validate configuration
   trello-sync config-validate
   ```

3. **Modify Settings**
   ```bash
   # Update path template for a board
   trello-sync config-add <board-id> \
     --target-path "custom/path/{org}/{board}/{column}/{card}.md"
   ```

### Environment Variables

- `TRELLO_API_KEY`: Trello API key (required)
- `TRELLO_TOKEN` or `TRELLO_API_TOKEN`: Trello API token (required)
- `OBSIDIAN_ROOT`: Default Obsidian root path (optional, can be set in config)

---

## Sync Process Details

### Card Markdown Format

Each synced card is stored as a markdown file with:

**YAML Frontmatter:**
```yaml
---
trello_board_card_id: "68f804be4dbc3c3da44bb046"
board: "GP Family Office"
url: "https://trello.com/c/xsKdq6ZO/1621-repair-desk"
workspace: "Family Office"
created: "2025-01-15T10:30:00Z"
updated: "2025-01-20T14:22:00Z"
list: "Current Tasks"
labels: ["urgent", "home"]
members: ["John Doe", "Jane Smith"]
due-date: "2025-02-01T00:00:00Z"
attachments-count: 2
comments-count: 5
---
```

**Markdown Body:**
- Card title as H1 heading
- Description section
- Checklists (if any)
- Attachments (images inline, files as links)
- Comments with author and timestamp

### Attachment Processing

1. **Download**: File attachments are downloaded to assets folder
2. **Naming**: Filenames are sanitized and deduplicated
3. **Linking**: Relative paths calculated from card file to asset
4. **Rendering**: Images use `![alt](path)`, files use `[name](path)`

### Error Handling

- **API Errors**: Retry with exponential backoff
- **File Errors**: Log and continue with next card
- **Configuration Errors**: Fail fast with clear error messages
- **Network Errors**: Retry up to 3 times

---

## Best Practices

### 1. Initial Setup

1. Get Trello API credentials
2. Set up `.env` file with credentials
3. Run `trello-sync config-init` to discover boards
4. Enable and configure desired boards
5. Run `trello-sync config-validate` to verify
6. Test sync with `--dry-run` first

### 2. Regular Maintenance

1. Run `trello-sync config-update` periodically to refresh board metadata
2. Review enabled boards and disable unused ones
3. Monitor sync statistics for issues
4. Check attachment storage usage

### 3. Path Template Design

- Use descriptive templates that match your workflow
- Group by workspace for multi-workspace setups
- Use consistent naming conventions
- Consider Obsidian folder structure best practices

### 4. Sync Frequency

- **High-activity boards**: Sync daily or multiple times per day
- **Low-activity boards**: Sync weekly or on-demand
- **Critical boards**: Consider more frequent syncs

### 5. Backup Strategy

- Obsidian vault should be backed up regularly
- Attachment folder should be included in backups
- Configuration file should be version controlled

### 6. Performance Optimization

- Only enable boards you actively use
- Use incremental sync (automatic)
- Monitor API rate limits (300 requests per 10 seconds)
- Consider batching syncs for multiple boards

---

## Troubleshooting

### Common Issues

**Issue: "OBSIDIAN_ROOT not set"**
- Solution: Set `OBSIDIAN_ROOT` environment variable or configure in `trello-sync.yaml`

**Issue: "Board not configured"**
- Solution: Run `trello-sync config-add <board-id>` to configure the board

**Issue: "Invalid YAML in config file"**
- Solution: Run `trello-sync config-validate` to see specific errors

**Issue: "Rate limit exceeded"**
- Solution: Wait a few minutes and retry, or reduce sync frequency

**Issue: "File permission denied"**
- Solution: Check Obsidian root path permissions and ensure write access

---

## Related Documentation

- `README.md` - Project overview and quick start
- `docs/roadmap.md` - Future features and round-trip sync plans
- `.cursor/rules/trello-sync.mdc` - MCP-based sync workflow
- `.cursor/rules/trello-structure.mdc` - Card format specification
- `.cursor/rules/trello-utilities.mdc` - Utility functions reference

