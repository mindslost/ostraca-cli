# Nexus: The PARA-Method AI Notebook

**Nexus** is a blazing-fast, terminal-based personal knowledge base designed to bridge the gap between human thought organization and machine context retrieval.

It enforces the **PARA method** (Projects, Areas, Resources, Archives) to keep your context windows clean, and acts as a seamless data provider for AI agents via standard Unix piping and the Model Context Protocol (MCP).

## Core Concepts

- **Markdown + YAML:** Notes are stored as pure Markdown files with YAML frontmatter. The document itself is the source of truth, ensuring 100% portability.
- **Frictionless Capture:** Nexus drops you directly into your native terminal editor (e.g., Emacs, Vim) so you never have to leave your keyboard to capture a thought.
- **SQLite FTS5 Engine:** Behind the scenes, Nexus syncs your notes to a local SQLite database (`~/.para_notes.db`) equipped with Full-Text Search (FTS5) for sub-millisecond retrieval.
- **Dual-Mode Output:** Built for both humans and machines. It outputs rich, colorized tables for human reading, and clean, XML-wrapped tags for LLM prompt injection.

------

## Installation

### Prerequisites

- Python 3.9+
- `pipx` (Recommended for global installation)

### Production Install (Global)

To use the `nexus` command anywhere on your system without managing virtual environments:

Bash

```shell
# From the project root directory
pipx install .
```

### Development Install

If you are modifying the source code and want to test changes live:

Bash

```shell
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

------

## Usage Guide: Human Mode

Manage your brain from the terminal using standard CLI commands.

### 1. Adding Notes

Create a new note. Nexus will generate a temporary file with YAML frontmatter, open your `$EDITOR`, and save the parsed result to the database when you exit.

Bash

```shell
nexus add "Microservice Auth Spec" --para Project
```

### 2. Editing Notes

Edit an existing note by its exact title or Short ID. Nexus automatically detects if you changed the tags or category in the YAML frontmatter and syncs the database.

Bash

```shell
nexus edit "Microservice Auth Spec"
```

### 3. Moving Notes (The PARA Lifecycle)

When a Project is finished, move it to your Archives so it stops polluting your active AI context windows. This programmatically rewrites the YAML frontmatter and updates the database.

Bash

```shell
nexus move "Microservice Auth Spec" --to Archive
```

### 4. Searching

Leverage SQLite FTS5 for lightning-fast keyword searches. Outputs a colorized table with highlighted match snippets.

Bash

```shell
nexus search "jwt tokens OR oauth" --para Resource
```

------

## Usage Guide: AI Integration (Machine Mode)

Nexus is designed to feed context to Large Language Models without friction.

### Method 1: Unix Piping (Standard I/O)

Use the `--raw` flag to bypass terminal formatting and output clean XML-wrapped markdown (`<context><note>...</note></context>`). Pipe this directly into AI CLI tools like `llm`.

**Example: Reviewing an architectural plan**

Bash

```shell
nexus search "database migration" --raw | llm "Review this architectural plan and write the SQL script."
```

### Method 2: Model Context Protocol (MCP)

For autonomous agents (like Claude Code), run Nexus as a background MCP server. This allows the AI to autonomously search your notes and fetch project context without you having to pipe anything.

**1. Start the Server:**

Bash

```shell
nexus mcp-start
```

**2. Configure your AI Client (Example for Claude Code):**

Bash

```shell
claude mcp add nexus -- nexus mcp-start
```

*Once configured, simply ask Claude: "Review my notes on the auth microservice and write the python validation logic."*

------

## Architecture & Data Model

For developers extending Nexus, here is how the data flows:

1. **Storage Location:** `~/.para_notes.db`
2. **Schema:**
   - `notes` table: Stores `id` (Short ID), `title`, `content` (Raw Markdown + YAML), `para_category`, `tags`, and timestamps.   - `notes_fts` table: An FTS5 virtual table for semantic search.
3. **Auto-Sync:** You do not need to manage the search index in Python. The database contains three native SQLite triggers (`notes_ai`, `notes_ad`, `notes_au`) that automatically sync the FTS5 virtual table whenever the main `notes` table is modified.

------

Now that you have the complete Prompt Framework (from our previous step) and this official README Guide, you have everything you need to start generating the actual Python code with your LLM.

Would you like me to help you brainstorm some specific tags or project categories to use once you have the CLI up and running?