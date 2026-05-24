import datetime
import pytest
from typer.testing import CliRunner
import ostraca_cli.db as db
import ostraca_cli.main as main

@pytest.fixture(autouse=True)
def patch_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_notes.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    # Re-initialize the db for test isolation
    db.init_db()


def test_parse_due_date():
    # Test valid absolute dates
    parsed = main.parse_due_date("05-24-2026 15:30")
    assert parsed == "2026-05-24 15:30"

    parsed_date_only = main.parse_due_date("05-24-2026")
    assert parsed_date_only == "2026-05-24 23:59"

    # Test relative shortcuts
    today_parsed = main.parse_due_date("today")
    now = datetime.datetime.now()
    assert today_parsed == now.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    tomorrow_parsed = main.parse_due_date("tomorrow")
    tomorrow = now + datetime.timedelta(days=1)
    assert tomorrow_parsed == tomorrow.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    # Test relative delta (days and weeks)
    plus_days = main.parse_due_date("+3d")
    target_days = now + datetime.timedelta(days=3)
    assert plus_days == target_days.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    plus_weeks = main.parse_due_date("+1w")
    target_weeks = now + datetime.timedelta(weeks=1)
    assert plus_weeks == target_weeks.replace(hour=23, minute=59, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

    # Test invalid formats
    with pytest.raises(ValueError, match="Invalid date format"):
        main.parse_due_date("invalid-date")

    with pytest.raises(ValueError, match="Invalid date format"):
        main.parse_due_date("2026-05-24")  # Not MM-DD-YYYY


def test_todo_crud_flow():
    runner = CliRunner()

    # 1. Add todo
    result = runner.invoke(main.app, ["todo", "add", "Test Task", "This is a test task", "--due", "05-24-2026 15:30", "--priority", "high"])
    assert result.exit_code == 0
    assert "Task added successfully" in result.stdout

    # Get the ID from the database
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, status, priority, due_date FROM todos")
        rows = cursor.fetchall()
        assert len(rows) == 1
        tid, title, desc, status, priority, due = rows[0]
        assert title == "Test Task"
        assert desc == "This is a test task"
        assert status == "todo"
        assert priority == "high"
        assert due == "2026-05-24 15:30"

    # 2. List todo
    result = runner.invoke(main.app, ["todo", "list"])
    assert result.exit_code == 0
    assert "Test Task" in result.stdout
    assert "High" in result.stdout

    # 3. Edit todo
    result = runner.invoke(main.app, ["todo", "edit", tid, "--title", "Updated Task", "--priority", "medium"])
    assert result.exit_code == 0
    assert "updated successfully" in result.stdout

    # Verify update
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, priority FROM todos WHERE id = ?", (tid,))
        row = cursor.fetchone()
        assert row[0] == "Updated Task"
        assert row[1] == "medium"

    # 4. Status update
    result = runner.invoke(main.app, ["todo", "status", tid, "in_progress"])
    assert result.exit_code == 0
    assert "updated from 'todo' to 'in_progress'" in result.stdout

    # 5. Complete todo
    result = runner.invoke(main.app, ["todo", "complete", tid])
    assert result.exit_code == 0
    assert "marked as completed" in result.stdout

    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM todos WHERE id = ?", (tid,))
        assert cursor.fetchone()[0] == "done"

    # 6. Delete todo
    # Simulate user confirmation "y"
    result = runner.invoke(main.app, ["todo", "delete", tid], input="y\n")
    assert result.exit_code == 0
    assert "deleted successfully" in result.stdout

    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM todos")
        assert cursor.fetchone()[0] == 0


def test_todo_calendar_renders():
    runner = CliRunner()

    # Insert a couple of tasks with explicit dates
    runner.invoke(main.app, ["todo", "add", "Task Wednesday", "Due Wed", "--due", "05-20-2026 10:00"])
    runner.invoke(main.app, ["todo", "add", "Task Thursday", "Due Thu", "--due", "05-21-2026 15:00"])

    # Test month view with explicit base date
    result = runner.invoke(main.app, ["todo", "calendar", "--view", "month", "--date", "05-20-2026"])
    assert result.exit_code == 0
    assert "Calendar:" in result.stdout
    assert "Task" in result.stdout
    assert "Wednesd" in result.stdout

    # Test week view with explicit base date
    result = runner.invoke(main.app, ["todo", "calendar", "--view", "week", "--date", "05-20-2026"])
    assert result.exit_code == 0
    assert "Weekly Task Calendar" in result.stdout
    assert "Task Wednesday" in result.stdout
    assert "Task Thursday" in result.stdout

    # Test day view with explicit base date
    result = runner.invoke(main.app, ["todo", "calendar", "--view", "day", "--date", "05-20-2026"])
    assert result.exit_code == 0
    assert "Agenda for" in result.stdout
    assert "Task Wednesday" in result.stdout


def test_check_reminders():
    runner = CliRunner()

    # Add a task due soon (e.g. +5 minutes)
    now = datetime.datetime.now()
    due_soon = now + datetime.timedelta(minutes=5)
    due_soon_str = due_soon.strftime("%m-%d-%Y %H:%M")

    runner.invoke(main.app, ["todo", "add", "Urgent Meeting", "Important sync", "--due", due_soon_str, "--priority", "high"])

    # Run check-reminders
    result = runner.invoke(main.app, ["todo", "check-reminders"])
    assert result.exit_code == 0
    # Since notify-send might not be installed or display variables might not be set in the sandbox environment,
    # it might fallback or succeed. But it should output either reminder notification info or nothing if no match.
    # It should mark reminder_sent = 1
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT reminder_sent FROM todos WHERE title = 'Urgent Meeting'")
        assert cursor.fetchone()[0] == 1


def test_todo_mcp_tools():
    # Test create_ostraca_todo
    res = main.create_ostraca_todo(title="MCP Task", description="via MCP", due="today", priority="high")
    assert "created successfully" in res
    assert "ID" in res

    # Test list_ostraca_todos
    todo_list_out = main.list_ostraca_todos(priority="high")
    assert "MCP Task" in todo_list_out
    assert "high" in todo_list_out

    # Get the ID
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM todos WHERE title = 'MCP Task'")
        tid = cursor.fetchone()[0]

    # Test complete_ostraca_todo
    res_comp = main.complete_ostraca_todo(tid)
    assert "marked as completed" in res_comp

    # Verify state in DB
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM todos WHERE id = ?", (tid,))
        assert cursor.fetchone()[0] == "done"
