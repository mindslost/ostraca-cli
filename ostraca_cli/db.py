"""
Database management for the Ostraca CLI.

This module handles SQLite database connections, schema initialization,
and Full-Text Search (FTS5) index synchronization using triggers.
"""

import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator, List, Optional

# Database file is stored in the user's home directory
DB_PATH: Path = Path.home() / ".para_notes.db"

# Valid PARA categories enforced by both Python and SQL CHECK constraints
PARA_CATEGORIES: List[str] = ["Project", "Area", "Resource", "Archive"]


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """
    Provide a transactional scope around a series of database operations.

    Yields:
        A sqlite3.Connection object.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def backup_db(target_path: Optional[Path] = None) -> Path:
    """
    Create a backup of the SQLite database using its built-in backup API.

    Args:
        target_path: Optional destination path. Defaults to DB_PATH with a timestamp.

    Returns:
        The Path to the created backup file.
    """
    if not target_path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        target_path = DB_PATH.with_suffix(f".bak_{timestamp}.db")

    # Ensure the directory for the target exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db() as source_conn:
        dest_conn = sqlite3.connect(target_path)
        try:
            with dest_conn:
                source_conn.backup(dest_conn)
        finally:
            dest_conn.close()

    return target_path


def restore_db(source_path: Path) -> None:
    """
    Restore the SQLite database from a backup file using the built-in backup API.

    Args:
        source_path: The path to the backup file.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Backup file not found at: {source_path}")

    # Use the backup API to restore into the live database
    with get_db() as dest_conn:
        source_conn = sqlite3.connect(source_path)
        try:
            source_conn.backup(dest_conn)
        finally:
            source_conn.close()


def init_db() -> None:
    """
    Initialize the SQLite database schema and FTS5 search index.

    Creates the 'notes' table with PARA category constraints,
    sets up the 'notes_fts' virtual table for searching,
    and installs triggers to keep the search index in sync.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Core Table: Stores the source of truth for all notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                para_category TEXT CHECK(para_category IN ('Project', 'Area', 'Resource', 'Archive')) NOT NULL,
                tags TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Search Index (FTS5): External content table for high-performance searching
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title,
                content,
                tags,
                content='notes',
                content_rowid='rowid'
            )
        """)

        # 3. Auto-Sync Triggers: Ensure 'notes_fts' stays updated as 'notes' changes

        # Trigger on INSERT: Add new records to the FTS index
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.rowid, new.title, new.content, new.tags);
            END;
        """)

        # Trigger on DELETE: Remove records from the FTS index
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
                VALUES('delete', old.rowid, old.title, old.content, old.tags);
            END;
        """)

        # Trigger on UPDATE: Refresh records in the FTS index
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
                VALUES('delete', old.rowid, old.title, old.content, old.tags);
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.rowid, new.title, new.content, new.tags);
            END;
        """)
        conn.commit()
