"""Trello Sync - One-way sync of Trello boards to local markdown files."""

__version__ = '0.1.0'

from trello_sync.cli import cli
from trello_sync.services import TrelloSync

__all__ = ['TrelloSync', 'cli']

