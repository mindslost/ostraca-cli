# Ostraca CLI Documentation

Ostraca CLI is a terminal-based personal knowledge base (PKB) that enforces the **PARA** organization method. It is designed for frictionless human capture via terminal editors and high-performance context retrieval for AI agents.

## 1. PARA Methodology

The PARA method, popularized by Tiago Forte, categorizes information into four distinct buckets:

- **Projects**: Series of tasks linked to a goal, with a deadline (e.g., "Complete Documentation").
- **Areas**: Sphere of activity with a standard to be maintained over time (e.g., "Health", "Finances").
- **Resources**: Topic or interest that may be useful in the future (e.g., "Python", "Baking").
- **Archives**: Inactive items from the other three categories.

Ostraca CLI enforces this categorization via a `CHECK` constraint in its database, ensuring that every note belongs to exactly one of these four categories.

## 2. Architecture

### Storage & Database Schema

Ostraca CLI uses a single-file SQLite database located at `~/.para_notes.db`. This database contains two primary tables:

1. **`notes`**: Stores all Markdown notes and their PARA categories.
   - `id` (TEXT PRIMARY KEY): Unique 8-character ID (`shortuuid`).
   - `title` (TEXT NOT NULL): The note's title.
   - `content` (TEXT NOT NULL): Markdown body with YAML frontmatter.
   - `para_category` (TEXT NOT NULL): Enforced by a check constraint (`CHECK(para_category IN ('Project', 'Area', 'Resource', 'Archive'))`).
   - `tags` (TEXT): Comma-separated list of tags.
   - `created_at` / `updated_at` (DATETIME): Timestamp fields.

2. **`todos`**: Stores task list items.
   - `id` (TEXT PRIMARY KEY): Unique 8-character ID (`shortuuid`).
   - `title` (TEXT NOT NULL): The task title.
   - `description` (TEXT): Optional task description.
   - `status` (TEXT NOT NULL): Current status, defaulting to `todo` (`CHECK(status IN ('todo', 'in_progress', 'done'))`).
   - `priority` (TEXT NOT NULL): Task priority, defaulting to `medium` (`CHECK(priority IN ('low', 'medium', 'high'))`).
   - `due_date` (TEXT): Formatted as `YYYY-MM-DD HH:MM`.
   - `reminder_sent` (INTEGER): Flag (`0` or `1`) indicating whether a system notification has been dispatched.
   - `created_at` / `updated_at` (DATETIME): Timestamp fields.

### Search

The application leverages SQLite **FTS5** (Full-Text Search) for high-performance searching. Native database triggers (`notes_ai`, `notes_ad`, `notes_au`) automatically keep a virtual FTS table (`notes_fts`) in sync with the primary `notes` table whenever notes are inserted, deleted, or updated.

### Note Identifiers

Each note is assigned a **Short ID** (8 characters) using the `shortuuid` library. These IDs are unique within the database and provide a stable way to reference notes even if their titles change.

### Metadata & Frontmatter

Ostraca stores metadata (title, category, tags) directly inside the Markdown content using **YAML frontmatter**. This makes the files portable and human-readable.

```markdown
---
title: "Project Alpha"
para: Project
tags: ["internal", "v1"]
---
# Project Alpha
Content goes here...
```

The CLI synchronizes the database fields with this frontmatter whenever a note is edited.

## 3. CLI Command Reference

### Note Commands

#### `ost add [TITLE]`

Creates a new note.

- **Arguments**: `TITLE` (The title of the note).
- **Options**: `--para [Project|Area|Resource|Archive]` (Required category).

#### `ost edit [ID|TITLE]`

Opens an existing note in your preferred editor.

- **Arguments**: `ID` or `TITLE` (Short ID or exact title).
- **Note**: You can update the title, category, and tags by modifying the frontmatter directly in the editor.

#### `ost move [ID|TITLE]`

Quickly re-categorize a note.

- **Arguments**: `ID` or `TITLE`.
- **Options**: `--to [Project|Area|Resource|Archive]` (The target category).

#### `ost search [QUERY]`

Perform a full-text search.

- **Arguments**: `QUERY` (SQLite FTS5 syntax).
- **Options**:
  - `--para [Category]`: Filter results by category.
  - `--raw`: Output raw XML for machine/AI-readable context.

#### `ost list`

View your PARA tree.

- **Options**:
  - `--para [Category]`: Filter list by category.
  - `--tags [TAG1,TAG2]`: Filter list by comma-separated tags.

#### `ost open [ID|TITLE]`

Open a note in read-only mode for viewing. Changes made in the editor session will **not** be saved.

#### `ost export [ID|TITLE]`

Export a note's content to a Markdown file.

- **Arguments**: `ID` or `TITLE` (Short ID or exact title).
- **Options**:
  - `--output / -o [PATH]`: Destination file path or directory (defaults to home folder).
  - `--force / -f`: Overwrite the destination file if it already exists.

#### `ost delete [ID|TITLE]`

Permanently remove a note. Requires user confirmation.

#### `ost backup`

Create a consistent SQLite backup of your database.

- **Options**:
  - `--path / -p [PATH]`: Custom destination path.
  - `--prune`: Prune old backups, keeping only the 20 most recent backups.

#### `ost restore [PATH]`

Restore your database from a backup file.

- **Warning**: This will overwrite your current database.

#### `ost mcp-start`

Launch the FastMCP server. This allows AI agents to interact with your notes and todos via standard input/output (stdio):

- `search_ostraca_notes(query, category)`: Full-text search across all notes.
- `get_ostraca_note(identifier)`: Fetch content and metadata for any note.
- `create_ostraca_note(title, para, content, tags)`: Create a new note.
- `edit_ostraca_note(identifier, content)`: Modify an existing note.
- `patch_ostraca_note(identifier, old_string, new_string)`: Targeted text replacement (highly efficient).
- `append_to_ostraca_note(identifier, content)`: Append text to the end of a note.
- `get_project_context(project_name)`: Get specific details for a project note.
- `list_ostraca_todos(status, priority, all_items)`: Retrieve list of todos matching optional status/priority filters.
- `create_ostraca_todo(title, description, due, priority)`: Create a new todo task.
- `complete_ostraca_todo(identifier)`: Complete a todo task by ID or title.
- `update_ostraca_todo(identifier, title, description, due, priority, status)`: Update attributes of an existing todo task.
- `delete_ostraca_todo(identifier)`: Permanently delete a todo task.

### Todo Commands (`ost todo`)

The `todo` subcommand group allows you to manage tasks and schedule deadlines.

#### `ost todo add [TITLE] [DESCRIPTION]`

Add a new task to your todo list.

- **Arguments**:
  - `TITLE`: Title of the task.
  - `DESCRIPTION` (Optional): Brief details/description.
- **Options**:
  - `--due / -d [DATE]`: Task due date. Supports explicit formats (`MM-DD-YYYY HH:MM`, `MM-DD-YYYY`) and relative formats (`today`, `tomorrow`, `+Nd` e.g., `+3d`, `+Nw` e.g., `+1w`).
  - `--priority / -p [low|medium|high]`: Task priority level (defaults to `medium`).

#### `ost todo edit [ID|TITLE]`

Edit an existing todo item's attributes.

- **Arguments**: `ID` or `TITLE` (Short ID or exact title).
- **Options**:
  - `--title / -t [TEXT]`: New task title.
  - `--desc / -d [TEXT]`: New task description.
  - `--due [DATE]`: New due date (pass empty string `""` to clear the due date).
  - `--priority / -p [low|medium|high]`: New priority level.

#### `ost todo complete [ID|TITLE]`

Mark a task as completed.

- **Arguments**: `ID` or `TITLE`.

#### `ost todo status [ID|TITLE] [todo|in_progress|done]`

Manually update a task's status.

- **Arguments**:
  - `ID` or `TITLE`.
  - `STATUS`: Target status (`todo`, `in_progress`, or `done`).

#### `ost todo delete [ID|TITLE]`

Permanently remove a task from the database. Requires user confirmation.

- **Arguments**: `ID` or `TITLE`.

#### `ost todo list`

List todo tasks in a styled table.

- **Options**:
  - `--status / -s [todo|in_progress|done]`: Filter by task status.
  - `--priority / -p [low|medium|high]`: Filter by priority.
  - `--all / -a`: Show all tasks, including completed ones (by default, completed tasks are hidden).

#### `ost todo calendar`

Display a terminal calendar highlighting scheduled tasks.

- **Options**:
  - `--view / -v [day|week|month]`: View scale (defaults to `month`).
  - `--date / -d [MM-DD-YYYY]`: Base date to focus the calendar on (defaults to today).

#### `ost todo check-reminders`

Evaluate upcoming tasks and trigger system desktop notifications.

- **Options**: `--buffer / -b [MINUTES]`: Check for tasks due within the specified buffer minutes (defaults to `15`).

#### `ost todo setup-reminders`

Set up automatic system timers to periodically run `ost todo check-reminders` in the background.
- On **Linux**, generates and registers a user-level `systemd` service and timer file running every 5 minutes.
- On **macOS**, generates and registers a user-level `launchd` plist file running every 5 minutes.

## 4. Configuration & Reminders

### Editor Selection

Ostraca CLI respects the `$EDITOR` environment variable. If not set, it defaults to `vim`.

```bash
# Set your editor in your shell configuration (e.g. .bashrc or .zshrc)
export EDITOR="code --wait"
```

### Database Location

The database is always stored at `~/.para_notes.db`.

### Desktop Notifications & Timers

The `ost todo check-reminders` command fires platform-native notifications for tasks approaching their due dates:
- **macOS**: Utilizes AppleScript (`osascript`) to send native notifications.
- **Linux**: Utilizes `notify-send` (libnotify).

Automatic scheduling of these notifications is supported via:
- **systemd** (Linux): Writes unit files under `~/.config/systemd/user/` (`ostraca-reminders.service` and `ostraca-reminders.timer`).
- **launchd** (macOS): Writes a plist file under `~/Library/LaunchAgents/` (`com.ostraca.reminders.plist`).

## 5. Metadata Parser

The metadata is parsed using a regex-based parser in `ostraca_cli/frontmatter.py`. This ensures that even if you use complex YAML features, the core PARA metadata remains extractable and synchronized with the database.
