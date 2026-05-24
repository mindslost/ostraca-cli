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

## 8. Todo and Reminder Management

Ostraca CLI includes a comprehensive todo and reminder subsystem to track your tasks alongside your notes.

### Add a Task

Create tasks with descriptions, priority levels, and due dates:

```bash
# Add a task due tomorrow with high priority
ost todo add "Draft release notes" "Focus on the new todo feature" --due tomorrow --priority high

# Add a task with a relative deadline in 3 days
ost todo add "Database review" --due +3d --priority medium
```

### List Tasks

View a table of your active tasks sorted by due date and priority:

```bash
# List all active tasks
ost todo list

# Filter tasks by status and priority (including completed tasks)
ost todo list --status in_progress --priority high --all
```

### Complete and Manage Status

Update task status or complete tasks directly:

```bash
# Mark a task as completed (by ID or Title)
ost todo complete [ID|Title]

# Manually transition task status
ost todo status [ID|Title] in_progress
```

### View Calendar

Get a visual summary of scheduled tasks in day, week, or month views:

```bash
# View the current month calendar
ost todo calendar

# View the agenda for a specific day
ost todo calendar --view day --date 05-25-2026
```

### Desktop Alerts & Reminders

You can trigger on-demand desktop alerts for upcoming tasks:

```bash
# Check for tasks due within the next 15 minutes
ost todo check-reminders
```

To configure automatic notifications to run in the background (runs every 5 minutes):

```bash
ost todo setup-reminders
```
Follow the interactive prompt to install the system daemon config files (`launchd` on macOS or `systemd` on Linux).

