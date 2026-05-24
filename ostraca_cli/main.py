"""
Ostraca CLI - Personal Knowledge Base enforcing the PARA method.

This module provides the main CLI entry point using Typer and exposes
MCP (Model Context Protocol) tools for AI agents to interact with the notes.
"""

import os
import shlex
import re
import sqlite3
import subprocess
import tempfile
import html
import datetime
import calendar
import shutil
import sys
from typing import List, Optional, Tuple
from pathlib import Path

import shortuuid
import typer
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.markup import escape
from rich.text import Text
from rich import box

from ostraca_cli.db import (
    get_db,
    init_db,
    backup_db,
    restore_db,
    prune_backups,
    PARA_CATEGORIES,
)
from ostraca_cli.frontmatter import extract_frontmatter

# Initialize Typer app and FastMCP server
app = typer.Typer(
    help="Ostraca CLI - A terminal-based personal knowledge base enforcing the PARA method.",
    add_completion=True,
)
todo_app = typer.Typer(help="Manage todo items and scheduling.")
app.add_typer(todo_app, name="todo")
mcp = FastMCP("Ostraca")
console = Console()

# Run DB initialization when the application starts to ensure schema is up to date
try:
    init_db()
except sqlite3.Error as e:
    console.print(f"[red]Failed to initialize database: {e}[/red]")
    raise typer.Exit(1) from e


def get_editor() -> str:
    """
    Determine the user's preferred text editor.

    Checks the 'EDITOR' environment variable, defaulting to 'vim' if not set.
    """
    return os.environ.get("EDITOR", "vim")


def format_yaml_frontmatter(title: str, category: str, tags: List[str]) -> str:
    """
    Create a YAML frontmatter block for a Markdown note.

    Args:
        title: The title of the note.
        category: The PARA category (Project, Area, Resource, Archive).
        tags: A list of tags to associate with the note.

    Returns:
        A formatted YAML frontmatter string bounded by '---'.
    """
    # Escape double quotes in title to prevent YAML parsing errors
    safe_title = title.replace('"', '\\"')
    tags_str = ", ".join(f'"{t}"' for t in tags)
    return f'---\ntitle: "{safe_title}"\npara: {category}\ntags: [{tags_str}]\n---\n\n'


def get_note_by_identifier(
    identifier: str,
) -> Optional[Tuple[str, str, str, str, str, str]]:
    """
    Retrieve a note from the database by its unique 8-character ID or its Title.

    Args:
        identifier: The note's short ID or full title.

    Returns:
        A tuple containing (id, title, content, para_category, tags, updated_at)
        or None if no match is found.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content, para_category, tags, updated_at "
            "FROM notes WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        return cursor.fetchone()


def complete_note_identifier(incomplete: str) -> List[str]:
    """Autocompletion function for note IDs and titles."""
    if not incomplete:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM notes LIMIT 100")
            results = cursor.fetchall()
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            # Fetch matching IDs or Titles directly using SQL LIKE
            cursor.execute(
                "SELECT id, title FROM notes WHERE id LIKE ? OR LOWER(title) LIKE ?",
                (f"{incomplete}%", f"%{incomplete.lower()}%"),
            )
            results = cursor.fetchall()

    completions = []
    incomplete_lower = incomplete.lower()
    for note_id, title in results:
        if note_id.lower().startswith(incomplete_lower):
            completions.append(note_id)
        elif incomplete_lower in title.lower():
            # If they are typing the title, return the title wrapped in quotes if it has spaces,
            # but returning just the ID or Title works. We'll return what matches best.
            completions.append(title)

    return completions


def edit_content(content: str) -> str:
    """
    Open the provided content in a temporary file using the user's preferred editor.

    Args:
        content: The initial content to be edited.

    Returns:
        The content of the file after the editor session has closed.

    Raises:
        typer.Exit: If the editor command is not found.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        editor = get_editor()
        editor_args = shlex.split(editor) if editor else ["vim"]
        try:
            # Run the editor; check=False because we handle exit codes if needed later
            subprocess.run([*editor_args, tmp_path], check=False)
        except FileNotFoundError as exc:
            console.print(f"[red]Error: Editor '{editor}' not found.[/red]")
            raise typer.Exit(1) from exc

        with open(tmp_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        # Ensure the temporary file is deleted even if the process is interrupted
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def perform_search(query: str, category: Optional[str] = None) -> List[Tuple]:
    """
    Execute a full-text search (FTS5) across titles, content, and tags.

    Args:
        query: The FTS5 search query.
        category: Optional PARA category to filter the search results.

    Returns:
        A list of result tuples from the database.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if category:
            sql = """
                SELECT n.id, n.title, n.para_category, n.updated_at, n.content,
                       snippet(notes_fts, -1, 'START_HL', 'END_HL', '...', 20)
                FROM notes_fts
                JOIN notes n ON notes_fts.rowid = n.rowid
                WHERE notes_fts MATCH ? AND n.para_category = ?
                ORDER BY rank
            """
            params = (query, category)
        else:
            sql = """
                SELECT n.id, n.title, n.para_category, n.updated_at, n.content,
                       snippet(notes_fts, -1, 'START_HL', 'END_HL', '...', 20)
                FROM notes_fts
                JOIN notes n ON notes_fts.rowid = n.rowid
                WHERE notes_fts MATCH ?
                ORDER BY rank
            """
            params = (query,)
        cursor.execute(sql, params)
        return cursor.fetchall()


@app.command()
def add(
    title: str = typer.Argument(..., help="Title of the new note"),
    para: str = typer.Option(..., help=f"PARA category: {', '.join(PARA_CATEGORIES)}"),
) -> None:
    """
    Create a new note with a title and category.

    Opens your default editor with pre-filled frontmatter.
    The note is only saved if the frontmatter remains valid.
    """
    if para not in PARA_CATEGORIES:
        console.print(
            f"[red]Error: Category must be one of: {', '.join(PARA_CATEGORIES)}.[/red]"
        )
        raise typer.Exit(1)

    # Generate a unique 8-character ID for the note
    note_id = str(shortuuid.uuid())[:8]
    initial_content = format_yaml_frontmatter(title, para, [])
    edited_content = edit_content(initial_content)

    # Validate frontmatter after editing
    metadata, _ = extract_frontmatter(edited_content)
    if not metadata:
        console.print("[red]Error: Invalid frontmatter. Note not saved.[/red]")
        raise typer.Exit(1)

    # Extract potentially updated fields from frontmatter
    final_title = metadata.get("title", title)
    final_para = metadata.get("para", para)

    if final_para not in PARA_CATEGORIES:
        console.print(
            f"[yellow]Warning: Invalid category in frontmatter. Defaulting to {para}.[/yellow]"
        )
        final_para = para

    final_tags = ",".join(metadata.get("tags", []))

    with get_db() as conn:
        cursor = conn.cursor()
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor.execute(
                    "INSERT INTO notes (id, title, content, para_category, tags) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (note_id, final_title, edited_content, final_para, final_tags),
                )
                conn.commit()
                break
            except sqlite3.IntegrityError as e:
                # Handle collision on short ID (extremely rare but possible)
                if (
                    "UNIQUE constraint failed: notes.id" in str(e)
                    and attempt < max_retries - 1
                ):
                    note_id = str(shortuuid.uuid())[:8]
                    continue
                console.print(f"[red]Error saving note: {escape(str(e))}[/red]")
                raise typer.Exit(1) from e
    console.print(f"[green]Note '{escape(final_title)}' added successfully.[/green]")


@app.command()
def edit(
    identifier: str = typer.Argument(
        ...,
        autocompletion=complete_note_identifier,
        help="ID or Title of the note to edit",
    ),
) -> None:
    """
    Edit an existing note's content and metadata.

    Opens the note in your default editor. You can update the title,
    category, and tags directly in the frontmatter.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Note '{escape(identifier)}' not found.[/red]")
        raise typer.Exit(1)

    note_id, old_title, old_content, old_para, _, _ = row
    new_content = edit_content(old_content)

    if new_content == old_content:
        console.print("No changes made.")
        return

    metadata, _ = extract_frontmatter(new_content)
    if not metadata:
        console.print(
            "[red]Error: Invalid frontmatter format. Changes not saved.[/red]"
        )
        return

    final_title = metadata.get("title", old_title)
    final_para = metadata.get("para", old_para)
    if final_para not in PARA_CATEGORIES:
        final_para = old_para

    final_tags = ",".join(metadata.get("tags", []))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content = ?, para_category = ?, "
            "tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (final_title, new_content, final_para, final_tags, note_id),
        )
        conn.commit()
    console.print(f"[green]Note '{escape(final_title)}' updated successfully.[/green]")


@app.command(name="open")
def open_note(
    identifier: str = typer.Argument(
        ...,
        autocompletion=complete_note_identifier,
        help="ID or Title of the note to open",
    ),
) -> None:
    """
    Open a note in read-only mode for viewing.

    Any changes made in the editor session will NOT be saved.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Note '{escape(identifier)}' not found.[/red]")
        raise typer.Exit(1)

    _, title, content, _, _, _ = row
    edit_content(content)
    console.print(
        f"[red]Opened in read-only mode.[/red] [bold red]No changes saved.[/bold red] "
        f"To make changes run \"ost edit '{escape(title)}'\"."
    )


@app.command()
def move(
    identifier: str = typer.Argument(
        ...,
        autocompletion=complete_note_identifier,
        help="ID or Title of the note to move",
    ),
    to: str = typer.Option(..., help="Target PARA category"),
) -> None:
    """
    Quickly move a note to a different PARA category.

    Automatically updates the frontmatter inside the note content.
    """
    if to not in PARA_CATEGORIES:
        console.print(
            f"[red]Error: Category must be one of: {', '.join(PARA_CATEGORIES)}.[/red]"
        )
        raise typer.Exit(1)

    row = get_note_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Note '{escape(identifier)}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, content, old_para, _, _ = row
    if old_para == to:
        console.print(f"Note '{escape(title)}' is already in {escape(to)}.")
        return

    metadata, body = extract_frontmatter(content)
    if not metadata:
        # Fallback to simple regex if frontmatter parsing is failing
        new_content = re.sub(
            r"^(para:\s*).+$", rf"\g<1>{to}", content, flags=re.MULTILINE
        )
    else:
        metadata["para"] = to
        tags = metadata.get("tags", [])
        new_content = (
            format_yaml_frontmatter(metadata.get("title", title), to, tags) + body
        )

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET content = ?, para_category = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_content, to, note_id),
            )
            conn.commit()
        console.print(f"[green]Note '{escape(title)}' moved to {escape(to)}.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]Failed to move note: {escape(str(e))}[/red]")
        raise typer.Exit(1) from e


@app.command()
def backup(
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Custom destination path for the backup file"
    ),
    prune: bool = typer.Option(
        False,
        "--prune",
        help="Remove old backups, keeping only the 20 most recent ones",
    ),
) -> None:
    """
    Create a backup of the Ostraca database.

    Uses SQLite's built-in backup API to ensure a consistent snapshot.
    If no path is provided, a timestamped file is created in the
    '~/ostraca-backup' directory.
    """
    try:
        backup_path = backup_db(path)
        console.print(
            f"[green]Backup created successfully at:[/green] [bold cyan]{backup_path}[/bold cyan]"
        )

        if prune:
            deleted = prune_backups(20)
            if deleted:
                console.print(f"[yellow]Pruned {len(deleted)} old backup(s).[/yellow]")
    except Exception as e:
        console.print(f"[red]Error creating backup: {escape(str(e))}[/red]")
        raise typer.Exit(1)


@app.command()
def restore(
    path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the backup file to restore",
    ),
) -> None:
    """
    Restore the Ostraca database from a backup file.

    WARNING: This will overwrite your current notes.
    Uses SQLite's built-in backup API to safely restore.
    """
    console.print(
        f"[bold red]WARNING:[/bold red] You are about to restore the database from {escape(str(path))}."
    )
    console.print(
        "[red]This will completely overwrite your current notes and database structure.[/red]"
    )

    if typer.confirm("Are you sure you want to proceed?"):
        try:
            # We perform a backup before restoring, just in case
            backup_db()
            restore_db(path)
            console.print(
                f"[green]Database restored successfully from:[/green] [bold cyan]{escape(str(path))}[/bold cyan]"
            )
        except Exception as e:
            console.print(f"[red]Error during restore: {escape(str(e))}[/red]")
            raise typer.Exit(1)
    else:
        console.print("Restore cancelled.")


@app.command()
def delete(
    identifier: str = typer.Argument(
        ...,
        autocompletion=complete_note_identifier,
        help="ID or Title of the note to delete",
    ),
) -> None:
    """
    Permanently delete a note.

    Requires user confirmation before proceeding.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Note '{escape(identifier)}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, _, _, _, _ = row
    if typer.confirm(f"Are you sure you want to delete '{title}'?"):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                conn.commit()
            console.print(
                f"[green]Note '{escape(title)}' deleted successfully.[/green]"
            )
        except sqlite3.Error as e:
            console.print(f"[red]Failed to delete note: {escape(str(e))}[/red]")
            raise typer.Exit(1) from e
    else:
        console.print("Deletion cancelled.")


@app.command()
def export(
    identifier: str = typer.Argument(
        ...,
        autocompletion=complete_note_identifier,
        help="ID or Title of the note to export",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination path or directory (defaults to home folder)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
) -> None:
    """
    Export a note to a Markdown file.

    If output is a directory, the file will be named '{title}.md'.
    If output is not provided, it defaults to the user's home directory.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Note '{escape(identifier)}' not found.[/red]")
        raise typer.Exit(1)

    _, title, content, _, _, _ = row
    filename = re.sub(r'[\\/*?:"<>|]', "", title) + ".md"

    # Determine the final output path
    if output is None:
        # Default to home directory
        output_path = Path.home() / filename
    elif output.is_dir():
        output_path = output / filename
    else:
        output_path = output

    if output_path.exists() and not force:
        console.print(
            f"[red]Error: File '{output_path}' already exists. Use --force to overwrite.[/red]"
        )
        raise typer.Exit(1)

    try:
        # Ensure parent directory exists if a path was provided
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(
            f"[green]Note '{escape(title)}' exported to '{output_path}'.[/green]"
        )
    except Exception as e:
        console.print(f"[red]Failed to export note: {escape(str(e))}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (SQLite FTS5 syntax)"),
    para: Optional[str] = typer.Option(None, help="Filter by PARA category"),
    raw: bool = typer.Option(False, "--raw", help="Output raw XML for AI context"),
) -> None:
    """
    Search notes using Full-Text Search.

    Displays results in a table with matches highlighted in snippets.
    Supports '--raw' for tool-like integration.
    """
    try:
        results = perform_search(query, para)
    except sqlite3.OperationalError as exc:
        if raw:
            print("<error>Malformed search query</error>")
        else:
            console.print("[red]Error: Malformed search query.[/red]")
        raise typer.Exit(1) from exc

    if raw:
        xml_output = []
        for note_id, title, category, updated_at, content, _ in results:
            xml_output.append(
                f'<context><note id="{html.escape(note_id)}" title="{html.escape(title)}" '
                f'category="{html.escape(category)}" last_updated="{html.escape(str(updated_at))}">'
                f"{html.escape(content)}</note></context>"
            )
        print("\n".join(xml_output))
    else:
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("ID", style="dim white")
        table.add_column("Title", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Snippet", style="white")
        table.add_column("Last Updated", style="green")

        for note_id, title, category, updated_at, _, snippet in results:
            # Build highlighted snippet using Text objects to avoid markup errors
            snippet_text = Text()
            curr = (snippet or "").replace("\n", " ")
            while "START_HL" in curr:
                pre, rest = curr.split("START_HL", 1)
                snippet_text.append(pre)
                if "END_HL" in rest:
                    match, rest = rest.split("END_HL", 1)
                    snippet_text.append(match, style="bold yellow")
                    curr = rest
                else:
                    snippet_text.append(rest)
                    curr = ""
            snippet_text.append(curr)

            table.add_row(
                Text(note_id),
                Text(title),
                Text(category),
                snippet_text,
                Text(str(updated_at)),
            )
        console.print(table)


def get_filtered_notes(para: Optional[str], tags: Optional[str]) -> List[Tuple]:
    """Fetch and filter notes based on PARA category and tags."""
    conditions = []
    params = []

    if para:
        conditions.append("para_category = ?")
        params.append(para)

    if tags:
        filter_tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if filter_tags:
            sql_parts = []
            for t in filter_tags:
                sql_parts.append("LOWER(',' || tags || ',') LIKE ?")
                params.append(f"%,{t},%")
            conditions.append(f"({ ' OR '.join(sql_parts) })")

    query_sql = "SELECT id, title, para_category, tags FROM notes"
    if conditions:
        query_sql += " WHERE " + " AND ".join(conditions)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query_sql, params)
        return cursor.fetchall()


@app.command(name="list")
def list_notes(
    para: Optional[str] = typer.Option(None, help="Filter by PARA category"),
    tags: Optional[str] = typer.Option(None, help="Filter by comma-separated tags"),
) -> None:
    """
    List notes organized in a PARA directory tree.

    Supports filtering by category and/or tags.
    Use --interactive to act on notes.
    """
    if para and para not in PARA_CATEGORIES:
        console.print(
            f"[red]Error: Category must be one of: {', '.join(PARA_CATEGORIES)}.[/red]"
        )
        raise typer.Exit(1)

    results = get_filtered_notes(para, tags)
    if not results:
        console.print("No notes found matching the criteria.")
        return

    # Render static tree
    tree = Tree("Ostraca")
    categories = {}
    for note_id, title, cat, tags_str in results:
        categories.setdefault(cat, []).append((note_id, title, tags_str))

    for cat in PARA_CATEGORIES:
        if cat in categories:
            cat_node = tree.add(f"[bold cyan]{cat}s[/bold cyan]")
            for note_id, title, tags_str in sorted(
                categories[cat], key=lambda x: x[1].lower()
            ):
                node_text = f"[dim white]{escape(note_id)}[/dim white] | [green]{escape(title)}[/green]"
                if tags_str:
                    formatted_tags = ", ".join(
                        t.strip() for t in tags_str.split(",") if t.strip()
                    )
                    if formatted_tags:
                        node_text += f" [dim]({escape(formatted_tags)})[/dim]"
                cat_node.add(node_text)
    console.print(tree)


@mcp.tool()
def search_ostraca_notes(query: str, category: Optional[str] = None) -> str:
    """
    Search your personal knowledge base using FTS5.

    This tool is intended for AI agents to retrieve context.
    """
    try:
        results = perform_search(query, category)
        out = [
            f'<context><note id="{html.escape(r[0])}" title="{html.escape(r[1])}" '
            f'category="{html.escape(r[2])}" last_updated="{html.escape(str(r[3]))}">'
            f"{html.escape(r[4])}</note></context>"
            for r in results
        ]
        return "\n".join(out) if out else "No notes found matching the query."
    except sqlite3.OperationalError:
        return "<error>Malformed search query</error>"


@mcp.tool()
def get_ostraca_note(identifier: str) -> str:
    """
    Retrieve the full content of any note by its ID or title.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        return f"Note '{identifier}' not found."

    note_id, title, content, category, tags, updated_at = row
    return (
        f'<context><note id="{html.escape(note_id)}" title="{html.escape(title)}" '
        f'category="{html.escape(category)}" tags="{html.escape(tags or "")}" '
        f'last_updated="{html.escape(str(updated_at))}">{html.escape(content)}</note></context>'
    )


@mcp.tool()
def get_project_context(project_name: str) -> str:
    """
    Retrieve the full content of a project note by its title.

    Use this to get details about specific active projects.
    """
    row = get_note_by_identifier(project_name)
    # Ensure it's actually in the 'Project' category
    if not row or row[3] != "Project":
        return f"Project '{project_name}' not found."

    note_id, title, content, category, _, updated_at = row
    return (
        f'<context><note id="{html.escape(note_id)}" title="{html.escape(title)}" '
        f'category="{html.escape(category)}" last_updated="{html.escape(str(updated_at))}">'
        f"{html.escape(content)}</note></context>"
    )


@mcp.tool()
def create_ostraca_note(
    title: str, para: str, content: str, tags: Optional[List[str]] = None
) -> str:
    """
    Create a new note in your personal knowledge base.

    Args:
        title: The title of the note.
        para: The PARA category (Project, Area, Resource, Archive).
        content: The Markdown content of the note. If it doesn't include YAML frontmatter,
                 one will be automatically generated.
        tags: Optional list of tags for the note.
    """
    if para not in PARA_CATEGORIES:
        return f"Error: Category must be one of: {', '.join(PARA_CATEGORIES)}."

    # Check if content already has frontmatter
    metadata, body = extract_frontmatter(content)

    if not metadata:
        # No frontmatter found, prepend it
        full_content = format_yaml_frontmatter(title, para, tags or []) + content
        final_title = title
        final_para = para
        final_tags = ",".join(tags or [])
    else:
        # Frontmatter found, use it
        full_content = content
        final_title = metadata.get("title", title)
        final_para = metadata.get("para", para)
        if final_para not in PARA_CATEGORIES:
            final_para = para
        final_tags = ",".join(metadata.get("tags", []))

    note_id = str(shortuuid.uuid())[:8]

    with get_db() as conn:
        cursor = conn.cursor()
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor.execute(
                    "INSERT INTO notes (id, title, content, para_category, tags) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (note_id, final_title, full_content, final_para, final_tags),
                )
                conn.commit()
                return f"Note '{final_title}' created successfully with ID {note_id}."
            except sqlite3.IntegrityError as e:
                # Handle collision on short ID (extremely rare but possible)
                if (
                    "UNIQUE constraint failed: notes.id" in str(e)
                    and attempt < max_retries - 1
                ):
                    note_id = str(shortuuid.uuid())[:8]
                    continue
                return f"Error saving note: {e}"
    return "Failed to create note after multiple retries."


@mcp.tool()
def edit_ostraca_note(identifier: str, content: str) -> str:
    """
    Edit an existing note in your personal knowledge base.

    Args:
        identifier: The ID or Title of the note to edit.
        content: The full new content of the note, including YAML frontmatter.
                 The frontmatter will be parsed to update note metadata (title, para, tags).
    """
    row = get_note_by_identifier(identifier)
    if not row:
        return f"Error: Note '{identifier}' not found."

    note_id, old_title, old_content, old_para, _, _ = row

    if content == old_content:
        return "No changes made."

    metadata, _ = extract_frontmatter(content)
    if not metadata:
        return "Error: Invalid frontmatter format. Changes not saved. Ensure the content starts with '---' and ends with '---' for frontmatter."

    final_title = metadata.get("title", old_title)
    final_para = metadata.get("para", old_para)
    if final_para not in PARA_CATEGORIES:
        final_para = old_para

    final_tags = ",".join(metadata.get("tags", []))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content = ?, para_category = ?, "
            "tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (final_title, content, final_para, final_tags, note_id),
        )
        conn.commit()
    return f"Note '{final_title}' updated successfully."


@mcp.tool()
def patch_ostraca_note(identifier: str, old_string: str, new_string: str) -> str:
    """
    Apply a targeted text replacement to an existing note.

    This is more efficient than edit_ostraca_note for large notes
    because it only transmits the change.

    Args:
        identifier: The ID or Title of the note to patch.
        old_string: The exact text to find and replace.
        new_string: The text to replace it with.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        return f"Error: Note '{identifier}' not found."

    note_id, old_title, old_content, old_para, old_tags_str, _ = row

    # Ensure old_string exists and is unique to prevent accidental multiple replacements
    count = old_content.count(old_string)
    if count == 0:
        return f"Error: 'old_string' not found in note '{identifier}'."
    if count > 1:
        return f"Error: 'old_string' is ambiguous (found {count} occurrences) in note '{identifier}'."

    new_content = old_content.replace(old_string, new_string)

    # Reparse metadata in case it was changed
    metadata, _ = extract_frontmatter(new_content)

    final_title = old_title
    final_para = old_para
    final_tags = old_tags_str

    if metadata:
        final_title = metadata.get("title", old_title)
        final_para = metadata.get("para", old_para)
        if final_para not in PARA_CATEGORIES:
            final_para = old_para
        final_tags = ",".join(metadata.get("tags", []))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content = ?, para_category = ?, "
            "tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (final_title, new_content, final_para, final_tags, note_id),
        )
        conn.commit()

    return f"Note '{final_title}' patched successfully."


@mcp.tool()
def append_to_ostraca_note(identifier: str, content: str) -> str:
    """
    Append content to the end of an existing note.

    Args:
        identifier: The ID or Title of the note.
        content: The text to append to the end of the note.
    """
    row = get_note_by_identifier(identifier)
    if not row:
        return f"Error: Note '{identifier}' not found."

    note_id, title, old_content, para, tags, _ = row
    new_content = old_content.rstrip() + "\n\n" + content.strip() + "\n"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_content, note_id),
        )
        conn.commit()

    return f"Content appended to note '{title}'."


@app.command()
def mcp_start() -> None:
    """
    Start the FastMCP server for AI agent integration.

    Uses standard input/output (stdio) for communication.
    """
    mcp.run(transport="stdio")


# ─── TODO LIST FLOW IMPLEMENTATION ───────────────────────────────────────────

def parse_due_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse a due date string.
    Supported formats:
    - MM-DD-YYYY HH:MM
    - MM-DD-YYYY
    - "today" -> YYYY-MM-DD 23:59
    - "tomorrow" -> YYYY-MM-DD 23:59
    - "+Nd" (e.g. +3d) -> N days from now, YYYY-MM-DD 23:59
    - "+Nw" (e.g. +1w) -> N weeks from now, YYYY-MM-DD 23:59
    
    Returns:
        Formatted datetime string `YYYY-MM-DD HH:MM` or None if date_str is None.
    """
    if not date_str:
        return None

    date_str = date_str.strip().lower()
    now = datetime.datetime.now()

    if date_str == "today":
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        return target.strftime("%Y-%m-%d %H:%M")
    elif date_str == "tomorrow":
        target = (now + datetime.timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        return target.strftime("%Y-%m-%d %H:%M")

    match_relative = re.match(r"^\+(\d+)([dw])$", date_str)
    if match_relative:
        val = int(match_relative.group(1))
        unit = match_relative.group(2)
        if unit == "d":
            target = (now + datetime.timedelta(days=val)).replace(hour=23, minute=59, second=0, microsecond=0)
        else: # 'w'
            target = (now + datetime.timedelta(weeks=val)).replace(hour=23, minute=59, second=0, microsecond=0)
        return target.strftime("%Y-%m-%d %H:%M")

    # Explicit format: MM-DD-YYYY HH:MM
    try:
        dt = datetime.datetime.strptime(date_str, "%m-%d-%Y %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass

    # Explicit format: MM-DD-YYYY
    try:
        dt = datetime.datetime.strptime(date_str, "%m-%d-%Y")
        dt = dt.replace(hour=23, minute=59, second=0, microsecond=0)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass

    raise ValueError(
        "Invalid date format. Expected: MM-DD-YYYY HH:MM, MM-DD-YYYY, 'today', 'tomorrow', or '+Nd'/'+Nw' (e.g., '+3d')."
    )


def complete_todo_identifier(incomplete: str) -> List[str]:
    """Autocompletion function for todo IDs and titles."""
    with get_db() as conn:
        cursor = conn.cursor()
        if not incomplete:
            cursor.execute("SELECT id, title FROM todos LIMIT 100")
        else:
            cursor.execute(
                "SELECT id, title FROM todos WHERE id LIKE ? OR LOWER(title) LIKE ?",
                (f"{incomplete}%", f"%{incomplete.lower()}%"),
            )
        results = cursor.fetchall()

    completions = []
    incomplete_lower = incomplete.lower()
    for todo_id, title in results:
        if todo_id.lower().startswith(incomplete_lower):
            completions.append(todo_id)
        elif incomplete_lower in title.lower():
            completions.append(title)
    return completions


def get_todo_by_identifier(identifier: str) -> Optional[Tuple]:
    """Retrieve a todo from the database by its ID or Title."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, description, status, priority, due_date, reminder_sent FROM todos "
            "WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        return cursor.fetchone()


@todo_app.command(name="add")
def todo_add(
    title: str = typer.Argument(..., help="Title of the new task"),
    description: Optional[str] = typer.Argument(None, help="Optional description of the task"),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="Due date: MM-DD-YYYY HH:MM, MM-DD-YYYY, today, tomorrow, or +Nd/+Nw"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority: low, medium, high"),
) -> None:
    """Add a new task to your todo list."""
    if priority not in ("low", "medium", "high"):
        console.print("[red]Error: Priority must be 'low', 'medium', or 'high'.[/red]")
        raise typer.Exit(1)

    try:
        parsed_due = parse_due_date(due)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    todo_id = str(shortuuid.uuid())[:8]

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO todos (id, title, description, status, priority, due_date, reminder_sent) "
                "VALUES (?, ?, ?, 'todo', ?, ?, 0)",
                (todo_id, title, description, priority, parsed_due),
            )
            conn.commit()
        except sqlite3.Error as e:
            console.print(f"[red]Database error: {e}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]Task added successfully with ID [bold]{todo_id}[/bold].[/green]")


@todo_app.command(name="edit")
def todo_edit(
    identifier: str = typer.Argument(..., autocompletion=complete_todo_identifier, help="ID or Title of the task to edit"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New title"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    due: Optional[str] = typer.Option(None, "--due", help="New due date: MM-DD-YYYY HH:MM, MM-DD-YYYY, today, tomorrow, or +Nd/+Nw"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority: low, medium, high"),
) -> None:
    """Edit an existing task."""
    row = get_todo_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Task '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    todo_id, old_title, old_desc, old_status, old_prio, old_due, old_reminder = row

    new_title = title if title is not None else old_title
    new_desc = description if description is not None else old_desc
    new_prio = priority if priority is not None else old_prio

    if new_prio not in ("low", "medium", "high"):
        console.print("[red]Error: Priority must be 'low', 'medium', or 'high'.[/red]")
        raise typer.Exit(1)

    if due is not None:
        if due.strip() == "":
            new_due = None
        else:
            try:
                new_due = parse_due_date(due)
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1)
    else:
        new_due = old_due

    # If due date changes, reset reminder_sent to 0 so they can receive notifications again
    reset_reminder = 0 if new_due != old_due else old_reminder

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE todos SET title = ?, description = ?, due_date = ?, priority = ?, "
            "reminder_sent = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_title, new_desc, new_due, new_prio, reset_reminder, todo_id),
        )
        conn.commit()

    console.print(f"[green]Task '[bold]{new_title}[/bold]' updated successfully.[/green]")


@todo_app.command(name="complete")
def todo_complete(
    identifier: str = typer.Argument(..., autocompletion=complete_todo_identifier, help="ID or Title of the task to complete"),
) -> None:
    """Mark a task as completed."""
    row = get_todo_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Task '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    todo_id, title, _, _, _, _, _ = row

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE todos SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (todo_id,),
        )
        conn.commit()

    console.print(f"[green]Task '[bold]{title}[/bold]' marked as completed![/green]")


@todo_app.command(name="status")
def todo_status(
    identifier: str = typer.Argument(..., autocompletion=complete_todo_identifier, help="ID or Title of the task"),
    status: str = typer.Argument(..., help="New status: todo, in_progress, done"),
) -> None:
    """Update a task's status."""
    if status not in ("todo", "in_progress", "done"):
        console.print("[red]Error: Status must be 'todo', 'in_progress', or 'done'.[/red]")
        raise typer.Exit(1)

    row = get_todo_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Task '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    todo_id, title, _, old_status, _, _, _ = row

    with get_db() as conn:
        cursor = conn.cursor()
        # Reset reminder_sent if status changed from done back to todo/in_progress
        reminder_val = 0 if status != "done" else 1
        cursor.execute(
            "UPDATE todos SET status = ?, reminder_sent = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, reminder_val, todo_id),
        )
        conn.commit()

    console.print(f"[green]Status of task '[bold]{title}[/bold]' updated from '{old_status}' to '{status}'.[/green]")


@todo_app.command(name="delete")
def todo_delete(
    identifier: str = typer.Argument(..., autocompletion=complete_todo_identifier, help="ID or Title of the task to delete"),
) -> None:
    """Permanently delete a task."""
    row = get_todo_by_identifier(identifier)
    if not row:
        console.print(f"[red]Error: Task '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    todo_id, title, _, _, _, _, _ = row

    if typer.confirm(f"Are you sure you want to delete task '{title}'?"):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
        console.print(f"[green]Task '{title}' deleted successfully.[/green]")
    else:
        console.print("Deletion cancelled.")


@todo_app.command(name="list")
def todo_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status: todo, in_progress, done"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority: low, medium, high"),
    all_items: bool = typer.Option(False, "--all", "-a", help="Show all tasks including completed ones"),
) -> None:
    """List todo tasks organized in a table."""
    conditions = []
    params = []

    if status:
        if status not in ("todo", "in_progress", "done"):
            console.print("[red]Error: Status filter must be 'todo', 'in_progress', or 'done'.[/red]")
            raise typer.Exit(1)
        conditions.append("status = ?")
        params.append(status)
    elif not all_items:
        conditions.append("status != 'done'")

    if priority:
        if priority not in ("low", "medium", "high"):
            console.print("[red]Error: Priority filter must be 'low', 'medium', or 'high'.[/red]")
            raise typer.Exit(1)
        conditions.append("priority = ?")
        params.append(priority)

    query = "SELECT id, title, description, status, priority, due_date FROM todos"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY due_date IS NULL ASC, due_date ASC, CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END ASC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        console.print("[yellow]No tasks found matching your filters.[/yellow]")
        return

    table = Table(title="[bold magenta]Ostraca Todo List[/bold magenta]", border_style="magenta", box=box.ROUNDED)
    table.add_column("ID", style="dim cyan", justify="center")
    table.add_column("Status", justify="left")
    table.add_column("Priority", justify="left")
    table.add_column("Title & Description", style="white")
    table.add_column("Due Date")

    now = datetime.datetime.now()

    for row in rows:
        tid, title, desc, stat, prio, due = row

        if stat == "done":
            status_str = "[green]✔ Done[/green]"
        elif stat == "in_progress":
            status_str = "[yellow]◑ In Prog[/yellow]"
        else:
            status_str = "[red]○ Todo[/red]"

        if prio == "high":
            prio_str = "[bold red]▲ High[/bold red]"
        elif prio == "medium":
            prio_str = "[bold yellow]◆ Med[/bold yellow]"
        else:
            prio_str = "[bold blue]▼ Low[/bold blue]"

        title_text = Text()
        title_text.append(title, style="bold")
        if desc:
            title_text.append(f"\n{desc}", style="dim italic")

        if due:
            try:
                due_dt = datetime.datetime.strptime(due, "%Y-%m-%d %H:%M")
                due_display = due_dt.strftime("%m-%d-%Y %H:%M")
                if due_dt < now:
                    diff = now - due_dt
                    if diff.days > 0:
                        rel = f"Overdue {diff.days}d"
                    elif diff.seconds // 3600 > 0:
                        rel = f"Overdue {diff.seconds // 3600}h"
                    else:
                        rel = f"Overdue {diff.seconds // 60}m"
                    due_str = f"[bold red]{due_display} ({rel})[/bold red]"
                else:
                    diff = due_dt - now
                    if diff.days > 0:
                        rel = f"In {diff.days}d"
                    elif diff.seconds // 3600 > 0:
                        rel = f"In {diff.seconds // 3600}h"
                    else:
                        rel = f"In {diff.seconds // 60}m"
                    
                    if diff.days == 0:
                        due_str = f"[yellow]{due_display} ({rel})[/yellow]"
                    else:
                        due_str = f"[green]{due_display} ({rel})[/green]"
            except Exception:
                due_str = f"[white]{due}[/white]"
        else:
            due_str = "[dim]No due date[/dim]"

        table.add_row(tid, status_str, prio_str, title_text, due_str)

    console.print(table)


@todo_app.command(name="calendar")
def todo_calendar(
    view: str = typer.Option("month", "--view", "-v", help="Calendar view: day, week, month"),
    date_str: Optional[str] = typer.Option(None, "--date", "-d", help="Base date (MM-DD-YYYY), defaults to today"),
) -> None:
    """Show a calendar view (day/week/month) of upcoming tasks."""
    if view not in ("day", "week", "month"):
        console.print("[red]Error: View must be 'day', 'week', or 'month'.[/red]")
        raise typer.Exit(1)

    now = datetime.datetime.now()
    if date_str:
        try:
            base_date = datetime.datetime.strptime(date_str.strip(), "%m-%d-%Y")
        except ValueError:
            console.print("[red]Error: Base date must be in MM-DD-YYYY format.[/red]")
            raise typer.Exit(1)
    else:
        base_date = now

    from rich.panel import Panel

    if view == "month":
        year = base_date.year
        month = base_date.month

        _, last_day = calendar.monthrange(year, month)
        start_month_str = f"{year:04d}-{month:02d}-01 00:00"
        end_month_str = f"{year:04d}-{month:02d}-{last_day:02d} 23:59"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, status, priority, due_date FROM todos "
                "WHERE due_date >= ? AND due_date <= ? "
                "ORDER BY due_date ASC",
                (start_month_str, end_month_str),
            )
            tasks = cursor.fetchall()

        tasks_by_day = {}
        for t in tasks:
            due_str = t[4]
            try:
                dt = datetime.datetime.strptime(due_str, "%Y-%m-%d %H:%M")
                tasks_by_day.setdefault(dt.day, []).append(t)
            except ValueError:
                pass

        table = Table(
            title=f"[bold magenta]Calendar: {calendar.month_name[month]} {year}[/bold magenta]",
            box=box.ROUNDED,
            expand=True,
            border_style="magenta",
            show_lines=True,
        )
        
        days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for day_name in days_of_week:
            table.add_column(day_name, justify="left", style="white", ratio=1)

        cal = calendar.Calendar(firstweekday=6)
        month_matrix = cal.monthdayscalendar(year, month)
        target_height = 5
        
        for week in month_matrix:
            week_cells = []
            for day in week:
                if day == 0:
                    week_cells.append("\n" * (target_height - 1))
                else:
                    cell_lines = []
                    is_today = (day == now.day and month == now.month and year == now.year)
                    if is_today:
                        cell_lines.append(f"[bold yellow reverse] {day:02d} (Today) [/bold yellow reverse]")
                    else:
                        cell_lines.append(f"[bold white]{day:02d}[/bold white]")
                    
                    day_tasks = tasks_by_day.get(day, [])
                    if day_tasks:
                        cell_lines.append("[dim]──────────[/dim]")
                        slots_left = target_height - 2
                        
                        if len(day_tasks) <= slots_left:
                            for tid, title, status, priority, _ in day_tasks:
                                stat_icon = "✔" if status == "done" else ("◑" if status == "in_progress" else "○")
                                stat_color = "green" if status == "done" else ("yellow" if status == "in_progress" else "red")
                                prio_color = "red" if priority == "high" else ("yellow" if priority == "medium" else "blue")
                                
                                trunc_title = title[:12] + ".." if len(title) > 12 else title
                                cell_lines.append(
                                    f"[{stat_color}]{stat_icon}[/{stat_color}] "
                                    f"[{prio_color}]{tid}[/{prio_color}] "
                                    f"{trunc_title}"
                                )
                        else:
                            for tid, title, status, priority, _ in day_tasks[:slots_left - 1]:
                                stat_icon = "✔" if status == "done" else ("◑" if status == "in_progress" else "○")
                                stat_color = "green" if status == "done" else ("yellow" if status == "in_progress" else "red")
                                prio_color = "red" if priority == "high" else ("yellow" if priority == "medium" else "blue")
                                
                                trunc_title = title[:12] + ".." if len(title) > 12 else title
                                cell_lines.append(
                                    f"[{stat_color}]{stat_icon}[/{stat_color}] "
                                    f"[{prio_color}]{tid}[/{prio_color}] "
                                    f"{trunc_title}"
                                )
                            remaining = len(day_tasks) - (slots_left - 1)
                            cell_lines.append(f"[dim]+ {remaining} more...[/dim]")
                    
                    while len(cell_lines) < target_height:
                        cell_lines.append("")
                    week_cells.append("\n".join(cell_lines[:target_height]))
            table.add_row(*week_cells)
        console.print(table)

    elif view == "week":
        start_of_week = base_date - datetime.timedelta(days=base_date.weekday())
        
        grid = Table.grid(expand=True, padding=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)

        panels = []
        for i in range(7):
            day_dt = start_of_week + datetime.timedelta(days=i)
            start_day_str = day_dt.replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
            end_day_str = day_dt.replace(hour=23, minute=59).strftime("%Y-%m-%d %H:%M")

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, title, status, priority, due_date FROM todos "
                    "WHERE due_date >= ? AND due_date <= ? "
                    "ORDER BY due_date ASC",
                    (start_day_str, end_day_str),
                )
                day_tasks = cursor.fetchall()

            day_lines = []
            if day_tasks:
                for tid, title, status, priority, due_str in day_tasks:
                    try:
                        dt = datetime.datetime.strptime(due_str, "%Y-%m-%d %H:%M")
                        time_str = dt.strftime("%H:%M")
                    except ValueError:
                        time_str = "23:59"
                    
                    stat_icon = "✔" if status == "done" else ("◑" if status == "in_progress" else "○")
                    stat_color = "green" if status == "done" else ("yellow" if status == "in_progress" else "red")
                    prio_icon = "▲" if priority == "high" else ("◆" if priority == "medium" else "▼")
                    prio_color = "red" if priority == "high" else ("yellow" if priority == "medium" else "blue")

                    day_lines.append(
                        f"[{stat_color}]{stat_icon}[/{stat_color}] "
                        f"[{prio_color}]{prio_icon}[/{prio_color}] "
                        f"[dim]{time_str}[/dim] [cyan]{tid}[/cyan] [bold]{title}[/bold]"
                    )
            else:
                day_lines.append("[dim]No tasks scheduled[/dim]")

            day_label = day_dt.strftime("%A, %m-%d-%Y")
            is_today = (day_dt.date() == now.date())
            border_style = "yellow" if is_today else "magenta"
            panel_title = f"[bold yellow]{day_label} (Today)[/bold yellow]" if is_today else f"[bold white]{day_label}[/bold white]"

            panels.append(
                Panel(
                    "\n".join(day_lines),
                    title=panel_title,
                    border_style=border_style,
                    box=box.ROUNDED,
                )
            )

        grid.add_row(panels[0], panels[1])
        grid.add_row(panels[2], panels[3])
        grid.add_row(panels[4], panels[5])
        grid.add_row(panels[6], "")
        
        console.print(Panel(grid, title="[bold magenta]Weekly Task Calendar[/bold magenta]", border_style="magenta", box=box.ROUNDED))

    elif view == "day":
        start_day_str = base_date.replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
        end_day_str = base_date.replace(hour=23, minute=59).strftime("%Y-%m-%d %H:%M")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, description, status, priority, due_date FROM todos "
                "WHERE due_date >= ? AND due_date <= ? "
                "ORDER BY due_date ASC",
                (start_day_str, end_day_str),
            )
            day_tasks = cursor.fetchall()

        table = Table(title=f"Agenda for {base_date.strftime('%A, %m-%d-%Y')}", box=box.ROUNDED, border_style="magenta", expand=True)
        table.add_column("Time", justify="center", style="dim cyan")
        table.add_column("ID", justify="center", style="dim cyan")
        table.add_column("Status", justify="center")
        table.add_column("Priority", justify="center")
        table.add_column("Title & Description")

        if day_tasks:
            for tid, title, desc, status, priority, due_str in day_tasks:
                try:
                    dt = datetime.datetime.strptime(due_str, "%Y-%m-%d %H:%M")
                    time_str = dt.strftime("%H:%M")
                except ValueError:
                    time_str = "23:59"
                
                stat_icon = "✔ Done" if status == "done" else ("◑ In Prog" if status == "in_progress" else "○ Todo")
                stat_color = "green" if status == "done" else ("yellow" if status == "in_progress" else "red")
                prio_icon = "▲ High" if priority == "high" else ("◆ Med" if priority == "medium" else "▼ Low")
                prio_color = "red" if priority == "high" else ("yellow" if priority == "medium" else "blue")

                title_text = Text()
                title_text.append(title, style="bold")
                if desc:
                    title_text.append(f"\n{desc}", style="dim italic")

                table.add_row(
                    time_str,
                    tid,
                    f"[{stat_color}]{stat_icon}[/{stat_color}]",
                    f"[{prio_color}]{prio_icon}[/{prio_color}]",
                    title_text
                )
        else:
            table.add_row("-", "-", "-", "-", "[dim]No tasks scheduled for this day.[/dim]")

        console.print(table)


def send_notification(title: str, message: str, urgency: str = "normal") -> bool:
    """Send a platform-native desktop notification (supports Linux & macOS)."""
    if sys.platform == "darwin":
        safe_title = title.replace('"', '\\"')
        safe_message = message.replace('"', '\\"')
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=False)
            return True
        except Exception:
            return False
    elif shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-a", "Ostraca", "-u", urgency, title, message],
                check=False,
            )
            return True
        except Exception:
            return False
    return False


@todo_app.command(name="check-reminders")
def todo_check_reminders(
    buffer_minutes: int = typer.Option(15, "--buffer", "-b", help="Check for tasks due within this many minutes"),
) -> None:
    """Check for upcoming tasks and trigger system notifications."""
    now = datetime.datetime.now()
    limit = now + datetime.timedelta(minutes=buffer_minutes)

    limit_str = limit.strftime("%Y-%m-%d %H:%M")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, due_date, priority FROM todos "
            "WHERE status != 'done' AND due_date <= ? AND reminder_sent = 0",
            (limit_str,),
        )
        rows = cursor.fetchall()

    if not rows:
        return

    notified_ids = []

    for tid, title, due, priority in rows:
        urgency = "normal"
        if priority == "high":
            urgency = "critical"
        elif priority == "low":
            urgency = "low"

        message = f"Task due at {due}"
        # Trigger native desktop notification (AppleScript on macOS, notify-send on Linux)
        if send_notification(f"Ostraca Task Due: {title}", message, urgency):
            notified_ids.append(tid)
        else:
            console.print(f"[yellow]Reminder: {title} (Due: {due})[/yellow]")
            notified_ids.append(tid)

    if notified_ids:
        with get_db() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in notified_ids)
            cursor.execute(
                f"UPDATE todos SET reminder_sent = 1 WHERE id IN ({placeholders})",
                notified_ids,
            )
            conn.commit()
        console.print(f"[green]Sent {len(notified_ids)} task reminder notification(s).[/green]")


@todo_app.command(name="setup-systemd")
def todo_setup_systemd() -> None:
    """Print instructions and generate systemd service and timer files for user reminders."""
    import sys
    
    ost_path = shutil.which("ost")
    if not ost_path:
        ost_path = Path(sys.executable).parent / "ost"
        if not ost_path.exists():
            ost_path = "ost"
            
    service_content = f"""[Unit]
Description=Ostraca CLI Todo Reminders Service
After=network.target

[Service]
Type=oneshot
ExecStart={ost_path} todo check-reminders
"""

    timer_content = """[Unit]
Description=Ostraca CLI Todo Reminders Timer

[Timer]
OnBootSec=1m
OnUnitActiveSec=5m
Unit=ostraca-reminders.service

[Install]
WantedBy=timers.target
"""

    user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    
    console.print("[bold magenta]Systemd Configuration Setup[/bold magenta]")
    console.print(f"Detected `ost` executable at: [cyan]{ost_path}[/cyan]")
    console.print(f"User systemd directory: [cyan]{user_systemd_dir}[/cyan]\n")

    if typer.confirm("Would you like to write the service and timer files automatically?"):
        try:
            user_systemd_dir.mkdir(parents=True, exist_ok=True)
            
            service_file = user_systemd_dir / "ostraca-reminders.service"
            timer_file = user_systemd_dir / "ostraca-reminders.timer"
            
            with open(service_file, "w") as f:
                f.write(service_content)
            with open(timer_file, "w") as f:
                f.write(timer_content)
                
            console.print(f"[green]✓ Wrote {service_file}[/green]")
            console.print(f"[green]✓ Wrote {timer_file}[/green]")
            
            console.print("\n[bold green]To enable and start the reminder service timer, run the following commands:[/bold green]")
            console.print("  [bold cyan]systemctl --user daemon-reload[/bold cyan]")
            console.print("  [bold cyan]systemctl --user enable --now ostraca-reminders.timer[/bold cyan]")
            console.print("\n[bold green]To check the status of your timer:[/bold green]")
            console.print("  [bold cyan]systemctl --user status ostraca-reminders.timer[/bold cyan]")
            console.print("  [bold cyan]journalctl --user -u ostraca-reminders.service[/bold cyan]")
        except Exception as e:
            console.print(f"[red]Error writing systemd files: {e}[/red]")
    else:
        console.print("\n[bold]You can manually create the following files under `~/.config/systemd/user/`:[/bold]")
        console.print(f"\n[bold cyan]1. ostraca-reminders.service[/bold cyan]\n[dim]{service_content}[/dim]")
        console.print(f"\n[bold cyan]2. ostraca-reminders.timer[/bold cyan]\n[dim]{timer_content}[/dim]")


# ─── TODO MCP INTEGRATIONS ───────────────────────────────────────────────────

@mcp.tool()
def list_ostraca_todos(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    all_items: bool = False
) -> str:
    """
    List todo tasks in your personal knowledge base.
    
    Args:
        status: Filter by status ('todo', 'in_progress', 'done').
        priority: Filter by priority ('low', 'medium', 'high').
        all_items: If True, include completed tasks. Defaults to False.
    """
    conditions = []
    params = []

    if status:
        if status not in ("todo", "in_progress", "done"):
            return "Error: Status filter must be 'todo', 'in_progress', or 'done'."
            conditions.append("status = ?")
            params.append(status)
    elif not all_items:
        conditions.append("status != 'done'")

    if priority:
        if priority not in ("low", "medium", "high"):
            return "Error: Priority filter must be 'low', 'medium', or 'high'."
        conditions.append("priority = ?")
        params.append(priority)

    query = "SELECT id, title, description, status, priority, due_date FROM todos"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY due_date IS NULL ASC, due_date ASC, CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END ASC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

    if not rows:
        return "No tasks found matching your filters."

    output = []
    for r in rows:
        tid, title, desc, stat, prio, due = r
        desc_str = f" | Description: {desc}" if desc else ""
        due_str = f" | Due: {due}" if due else ""
        output.append(f"[{tid}] {title} (Status: {stat} | Priority: {prio}{desc_str}{due_str})")

    return "\n".join(output)


@mcp.tool()
def create_ostraca_todo(
    title: str,
    description: Optional[str] = None,
    due: Optional[str] = None,
    priority: str = "medium"
) -> str:
    """
    Create a new task/todo item in your personal knowledge base.
    
    Args:
        title: Title of the task.
        description: Detailed explanation of the task.
        due: Due date (e.g., 'MM-DD-YYYY HH:MM', 'MM-DD-YYYY', 'today', 'tomorrow', '+3d').
        priority: Priority ('low', 'medium', 'high'). Defaults to 'medium'.
    """
    if priority not in ("low", "medium", "high"):
        return "Error: Priority must be 'low', 'medium', or 'high'."

    try:
        parsed_due = parse_due_date(due)
    except ValueError as e:
        return f"Error: {e}"

    todo_id = str(shortuuid.uuid())[:8]

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO todos (id, title, description, status, priority, due_date, reminder_sent) "
                "VALUES (?, ?, ?, 'todo', ?, ?, 0)",
                (todo_id, title, description, priority, parsed_due),
            )
            conn.commit()
        except sqlite3.Error as e:
            return f"Database error: {e}"

    return f"Task '{title}' created successfully with ID {todo_id}."


@mcp.tool()
def complete_ostraca_todo(identifier: str) -> str:
    """
    Mark a todo item as completed by its ID or Title.
    """
    row = get_todo_by_identifier(identifier)
    if not row:
        return f"Error: Task '{identifier}' not found."

    todo_id, title, _, _, _, _, _ = row

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE todos SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (todo_id,),
        )
        conn.commit()

    return f"Task '{title}' ({todo_id}) marked as completed."


if __name__ == "__main__":
    app()
