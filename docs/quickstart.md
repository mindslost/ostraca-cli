# Ostraca CLI Quickstart Guide

Get up and running with Ostraca CLI, your terminal-based personal knowledge base enforcing the PARA method.

## 1. Installation

Install Ostraca CLI in editable mode from the project root:

```bash
pip install -e .
```

Ensure your `$EDITOR` environment variable is set (defaults to `vim`):

```bash
export EDITOR=nano  # or vim, code, etc.
```

## 2. Create Your First Note

Ostraca uses the PARA method (Projects, Areas, Resources, Archives). Create a new note by specifying a title and a category:

```bash
ost add "Launch Ostraca CLI" --para Project
```

This will open your editor with pre-filled YAML frontmatter. Add your content below the `---` separators and save.

## 3. List Your Notes

View your PARA tree to see how your knowledge is organized:

```bash
ost list
```

## 4. Search Your Knowledge

Use powerful full-text search to find specific information across all notes:

```bash
ost search "launch"
```

## 5. Manage Notes

### Edit a Note

Use the unique 8-character ID or the full Title:

```bash
ost edit [ID|Title]
```

### Move a Note

Quickly change a note's PARA category:

```bash
ost move [ID|Title] --to Area
```

### Delete a Note

Permanently remove a note (requires confirmation):

```bash
ost delete [ID|Title]
```

## 6. Maintenance

### Backup Your Database

Create a consistent snapshot:

```bash
ost backup
```

### Restore from Backup

```bash
ost restore /path/to/backup.db
```

## 7. AI Integration (MCP)

If you use AI agents that support the Model Context Protocol (MCP), start the server:

```bash
ost mcp-start
```
