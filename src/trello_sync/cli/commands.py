"""CLI command definitions for Trello sync."""

import os
from pathlib import Path
from typing import Any

import click
import yaml
from dotenv import load_dotenv

from trello_sync.services.trello_sync import TrelloSync
from trello_sync.utils.config import (
    ConfigError,
    get_config_path,
    get_obsidian_root,
    load_config,
    save_config,
    validate_config,
)

# Load environment variables
load_dotenv()


@click.group()
def cli() -> None:
    """Trello Sync CLI - Sync Trello boards to local markdown files."""
    pass


@cli.command()
@click.argument('board_id')
@click.option('--board-name', help='Board name (optional, will fetch if not provided)')
@click.option('--workspace-name', help='Workspace name (optional, will fetch if not provided)')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without making changes')
def sync(
    board_id: str,
    board_name: str | None,
    workspace_name: str | None,
    dry_run: bool,
) -> None:
    """Sync a board to local files.

    Args:
        board_id: The ID of the board to sync.
        board_name: Optional board name.
        workspace_name: Optional workspace name.
        dry_run: If True, show what would be synced without making changes.
    """
    try:
        sync_client = TrelloSync()
        click.echo(f"Syncing board: {board_id}")
        
        stats = sync_client.sync_board(board_id, board_name, workspace_name, dry_run)
        
        click.echo(f"\n{'='*50}")
        click.echo(f"Sync complete!")
        click.echo(f"Total cards: {stats['total_cards']}")
        click.echo(f"Synced: {stats['synced_cards']}")
        click.echo(f"Skipped: {stats['skipped_cards']}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error syncing board: {e}")


@cli.command()
def list_boards() -> None:
    """List all accessible boards."""
    try:
        sync_client = TrelloSync()
        boards = sync_client.get_boards()
        
        click.echo(f"\nFound {len(boards)} boards:\n")
        for board in boards:
            status = "closed" if board.get('closed') else "open"
            click.echo(f"  {board['id']:20} {board['name']:40} ({status})")
        click.echo()
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error listing boards: {e}")


@cli.command()
@click.argument('board_id')
def show_board(board_id: str) -> None:
    """Show board details and lists.

    Args:
        board_id: The ID of the board to show.
    """
    try:
        sync_client = TrelloSync()
        board = sync_client.get_board(board_id)
        lists = sync_client.get_board_lists(board_id)
        
        click.echo(f"\nBoard: {board['name']}")
        click.echo(f"ID: {board['id']}")
        click.echo(f"URL: {board.get('url', 'N/A')}")
        click.echo(f"\nLists ({len(lists)}):\n")
        for list_data in lists:
            closed = " (closed)" if list_data.get('closed') else ""
            click.echo(f"  {list_data['id']:20} {list_data['name']}{closed}")
        click.echo()
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error showing board: {e}")


@cli.command()
def config() -> None:
    """Show current configuration."""
    try:
        config = load_config()
        config_path = get_config_path()
        
        click.echo(f"\nConfiguration file: {config_path}")
        click.echo(f"Exists: {config_path.exists()}\n")
        
        # Show Obsidian root
        try:
            obsidian_root = get_obsidian_root()
            click.echo(f"Obsidian Root: {obsidian_root}")
        except ConfigError as e:
            click.echo(f"Obsidian Root: Not configured ({e})")
        click.echo()
        
        # Show default assets folder
        default_assets = config.get('default_assets_folder', '.local_assets/Trello')
        click.echo(f"Default Assets Folder: {default_assets}")
        click.echo()
        
        # Show board configurations
        boards = config.get('boards', [])
        click.echo(f"Configured Boards: {len(boards)}\n")
        
        for board_config in boards:
            board_id = board_config.get('board_id', 'unknown')
            enabled = board_config.get('enabled', True)
            target_path = board_config.get('target_path', 'N/A')
            workspace = board_config.get('workspace_name', 'N/A')
            
            status = "enabled" if enabled else "disabled"
            click.echo(f"  Board ID: {board_id}")
            click.echo(f"    Status: {status}")
            click.echo(f"    Target Path: {target_path}")
            click.echo(f"    Workspace: {workspace}")
            click.echo()
        
        if not boards:
            click.echo("  No boards configured.")
            click.echo("  Use 'trello-sync config-add <board-id>' to add a board.")
            click.echo()
            
    except ConfigError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error loading config: {e}")


@cli.command()
@click.argument('board_id')
@click.option('--target-path', help='Target path template (e.g., "20_tasks/Trello/{org}/{board}/{column}/{card}.md")')
@click.option('--workspace-name', help='Workspace name for path substitution')
@click.option('--assets-folder', help='Assets folder template (optional)')
@click.option('--enabled/--disabled', default=True, help='Enable or disable this board')
def config_add(
    board_id: str,
    target_path: str | None,
    workspace_name: str | None,
    assets_folder: str | None,
    enabled: bool,
) -> None:
    """Add or update board configuration.
    
    Args:
        board_id: The Trello board ID to configure.
    """
    try:
        config_path = get_config_path()
        
        # Load existing config
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {
                'obsidian_root': None,
                'default_assets_folder': '.local_assets/Trello',
                'boards': [],
            }
        
        # Get board info if not provided
        if not target_path:
            sync_client = TrelloSync()
            board = sync_client.get_board(board_id)
            board_name = board.get('name', 'Unknown Board')
            org = board.get('organization', {})
            org_name = org.get('displayName', '') if org else ''
            
            if not workspace_name:
                workspace_name = org_name
            
            # Suggest default path
            default_path = '20_tasks/Trello/{org}/{board}/{column}/{card}.md'
            click.echo(f"\nBoard: {board_name}")
            if workspace_name:
                click.echo(f"Workspace: {workspace_name}")
            click.echo(f"\nSuggested target path: {default_path}")
            target_path = click.prompt("Target path template", default=default_path)
        
        if not workspace_name:
            workspace_name = click.prompt("Workspace name (for {org} substitution)", default='')
        
        # Find existing board config
        boards = config.get('boards', [])
        board_index = None
        for i, board_config in enumerate(boards):
            if board_config.get('board_id') == board_id:
                board_index = i
                break
        
        # Create or update board config
        board_config = {
            'board_id': board_id,
            'enabled': enabled,
            'target_path': target_path,
        }
        
        if workspace_name:
            board_config['workspace_name'] = workspace_name
        
        if assets_folder:
            board_config['assets_folder'] = assets_folder
        
        if board_index is not None:
            boards[board_index] = board_config
            click.echo(f"\nUpdated configuration for board {board_id}")
        else:
            boards.append(board_config)
            click.echo(f"\nAdded configuration for board {board_id}")
        
        config['boards'] = boards
        
        # Write config file
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        click.echo(f"Configuration saved to {config_path}")
        
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error adding config: {e}")


@cli.command()
def config_validate() -> None:
    """Validate configuration file."""
    try:
        errors = validate_config()
        
        if errors:
            click.echo("\nConfiguration validation failed:\n")
            for error in errors:
                click.echo(f"  ❌ {error}")
            click.echo()
            raise click.ClickException("Configuration is invalid")
        else:
            click.echo("\n✅ Configuration is valid!\n")
            
            # Show additional info
            try:
                obsidian_root = get_obsidian_root()
                click.echo(f"Obsidian Root: {obsidian_root}")
                click.echo(f"  Exists: {obsidian_root.exists()}")
                click.echo()
            except ConfigError as e:
                click.echo(f"⚠️  Obsidian Root: {e}\n")
            
    except ConfigError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error validating config: {e}")


@cli.command()
@click.option('--output', '-o', help='Output file path (default: watching.md in project root)')
def watching(output: str | None) -> None:
    """Generate watching.md file with all cards you are watching.
    
    This command queries the Trello API to find all cards across all boards
    that you are subscribed to (watching), and generates a markdown table
    with links to the local card files, board names, short links, and last
    update times.
    """
    try:
        sync_client = TrelloSync()
        click.echo("Fetching watched cards from Trello...")
        
        output_path = Path(output) if output else None
        result_path, card_count = sync_client.generate_watching_file(output_path)
        
        click.echo(f"\n✅ Generated watching.md file: {result_path}")
        click.echo(f"   Found {card_count} watched cards")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error generating watching file: {e}")


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be updated without making changes')
def config_update(dry_run: bool) -> None:
    """Update trello-sync.yaml with all accessible Trello boards.
    
    This command:
    - Adds any boards that are missing from the configuration
    - Removes boards that no longer exist in Trello
    - Preserves existing board configurations (enabled, target_path, etc.)
    - Updates board names, org names, and workspace names from Trello
    
    This is a one-time setup command to populate your configuration file.
    """
    try:
        config_path = get_config_path()
        config = load_config()
        existing_boards = config.get('boards', []) or []
        
        # Create a map of existing board configs by board_id
        existing_by_id: dict[str, dict[str, Any]] = {}
        for board_config in existing_boards:
            board_id = board_config.get('board_id')
            if board_id:
                existing_by_id[board_id] = board_config.copy()
        
        # Fetch all boards from Trello
        click.echo("Fetching boards from Trello...")
        sync_client = TrelloSync()
        trello_boards = sync_client.get_boards()
        trello_board_ids = {board['id'] for board in trello_boards}
        
        click.echo(f"Found {len(trello_boards)} boards in Trello")
        
        # Create a map of Trello boards by ID
        trello_by_id: dict[str, dict[str, Any]] = {}
        for board in trello_boards:
            trello_by_id[board['id']] = board
        
        # Determine what needs to be added/removed/updated
        boards_to_add: list[str] = []
        boards_to_remove: list[str] = []
        boards_to_update: list[str] = []
        
        for board_id in trello_board_ids:
            if board_id not in existing_by_id:
                boards_to_add.append(board_id)
            else:
                boards_to_update.append(board_id)
        
        for board_id in existing_by_id:
            if board_id not in trello_board_ids:
                boards_to_remove.append(board_id)
        
        if dry_run:
            click.echo("\n" + "="*50)
            click.echo("DRY RUN - No changes will be made")
            click.echo("="*50)
        
        click.echo(f"\nBoards to add: {len(boards_to_add)}")
        click.echo(f"Boards to update: {len(boards_to_update)}")
        click.echo(f"Boards to remove: {len(boards_to_remove)}")
        
        if boards_to_remove:
            click.echo("\nBoards that will be removed (no longer in Trello):")
            for board_id in boards_to_remove:
                board_config = existing_by_id[board_id]
                board_name = board_config.get('board_name', 'Unknown')
                click.echo(f"  - {board_name} ({board_id})")
        
        if boards_to_add:
            click.echo("\nBoards that will be added:")
            for board_id in boards_to_add:
                board = trello_by_id[board_id]
                click.echo(f"  - {board['name']} ({board_id})")
        
        if dry_run:
            click.echo("\nRun without --dry-run to apply changes.")
            return
        
        # Fetch full board details for new boards
        new_boards: list[dict[str, Any]] = []
        updated_count = 0
        
        click.echo("\nFetching board details...")
        for board_id in boards_to_add:
            board = trello_by_id[board_id]
            board_details = sync_client.get_board(board_id)
            
            # Extract organization name
            org = board_details.get('organization', {})
            org_name = org.get('displayName', '') if org else ''
            workspace_name = org_name
            
            new_board_config = {
                'board_id': board_id,
                'board_name': board['name'],
                'enabled': False,
                'target_path': '20_tasks/Trello/{org}/{board}/{column}/{card}.md',
                'workspace_name': workspace_name,
            }
            
            if org_name:
                new_board_config['org'] = org_name
            
            new_boards.append(new_board_config)
            updated_count += 1
            click.echo(f"  [{updated_count}/{len(boards_to_add)}] {board['name']}")
        
        # Update existing boards with latest info
        for board_id in boards_to_update:
            board = trello_by_id[board_id]
            board_details = sync_client.get_board(board_id)
            
            # Extract organization name
            org = board_details.get('organization', {})
            org_name = org.get('displayName', '') if org else ''
            workspace_name = org_name
            
            existing_config = existing_by_id[board_id]
            
            # Update board name and org info, but preserve other settings
            existing_config['board_name'] = board['name']
            existing_config['workspace_name'] = workspace_name
            if org_name:
                existing_config['org'] = org_name
            elif 'org' in existing_config:
                # Remove org if board no longer has one
                del existing_config['org']
            
            # Ensure required fields exist
            if 'enabled' not in existing_config:
                existing_config['enabled'] = False
            if 'target_path' not in existing_config:
                existing_config['target_path'] = '20_tasks/Trello/{org}/{board}/{column}/{card}.md'
        
        # Build final boards list
        final_boards: list[dict[str, Any]] = []
        
        # Add updated existing boards
        for board_id in trello_board_ids:
            if board_id in existing_by_id:
                final_boards.append(existing_by_id[board_id])
        
        # Add new boards
        final_boards.extend(new_boards)
        
        # Update config
        config['boards'] = final_boards
        
        # Save config
        save_config(config)
        
        click.echo(f"\n✅ Configuration updated!")
        click.echo(f"   Added: {len(boards_to_add)} boards")
        click.echo(f"   Updated: {len(boards_to_update)} boards")
        click.echo(f"   Removed: {len(boards_to_remove)} boards")
        click.echo(f"   Total boards: {len(final_boards)}")
        click.echo(f"   Saved to: {config_path}")
        
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error updating config: {e}")

