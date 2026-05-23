import sqlite3
import pytest
import ostraca_cli.db as db


@pytest.fixture
def temp_db(tmp_path):
    # Patch DB_PATH to point to a temp file in tmp_path
    original_path = db.DB_PATH
    test_db_path = tmp_path / "test_notes.db"
    db.DB_PATH = test_db_path
    db.init_db()
    yield test_db_path
    # Restore DB_PATH
    db.DB_PATH = original_path


def test_wal_mode_and_index(temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Check journal mode
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]
    assert journal_mode == "wal"

    # Check indexes on 'notes' table
    cursor.execute("PRAGMA index_list(notes)")
    indexes = [row[1] for row in cursor.fetchall()]
    assert "idx_notes_title" in indexes

    conn.close()


def test_fts_sync_triggers(temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Test INSERT
    cursor.execute(
        "INSERT INTO notes (id, title, content, para_category, tags) "
        "VALUES ('id1', 'Testing Notes', 'Content of test', 'Project', 'test')"
    )
    conn.commit()

    cursor.execute("SELECT * FROM notes_fts WHERE title MATCH 'Testing'")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Testing Notes"

    # Test UPDATE
    cursor.execute(
        "UPDATE notes SET title = 'Updated Title', content = 'Updated content' WHERE id = 'id1'"
    )
    conn.commit()

    cursor.execute("SELECT * FROM notes_fts WHERE title MATCH 'Updated'")
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "Updated Title"

    # Test DELETE
    cursor.execute("DELETE FROM notes WHERE id = 'id1'")
    conn.commit()

    cursor.execute("SELECT * FROM notes_fts WHERE title MATCH 'Updated'")
    assert cursor.fetchone() is None

    conn.close()
