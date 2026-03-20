<img width="1060" height="808" alt="image" src="https://github.com/user-attachments/assets/58515586-4e1a-4db5-9cca-56c315635b2f" />

# Nexus

**Nexus CLI**: A blazing-fast, terminal-based personal knowledge base built with Python and SQLite. It natively enforces the **PARA** (Projects, Areas, Resources, Archives) organization method, features lightning-fast full-text search via FTS5, and manages your notes seamlessly through Markdown and your favorite terminal editor.

Nexus is designed to be both a frictionless human interface for knowledge capture and a high-performance context provider for AI agents via the **Model Context Protocol (MCP)**.

---

## 🚀 Key Features

- **PARA Method Enforcement**: Organizes notes into four distinct categories: *Projects*, *Areas*, *Resources*, and *Archives*.
- **Frictionless Capture**: Use your native `$EDITOR` (Vim, Emacs, Nano, etc.) to write notes in standard Markdown.
- **SQLite + FTS5**: Notes are indexed in real-time using SQLite's FTS5 virtual table for instant full-text search across titles, content, and tags. Search results include context snippets for human-readable output.
- **YAML Frontmatter**: Metadata is stored directly in the Markdown file, ensuring your notes remain portable and self-contained. Supports complex titles with quotes and colons.
- **AI-Ready**:
  - **MCP Server**: Built-in support for the Model Context Protocol, allowing AI agents (like Claude Code) to autonomously search and retrieve your notes.
  - **Machine-Readable Output**: The `search` command includes a `--raw` flag that outputs clean XML specifically formatted for LLM context windows.
- **Visual Organization**: View your entire knowledge base in a clean, hierarchical tree format using `rich`.

---

## 🛠️ Installation

### From Source

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/nexus.git
   cd nexus
   ```

2. Install the package in editable mode:

   ```bash
   pip install -e .
   ```

3. Ensure your `$EDITOR` environment variable is set (defaults to `vim`):

   ```bash
   export EDITOR=nvim  # or your preferred editor
   ```

### Shell Autocompletion

Nexus supports shell autocompletion for note IDs and Titles. To enable it, run the command for your shell:

- **Zsh**: `nexus --install-completion zsh`
- **Bash**: `nexus --install-completion bash`
- **Fish**: `nexus --install-completion fish`

*Note: You may need to restart your terminal or source your shell's configuration file (e.g., `source ~/.zshrc`) for changes to take effect.*

---

## 📖 Quick Start

### 1. Add a New Note

```bash
nexus add "New Feature Specs" --para Project
```

This will open your editor with a pre-populated YAML frontmatter block.

### 2. List Your Notes

```bash
nexus list
nexus list --para Project
nexus list --tags python,security
```

Displays a tree structure of all your notes organized by PARA category.

### 2.1 Interactive Selection TUI

To interactively browse, open (`o`), edit (`e`), move (`m`), or delete (`d`) notes using arrow keys or Vim-style movement (`j/k`):

```bash
nexus list --interactive
# or
nexus list -i
```


### 3. Search Your Knowledge Base

```bash
nexus search "database optimization"
```

Uses FTS5 for a high-speed search across all note titles and content, displaying highlighted context snippets.

### 4. Edit a Note

```bash
nexus edit "New Feature Specs"
```

### 5. Move a Note (Re-categorize)

```bash
nexus move "Old Project" --to Archive
```

### 6. Delete a Note

```bash
nexus delete "Old Project"
```

Removes a note by ID or Title with a confirmation prompt.

---

## 🤖 MCP Integration

Nexus includes a built-in MCP server, enabling AI agents to interact with your personal knowledge base.

### Starting the MCP Server

```bash
nexus mcp-start
```

### Available Tools for AI Agents

- `search_nexus_notes(query: str, category: str = None)`: Search for notes using full-text search.
- `get_project_context(project_name: str)`: Retrieve the full content and metadata for a specific project note.

To use Nexus with **Claude Desktop**, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nexus": {
      "command": "nexus",
      "args": ["mcp-start"]
    }
  }
}
```

---

## 📁 Project Structure

```text
nexus/
├── nexus_cli/
│   ├── main.py          # CLI commands (Typer) and MCP server (FastMCP)
│   ├── db.py            # SQLite schema, FTS5 triggers, and DB utilities
│   └── frontmatter.py   # Regex-based YAML frontmatter parser
├── docs/                # Detailed design specifications and PARA methodology
├── pyproject.toml       # Package metadata and dependencies
└── README.md            # You are here
```

- **Database Location**: `~/.para_notes.db` (SQLite)

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
