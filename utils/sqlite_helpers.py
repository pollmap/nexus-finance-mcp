"""
Shared SQLite connection helpers.

Provides a factory for creating WAL-mode SQLite connections
with consistent pragmas across all servers.

Used by: memory_server.py, vault_index_server.py
"""
import sqlite3
from pathlib import Path


def get_db(db_path: str, mkdir: bool = True) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and Row factory.

    Args:
        db_path: Path to the SQLite database file.
        mkdir: If True, create parent directories if they don't exist.
    """
    if mkdir:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    return db
