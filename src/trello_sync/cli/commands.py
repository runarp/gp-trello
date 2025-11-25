"""CLI command definitions for Trello sync."""

import click
from dotenv import load_dotenv

from trello_sync.services.trello_sync import TrelloSync
from trello_sync.utils.config import (
    ConfigError,
    get_obsidian_root,
    load_config,
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
        
        if stats['total_cards'] == 0:
            click.echo(f"\n⚠ Board {board_id} is not configured or has no cards to sync.")
            click.echo("Use 'trello-sync config-add {board_id}' to configure this board.")
            return
        
        click.echo(f"\n{'='*50}")
        click.echo(f"Sync complete!")
        click.echo(f"Total cards: {stats['total_cards']}")
        click.echo(f"Synced: {stats['synced_cards']}")
        click.echo(f"Skipped: {stats['skipped_cards']}")
    except ConfigError as e:
        raise click.ClickException(f"Configuration error: {e}")
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
        config_data = load_config()
        obsidian_root = get_obsidian_root()
        
        click.echo("\nConfiguration:")
        click.echo("=" * 50)
        
        if obsidian_root:
            click.echo(f"OBSIDIAN_ROOT (env): {obsidian_root}")
        else:
            click.echo("OBSIDIAN_ROOT (env): Not set")
        
        if config_data.get('obsidian_root'):
            click.echo(f"obsidian_root (config): {config_data['obsidian_root']}")
        
        if config_data.get('default_assets_folder'):
            click.echo(f"default_assets_folder: {config_data['default_assets_folder']}")
        
        boards = config_data.get('boards', [])
        click.echo(f"\nConfigured boards: {len(boards)}")
        for board in boards:
            enabled = "✓" if board.get('enabled', True) else "✗"
            click.echo(f"  {enabled} {board.get('board_id', 'unknown')}")
            if board.get('target_path'):
                click.echo(f"    Path: {board['target_path']}")
        click.echo()
    except ConfigError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error reading config: {e}")


@cli.command()
def config_validate() -> None:
    """Validate configuration file."""
    try:
        config_data = load_config()
        errors = validate_config(config_data)
        
        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  ✗ {error}")
            raise click.ClickException("Configuration validation failed")
        else:
            click.echo("✓ Configuration is valid")
    except ConfigError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error validating config: {e}")


@cli.command()
@click.argument('board_id')
def config_add(board_id: str) -> None:
    """Add a board to configuration (interactive).

    Args:
        board_id: The ID of the board to configure.
    """
    try:
        sync_client = TrelloSync()
        board = sync_client.get_board(board_id)
        board_name = board['name']
        workspace_name = board.get('organization', {}).get('displayName', '')
        
        click.echo(f"\nConfiguring board: {board_name}")
        click.echo(f"Board ID: {board_id}")
        click.echo(f"Workspace: {workspace_name}")
        
        # Get target path
        default_path = "20_tasks/Trello/{org}/{board}/{column}/{card}.md"
        target_path = click.prompt(
            "Target path template",
            default=default_path,
            type=str,
        )
        
        # Get assets folder
        default_assets = ".local_assets/Trello/{org}/{board}"
        assets_folder = click.prompt(
            "Assets folder template",
            default=default_assets,
            type=str,
        )
        
        click.echo("\nConfiguration to add:")
        click.echo(f"  board_id: {board_id}")
        click.echo(f"  enabled: true")
        click.echo(f"  target_path: {target_path}")
        click.echo(f"  assets_folder: {assets_folder}")
        if workspace_name:
            click.echo(f"  workspace_name: {workspace_name}")
        
        if click.confirm("\nAdd this configuration?"):
            click.echo("\nPlease add this to your trello-sync.yaml file:")
            click.echo("  boards:")
            click.echo(f"    - board_id: \"{board_id}\"")
            click.echo(f"      enabled: true")
            click.echo(f"      target_path: \"{target_path}\"")
            click.echo(f"      assets_folder: \"{assets_folder}\"")
            if workspace_name:
                click.echo(f"      workspace_name: \"{workspace_name}\"")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Error adding config: {e}")

