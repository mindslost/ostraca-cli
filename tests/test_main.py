import pytest
from typer.testing import CliRunner
import ostraca_cli.db as db

# Run setup to patch db.DB_PATH before main is imported


@pytest.fixture(autouse=True)
def patch_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_notes.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    # Re-initialize the db for test isolation
    db.init_db()


def test_complete_note_identifier():
    import ostraca_cli.main as main
    # Insert some mock notes
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('id123456', 'Python Guide', 'Content', 'Resource', 'python')")
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('abcde789', 'SQLite Tutorial', 'Content', 'Resource', 'sqlite')")
        conn.commit()

    # Test incomplete matching ID
    comps = main.complete_note_identifier("id1")
    assert "id123456" in comps

    # Test incomplete matching Title
    comps = main.complete_note_identifier("Python")
    assert "Python Guide" in comps


def test_get_filtered_notes():
    import ostraca_cli.main as main
    # Insert notes
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('n1', 'Title 1', 'C1', 'Project', 'python,cli')")
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('n2', 'Title 2', 'C2', 'Area', 'sqlite')")
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('n3', 'Title 3', 'C3', 'Project', 'cli')")
        conn.commit()

    # Filter by category
    notes = main.get_filtered_notes(para="Project", tags=None)
    assert len(notes) == 2
    assert {n[0] for n in notes} == {"n1", "n3"}

    # Filter by tags (any of)
    notes = main.get_filtered_notes(para=None, tags="cli")
    assert len(notes) == 2
    assert {n[0] for n in notes} == {"n1", "n3"}

    # Filter by category and tags
    notes = main.get_filtered_notes(para="Project", tags="python")
    assert len(notes) == 1
    assert notes[0][0] == "n1"

    # Filter by tag not matching
    notes = main.get_filtered_notes(para=None, tags="java")
    assert len(notes) == 0


def test_cli_search():
    from ostraca_cli.main import app
    runner = CliRunner()

    # Insert a note
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (id, title, content, para_category, tags) VALUES ('n1', 'Vim Reference', 'How to use vim editor', 'Area', 'vim')")
        # Direct FTS insert to simulate trigger
        cursor.execute(
            "INSERT INTO notes_fts (rowid, title, content, tags) VALUES (1, 'Vim Reference', 'How to use vim editor', 'vim')")
        conn.commit()

    # Test CLI search
    result = runner.invoke(app, ["search", "vim"])
    assert result.exit_code == 0
    assert "Vim Reference" in result.stdout


def test_cli_add(monkeypatch):
    from ostraca_cli.main import app
    runner = CliRunner()

    # Mock edit_content to return fixed frontmatter and content
    mock_content = '---\ntitle: "Mocked Note"\npara: Project\ntags: [test]\n---\nSome content'
    monkeypatch.setattr("ostraca_cli.main.edit_content",
                        lambda x: mock_content)

    result = runner.invoke(app, ["add", "Mocked Note", "--para", "Project"])
    assert result.exit_code == 0
    assert "Mocked Note" in result.stdout
