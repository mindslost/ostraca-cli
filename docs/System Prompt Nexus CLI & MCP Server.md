# System Prompt: Nexus CLI & MCP Server

## 1. Task
Build a complete, production-ready Python package named `nexus-cli`. You must generate the `pyproject.toml` and all fully implemented Python files required to run the application according to the specifications provided in the References section.

## 2. Context
I am building a blazing-fast, terminal-based personal knowledge base that enforces the PARA method (Projects, Areas, Resources, Archives). It must act as a seamless context provider for AI agents via standard I/O piping and the Model Context Protocol (MCP). 

The system relies on a hybrid data model: 
* Notes are stored as raw Markdown files with YAML frontmatter, ensuring maximum portability. 
* A local SQLite database (`~/.para_notes.db`) with an FTS5 virtual table handles high-speed semantic text search and metadata tracking.

The tool must be frictionless for humans (launching their native `$EDITOR` like Emacs or Vim) while remaining perfectly machine-readable for AI agents.

## 3. References
Use the following architectural blueprints to write the code.

**File Structure Requirement:**
```text
nexus_project/
├── pyproject.toml
├── README.md
└── nexus_cli/
    ├── __init__.py
    ├── main.py          # Typer CLI app and FastMCP server initialization
    ├── db.py            # SQLite schema, triggers, and connection utilities
    └── frontmatter.py   # Custom regex-based YAML parser
```

**Module A: Database Schema (`nexus_cli/db.py`)**
Implement an `init_db()` function executing this exact schema:
1. Core Table (`notes`): `id` (TEXT Short ID), `title` (TEXT), `content` (TEXT), `para_category` (TEXT CHECK: Project, Area, Resource, Archive), `tags` (TEXT), `created_at`, `updated_at`.
2. Search Index (`notes_fts`): FTS5 virtual table indexing `title`, `content`, and `tags` (linked via `content='notes'` and `content_rowid='rowid'`).
3. Auto-Sync Triggers: Create SQLite triggers (`notes_ai`, `notes_ad`, `notes_au`) to auto-sync `notes_fts` on INSERT, DELETE, and UPDATE on the `notes` table.

**Module B: Frontmatter Logic (`nexus_cli/frontmatter.py`)**
Implement `extract_frontmatter(raw_content: str) -> tuple[dict, str]` using Python's `re` module. It must extract standard YAML frontmatter bounded by `---` and convert the `tags:` array into a Python list.

**Module C: CLI Commands (`nexus_cli/main.py`)**
Use `typer` for routing and `rich` for terminal UI.
* `add [title] --para [category]`: Generate Short ID -> Create temp file with YAML -> Open `$EDITOR` -> Parse YAML -> Insert to DB.
* `edit [identifier]`: Fetch by ID/Title -> Temp file -> Open `$EDITOR` -> If changed, parse YAML and Update DB.
* `move [identifier] --to [category]`: Fetch -> Use regex to replace `para:` value in YAML -> Update DB.
* `search [query] [--para category] [--raw]`: Query FTS5 (`MATCH ? ORDER BY rank`). Output `rich` table OR `--raw` XML.

**Module D: MCP Server (`nexus_cli/main.py`)**
Integrate `FastMCP`. Create command `nexus mcp-start` that runs `mcp.run(transport='stdio')`. Expose:
* `search_nexus_notes(query: str, category: str = None)`
* `get_project_context(project_name: str)`

**Module E: Packaging (`pyproject.toml`)**
Use `setuptools.build_meta`. Dependencies: `typer`, `rich`, `mcp`. Bind entry point `nexus` to `nexus_cli.main:app`.

## 4. Evaluate
Your code will be evaluated against the following strict guardrails. Do not fail these constraints:
* **Type Safety:** You must use strict Python 3.9+ type hints for all function signatures.
* **Error Handling:** You must gracefully catch `sqlite3.OperationalError` (for malformed FTS5 queries) and `FileNotFoundError`. Never leak raw stack traces to the CLI.
* **Clean Exits:** Temporary files created for `$EDITOR` must always be deleted in a `finally` block or context manager.
* **Machine Output Constraint:** When `search` is called with the `--raw` flag, you must bypass `rich` entirely and output this exact XML structure:
  `<context><note title="..." category="..." last_updated="...">[CONTENT]</note></context>`

## 5. Iterate
For your first response, output the complete, production-ready code for `pyproject.toml`, `db.py`, and `frontmatter.py`. 

Pause and ask for my review. Once approved, I will prompt you to generate `main.py`.