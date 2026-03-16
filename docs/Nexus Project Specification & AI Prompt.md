# Nexus: Project Specification & AI Prompt

**Objective:** To build a blazing-fast, terminal-based personal knowledge base that enforces the PARA method (Projects, Areas, Resources, Archives) and acts as a seamless context provider for AI agents via standard I/O piping and the Model Context Protocol (MCP).

---

## Part 1: System Design Document

### 1. Core Philosophy
* **Portable & Self-Contained:** Notes are stored as raw Markdown with YAML frontmatter. The document itself is the source of truth, ensuring portability to any other Markdown-based system.
* **Frictionless Capture:** Human-first data entry using the user's native `$EDITOR` (e.g., Emacs, Vim).
* **Machine-Readable:** Zero-noise output modes specifically formatted for LLM context windows.
* **Decoupled:** Serves context to whatever agent or pipeline the user prefers, whether through shell piping or autonomous MCP tool calls.

### 2. System Architecture
Nexus operates as a single Python package exposing two distinct interfaces that interact with a localized SQLite database (`~/.para_notes.db`).
* **The Typer CLI (`nexus`):** The human interface for reading, writing, and organizing Markdown notes, as well as the piping interface (`--raw`) for shell-based AI workflows.
* **The FastMCP Server (`nexus mcp-start`):** A persistent standard I/O server that exposes the database directly to modern agentic tools (like Claude Code) as a set of autonomous tools.

### 3. Data Model & State Management
The system relies on a hybrid approach: Markdown files contain the explicit metadata via YAML, while SQLite handles the high-speed indexing and retrieval.

**YAML Frontmatter (The Source of Truth)**
Every note contains a standardized YAML block at the top:
```yaml
---
title: "Microservice Auth Spec"
para: Project
tags: [python, security, api]
---
```

**SQLite Core Table (`notes`)**
* `id` (TEXT): Short ID (8-character) primary key.
* `title` (TEXT): Parsed from frontmatter.
* `content` (TEXT): The full raw Markdown (including the frontmatter block).
* `para_category` (TEXT): Parsed from frontmatter, enforced via `CHECK` constraint (`Project`, `Area`, `Resource`, `Archive`).
* `tags` (TEXT): Parsed from frontmatter array into a comma-separated string for DB storage.
* `created_at` / `updated_at` (DATETIME): Auto-managed timestamps.

**Search Index & Auto-Sync Triggers**
* `notes_fts`: An FTS5 virtual table indexing `title`, `content`, and `tags`. 
* Three SQLite triggers (`notes_ai`, `notes_ad`, `notes_au`) intercept all database modifications and automatically update the `notes_fts` index. The Python layer never manually updates this index.

### 4. Core Workflows
* **`nexus add [Title] --para [P|A|R|A]`**: Generates a Short ID and a temp Markdown file with YAML frontmatter. Launches `$EDITOR`. On save, parses YAML and `INSERT`s into SQLite.
* **`nexus edit [ID|Title]`**: Fetches document from SQLite, opens `$EDITOR`. On save, if modified, validates YAML frontmatter and `UPDATE`s SQLite.
* **`nexus move [ID|Title] --to [P|A|R|A]`**: Programmatically parses and reconstructs the YAML frontmatter block to update the `para:` category, then `UPDATE`s SQLite. This ensures the body of the note is never accidentally modified.
* **`nexus delete [ID|Title]`**: Removes a note from the database after a user confirmation.
* **`nexus search "query" [--para Category] [--raw]`**: 
    * *Human Mode:* Returns a formatted terminal table highlighting keyword matches using SQLite's `snippet()` function.
    * *Machine Mode (`--raw`):* Bypasses terminal formatting, returning clean XML (`<context><note>...</note></context>`) for LLM prompt injection.

---

## Part 2: AI Implementation Prompt

**Role:** You are an expert Python developer specializing in CLI applications, SQLite database optimization (specifically FTS5), and the Anthropic Model Context Protocol (MCP). 

**Task:** Build a complete Python package named `nexus-cli` based on the system design document above. Generate the necessary file structure, the `pyproject.toml`, and the fully implemented Python code.

### 1. Code Quality & Guardrails
* **Type Hinting:** Use strict Python 3.9+ type hints for all function signatures and variables. This is critical for `FastMCP` and `Typer` to function correctly.
* **Error Handling:** Gracefully catch `sqlite3.OperationalError` (especially for malformed FTS5 queries) and `FileNotFoundError`. Never leak raw stack traces to the user in the CLI. Use `rich` to print user-friendly red error messages.
* **Clean Exits:** Ensure temp files created for `$EDITOR` are always deleted in a `finally` block or context manager, even if the editor crashes.

### 2. File Structure
Generate the code to fit this structure:
```text
nexus_project/
├── pyproject.toml
├── README.md
└── nexus_cli/
    ├── __init__.py
    ├── main.py          # Typer CLI app and MCP server initialization
    ├── db.py            # SQLite schema, triggers, and connection utilities
    └── frontmatter.py   # Custom regex-based YAML parser
```

### 3. Database Schema (`nexus_cli/db.py`)
Implement an `init_db()` function executing the following:
1. **Core Table (`notes`):** `id` (TEXT Short ID), `title` (TEXT), `content` (TEXT), `para_category` (TEXT CHECK), `tags` (TEXT), `created_at`, `updated_at`.
2. **Search Index (`notes_fts`):** FTS5 virtual table indexing `title`, `content`, and `tags` (linked via `content='notes'` and `content_rowid='rowid'`).
3. **Triggers:** Create `notes_ai`, `notes_ad`, `notes_au` to auto-sync `notes_fts` on INSERT, DELETE, and UPDATE.

### 4. Frontmatter Logic (`nexus_cli/frontmatter.py`)
Implement `extract_frontmatter(raw_content: str) -> tuple[dict, str]` using Python's `re` module to parse standard YAML frontmatter bounded by `---` and convert the `tags:` array into a Python list. Ensure edge cases (like empty tags or missing frontmatter) are handled without crashing.

### 5. CLI Commands (`nexus_cli/main.py`)
Use `typer` for routing and `rich` for terminal output. Implement:
* `add`: Generate Short ID -> Temp file with YAML -> Open `$EDITOR` -> Parse & Validate -> Insert to DB.
* `edit`: Fetch -> Temp file -> Open `$EDITOR` -> Parse & Validate -> Update DB.
* `move`: Parse and reconstruct frontmatter block to update `para:` field -> Update DB.
* `delete`: Prompt for confirmation -> Delete from DB.
* `search`: Query FTS5 (`MATCH ? ORDER BY rank`). 
  * If not raw, print a `rich` Table using SQLite's `snippet()` function to show context matches.
  * If `--raw`, strictly output this exact format:
    `<context>`
    `  <note title="{title}" category="{para}" last_updated="{date}">`
    `    {content}`
    `  </note>`
    `</context>`

### 6. MCP Server (`nexus_cli/main.py`)
Integrate `FastMCP`. Create `nexus mcp-start` commanding `mcp.run(transport='stdio')`. Expose:
* `search_nexus_notes(query: str, category: str = None)`
* `get_project_context(project_name: str)`

### 7. Packaging (`pyproject.toml`)
Define a `pyproject.toml` (build-backend = "setuptools.build_meta").
* Name: `nexus-cli`
* Dependencies: `typer`, `rich`, `mcp`
* Entry point: Bind `nexus` to `nexus_cli.main:app`.

**Execution:** Output the complete, production-ready code for all files specified in the File Structure section.