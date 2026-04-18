# Ostraca CLI: Project Context & Instructions

This document provides essential context, architectural overviews, and operational guidelines for the **Ostraca CLI** project.

## Project Overview

**Ostraca CLI** is a terminal-based personal knowledge base (PKB) that enforces the **PARA** (Projects, Areas, Resources, Archives) organization method. It is designed for frictionless human capture via terminal editors and high-performance context retrieval for AI agents.

### Core Technologies

- **Language**: Python 3.9+
- **CLI Framework**: [Typer](https://typer.tiangolo.com/) (based on Click)
- **Terminal UI**: [Rich](https://rich.readthedocs.io/)
- **Database**: SQLite with **FTS5** (Full-Text Search)
- **AI Protocol**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) via `FastMCP`
- **ID Generation**: `shortuuid` (8-character unique IDs)

### Architecture

- **Storage**: Single-file SQLite database located at `~/.para_notes.db`.
- **Search**: Real-time synchronization between the `notes` table and an `notes_fts` virtual table using SQLite native triggers (`notes_ai`, `notes_ad`, `notes_au`).
- **Metadata**: Notes are stored as raw Markdown with YAML frontmatter. Metadata (title, category, tags) is parsed using a custom regex-based parser to maintain maximum portability.

---

## Project Structure

- `ostraca_cli/main.py`: Entry point for the Typer CLI and FastMCP server. Contains command logic and tool definitions.
- `ostraca_cli/db.py`: Database schema definition, FTS5 trigger setup, and connection utilities.
- `ostraca_cli/frontmatter.py`: Logic for extracting and manipulating YAML frontmatter from Markdown content.
- `docs/`: Comprehensive design specifications, methodology guides, and system prompts.

---

## Building and Running

### Installation

Install the project in editable mode with all dependencies:

```bash
pip install -e .
```

### Key CLI Commands

- `ost add "Title" --para [Category]`: Create a new note.
- `ost search "query"`: Perform full-text search with context snippets.
- `ost list`: View the PARA tree structure.
- `ost edit [ID|Title]`: Edit an existing note in your `$EDITOR`.
- `ost move [ID|Title] --to [Category]`: Re-categorize a note.
- `ost delete [ID|Title]`: Remove a note with a confirmation prompt.
- `ost backup`: Create a consistent SQLite backup of your database.
- `ost restore [PATH]`: Restore your database from a backup file.
- `ost mcp-start`: Launch the MCP server for AI integration.

### Testing

Currently, the project uses manual verification and simulation scripts (e.g., `test_collision.py`).
**TODO**: Implement a formal test suite using `pytest`.

---

## Development Conventions

### Note Identifiers

- Use **Short IDs** (8-character strings from `shortuuid`) for primary keys.
- Commands should support both the Short ID and the full Title as identifiers for user convenience.

### Database Integrity

- The `id` column has a `PRIMARY KEY` constraint.
- The `para_category` column has a `CHECK` constraint to enforce "Project", "Area", "Resource", or "Archive".
- Always use the `get_db()` context manager to handle connections and ensure they are closed correctly.

### Frontmatter Parsing

- Metadata is the source of truth for `title`, `para_category`, and `tags`.
- When editing or moving a note, the database fields must be synchronized with the parsed frontmatter.
- Use `extract_frontmatter` from `ostraca_cli/frontmatter.py` to handle edge cases like quoted titles or complex tag arrays.

### MCP Tools

When adding new features, ensure they are exposed as MCP tools in `ostraca_cli/main.py` using the `@mcp.tool()` decorator if they provide useful context for AI agents.

---

## User Preferences

- **Editor**: Respect the `$EDITOR` environment variable, defaulting to `vim`.
- **Output**: Prefer `rich` for human-readable terminal output and XML (via `--raw`) for machine/AI-readable output.
