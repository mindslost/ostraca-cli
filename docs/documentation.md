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

### Storage
Ostraca CLI uses a single-file SQLite database located at `~/.para_notes.db`. This ensures your knowledge base is portable and easy to back up.

### Search
The application leverages SQLite **FTS5** (Full-Text Search) for high-performance searching. Triggers automatically keep a virtual FTS table (`notes_fts`) in sync with the primary `notes` table whenever content is added, updated, or deleted.

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

### `ost add [TITLE]`
Creates a new note.
- **Arguments**: `TITLE` (The title of the note).
- **Options**: `--para [Project|Area|Resource|Archive]` (Required category).

### `ost edit [ID|TITLE]`
Opens an existing note in your preferred editor.
- **Arguments**: `ID` or `TITLE` (Short ID or exact title).
- **Note**: You can update the title, category, and tags by modifying the frontmatter directly in the editor.

### `ost move [ID|TITLE]`
Quickly re-categorize a note.
- **Arguments**: `ID` or `TITLE`.
- **Options**: `--to [Project|Area|Resource|Archive]` (The target category).

### `ost search [QUERY]`
Perform a full-text search.
- **Arguments**: `QUERY` (SQLite FTS5 syntax).
- **Options**: 
  - `--para [Category]`: Filter results by category.
  - `--raw`: Output raw XML for machine/AI-readable context.

### `ost list`
View your PARA tree.
- **Options**: 
  - `--para [Category]`: Filter list by category.
  - `--tags [TAG1,TAG2]`: Filter list by comma-separated tags.
  - `--interactive / -i`: Launch an interactive TUI to manage notes.

### `ost open [ID|TITLE]`
Open a note in read-only mode for viewing. Changes made in the editor session will **not** be saved.

### `ost delete [ID|TITLE]`
Permanently remove a note. Requires user confirmation.

### `ost backup`
Create a consistent SQLite backup of your database.
- **Options**: `--path / -p [PATH]` (Custom destination path).

### `ost restore [PATH]`
Restore your database from a backup file.
- **Warning**: This will overwrite your current notes.

### `ost mcp-start`
Launch the FastMCP server. This allows AI agents to interact with your notes via tools:
- `search_ostraca_notes(query, category)`: Full-text search across all notes.
- `get_ostraca_note(identifier)`: Fetch content and metadata for any note.
- `create_ostraca_note(title, para, content, tags)`: Create a new note.
- `edit_ostraca_note(identifier, content)`: Modify an existing note.
- `get_project_context(project_name)`: Get specific details for a project note.

## 4. Configuration

### Editor Selection
Ostraca CLI respects the `$EDITOR` environment variable. If not set, it defaults to `vim`.

```bash
# Set your editor in .bashrc or .zshrc
export EDITOR="code --wait"
```

### Database Location
The database is always stored at `~/.para_notes.db`. 

## 5. Metadata Parser
The metadata is parsed using a regex-based parser in `ostraca_cli/frontmatter.py`. This ensures that even if you use complex YAML features, the core PARA metadata remains extractable and synchronized with the database.
