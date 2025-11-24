"""CLI command definitions for Trello sync."""

import click
from dotenv import load_dotenv

from trello_sync.services.trello_sync import TrelloSync

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

