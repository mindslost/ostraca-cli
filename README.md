# Ostraca

**Ostraca: Frictionless markdown for humans. High-speed context for AI.**

In the ancient world, an *ostracon* was a pottery shard used as an everyday scratchpad—a frictionless way to jot down quick notes, receipts, and thoughts. 

**Ostraca CLI** brings that same instant capture to your terminal. It’s a blazing-fast personal knowledge base built with Python and SQLite that natively enforces the PARA method. Whether you are writing Markdown in your favorite editor or feeding structured context to an AI agent via the built-in MCP server, Ostraca keeps your knowledge organized, searchable, and instantly accessible.

---

## 🚀 Key Features

* **PARA Method Enforcement**: Automatically organizes your workflow into four distinct categories: *Projects*, *Areas*, *Resources*, and *Archives*.
* **Frictionless Capture**: Use your native `$EDITOR` (whether that's Doom Emacs, Neovim, or VS Code) to write notes in standard Markdown.
* **Lightning-Fast Retrieval**: Notes are indexed in real-time using SQLite's FTS5 virtual table. Get instant full-text search across titles, content, and tags, complete with human-readable context snippets.
* **Self-Contained Metadata**: Uses YAML frontmatter stored directly in the Markdown file, ensuring your notes remain portable, parseable, and independent. 
* **AI-Ready Architecture**:
    * **Built-in MCP Server**: Native support for the Model Context Protocol, allowing AI agents like Claude Code to autonomously search, read, and retrieve your notes.
    * **Machine-Readable Output**: The `search` command includes a `--raw` flag that outputs clean XML specifically formatted to maximize LLM context windows.
* **Visual Organization**: View your entire knowledge base in a clean, hierarchical tree format right in the terminal.

---

## 🛠️ Installation

### From Source

1. Clone the repository:

```bash
git clone https://github.com/your-username/ostraca.git
cd ostraca
```

2. Install the package in editable mode:

```bash
pip install -e .
```

3. Ensure your `$EDITOR` environment variable is set. Ostraca respects your terminal environment, whether you prefer a terminal editor or a GUI:

```bash
export EDITOR="emacsclient -c" # or "code --wait", "nvim", "vim", etc.
```

### Shell Autocompletion

Ostraca supports shell autocompletion for note IDs and Titles. To enable it, run the command for your shell:

* **Zsh**: `ost --install-completion zsh`
* **Bash**: `ost --install-completion bash`
* **Fish**: `ost --install-completion fish`

*Note: You may need to restart your terminal or source your shell's configuration file (e.g., `source ~/.zshrc`) for changes to take effect.*

---

## 📖 Quick Start

### 1. Add a New Note

```bash
ost add "New Feature Specs" --para Project
```
This will open your editor with a pre-populated YAML frontmatter block, ready for you to start typing.

### 2. List Your Notes

```bash
ost list
ost list --para Project
ost list --tags python,security
```
Displays a tree structure of all your notes organized by PARA category.

### 2.1 Interactive Selection TUI

To interactively browse, open (`o`), edit (`e`), move (`m`), or delete (`d`) notes using arrow keys or Vim-style movement (`j/k`):

```bash
ost list --interactive
# or
ost list -i
```

### 3. Search Your Knowledge Base

```bash
ost search "database optimization"
```
Uses FTS5 for a high-speed search across all note titles and content, displaying highlighted context snippets.

### 4. Edit a Note

```bash
ost edit "New Feature Specs"
```

### 5. Move a Note (Re-categorize)

```bash
ost move "Old Project" --to Archive
```

### 6. Delete a Note

```bash
ost delete "Old Project"
```
Removes a note by ID or Title with a confirmation prompt.

### 7. Backup and Restore

Create a consistent snapshot of your entire knowledge base:

```bash
ost backup
# or specify a path
ost backup --path ~/backups/para.db
```

To restore from a backup (WARNING: this overwrites your current database):

```bash
ost restore ~/backups/para.db
```

---

## 🤖 MCP Integration

Ostraca includes a built-in MCP server, enabling AI agents to interact seamlessly with your personal knowledge base.

### Starting the MCP Server

```bash
ost mcp-start
```

### Available Tools for AI Agents

* `search_ostraca_notes(query: str, category: str = None)`: Search for notes using full-text search.
* `get_ostraca_note(identifier: str)`: Retrieve the full content and metadata for any note (ID or Title).
* `create_ostraca_note(title: str, para: str, content: str, tags: list = None)`: Create a new note with optional tags.
* `edit_ostraca_note(identifier: str, content: str)`: Update an existing note's content and metadata.
* `get_project_context(project_name: str)`: Retrieve the full content for a specific project note.

### Claude Desktop Configuration

To use Ostraca with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ostraca": {
      "command": "ost",
      "args": ["mcp-start"]
    }
  }
}
```

---

## 📁 Project Structure

```text
ostraca/
├── ostraca_cli/
│   ├── main.py          # CLI commands (Typer) and MCP server (FastMCP)
│   ├── db.py            # SQLite schema, FTS5 triggers, and DB utilities
│   └── frontmatter.py   # Regex-based YAML frontmatter parser
├── docs/                # Detailed design specifications and PARA methodology
├── pyproject.toml       # Package metadata and dependencies
└── README.md            # You are here
```

* **Database Location**: `~/.para_notes.db` (SQLite)

---

## ⚖️ License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
