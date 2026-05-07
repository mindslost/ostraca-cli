"""
Ostraca CLI - Personal Knowledge Base enforcing the PARA method.

This module provides the main CLI entry point using Typer and exposes
MCP (Model Context Protocol) tools for AI agents to interact with the notes.
"""

import os
import re
import sqlite3
import subprocess
import tempfile
import html
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

from ostraca_cli.db import (
    get_db,
    init_db,
    backup_db,
    restore_db,
    prune_backups,
    PARA_CATEGORIES,
)
from ostraca_cli.frontmatter import extract_frontmatter
from ostraca_cli.tui import OstracaListApp

# Initialize Typer app and FastMCP server
app = typer.Typer(
    help="Ostraca CLI - A terminal-based personal knowledge base enforcing the PARA method.",
    add_completion=True,
)
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
    return (
        f"---\ntitle: \"{safe_title}\"\npara: {category}\n"
        f"tags: [{tags_str}]\n---\n\n"
    )


def get_note_by_identifier(identifier: str) -> Optional[Tuple[str, str, str, str, str, str]]:
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
    with get_db() as conn:
        cursor = conn.cursor()
        # Fetch all IDs and titles to filter in Python for simplicity and flexibility
        cursor.execute("SELECT id, title FROM notes")
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
        try:
            # Run the editor; check=False because we handle exit codes if needed later
            subprocess.run([editor, tmp_path], check=False)
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
    para: str = typer.Option(
        ..., help=f"PARA category: {', '.join(PARA_CATEGORIES)}"
    ),
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
                    (note_id, final_title, edited_content,
                     final_para, final_tags),
                )
                conn.commit()
                backup_db()
                break
            except sqlite3.IntegrityError as e:
                # Handle collision on short ID (extremely rare but possible)
                if ("UNIQUE constraint failed: notes.id" in str(e)
                        and attempt < max_retries - 1):
                    note_id = str(shortuuid.uuid())[:8]
                    continue
                console.print(f"[red]Error saving note: {escape(str(e))}[/red]")
                raise typer.Exit(1) from e
    console.print(f"[green]Note '{escape(final_title)}' added successfully.[/green]")


@app.command()
def edit(
    identifier: str = typer.Argument(..., autocompletion=complete_note_identifier, help="ID or Title of the note to edit")
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
            "[red]Error: Invalid frontmatter format. Changes not saved.[/red]")
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
        backup_db()
    console.print(
        f"[green]Note '{escape(final_title)}' updated successfully.[/green]")


@app.command(name="open")
def open_note(
    identifier: str = typer.Argument(..., autocompletion=complete_note_identifier, help="ID or Title of the note to open")
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
    identifier: str = typer.Argument(..., autocompletion=complete_note_identifier, help="ID or Title of the note to move"),
    to: str = typer.Option(..., help="Target PARA category")
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
            r"^(para:\s*).+$", rf"\g<1>{to}", content, flags=re.MULTILINE)
    else:
        metadata["para"] = to
        tags = metadata.get("tags", [])
        new_content = format_yaml_frontmatter(
            metadata.get("title", title), to, tags) + body

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET content = ?, para_category = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_content, to, note_id),
            )
            conn.commit()
            backup_db()
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
                console.print(
                    f"[yellow]Pruned {len(deleted)} old backup(s).[/yellow]"
                )
    except Exception as e:
        console.print(f"[red]Error creating backup: {escape(str(e))}[/red]")
        raise typer.Exit(1)


@app.command()
def restore(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the backup file to restore"
    )
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
    identifier: str = typer.Argument(..., autocompletion=complete_note_identifier, help="ID or Title of the note to delete")
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
                backup_db()
            console.print(
                f"[green]Note '{escape(title)}' deleted successfully.[/green]")
        except sqlite3.Error as e:
            console.print(f"[red]Failed to delete note: {escape(str(e))}[/red]")
            raise typer.Exit(1) from e
    else:
        console.print("Deletion cancelled.")


@app.command()
def export(
    identifier: str = typer.Argument(..., autocompletion=complete_note_identifier, help="ID or Title of the note to export"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Destination path or directory (defaults to home folder)"),
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
        console.print(f"[green]Note '{escape(title)}' exported to '{output_path}'.[/green]")
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
                f'{html.escape(content)}</note></context>'
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


def get_filtered_notes(
    para: Optional[str],
    tags: Optional[str]
) -> List[Tuple]:
    """Fetch and filter notes based on PARA category and tags."""
    with get_db() as conn:
        cursor = conn.cursor()
        query_sql = "SELECT id, title, para_category, tags FROM notes"
        params = ()
        if para:
            query_sql += " WHERE para_category = ?"
            params = (para,)
        cursor.execute(query_sql, params)
        results = cursor.fetchall()

    if tags:
        filter_tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
        results = [
            r for r in results
            if any(ft in [t.strip().lower() for t in (r[3] or "").split(",") if t.strip()]
                   for ft in filter_tags)
        ]
    return results


@app.command(name="list")
def list_notes(
    para: Optional[str] = typer.Option(None, help="Filter by PARA category"),
    tags: Optional[str] = typer.Option(
        None, help="Filter by comma-separated tags"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Launch interactive selection TUI"
    ),
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

    if interactive:
        while True:
            results = get_filtered_notes(para, tags)
            if not results:
                console.print("No notes found matching the criteria.")
                break

            # Launch the interactive TUI
            app_instance = OstracaListApp(results)
            result = app_instance.run()

            if not result:
                break

            action, data = result
            if action == "open":
                open_note(data)
            elif action == "edit":
                edit(data)
            elif action == "delete":
                # We bypass the standard 'delete' confirmation because the TUI already did it
                try:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM notes WHERE id = ?", (data,))
                        conn.commit()
                        backup_db()
                    console.print("[green]Note deleted successfully.[/green]")
                except sqlite3.Error as e:
                    console.print(f"[red]Failed to delete note: {e}[/red]")
            elif action == "move":
                note_id, target_category = data
                move(note_id, to=target_category)
                # move() already calls backup_db()
    else:
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
                for note_id, title, tags_str in sorted(categories[cat], key=lambda x: x[1].lower()):
                    node_text = f"[dim white]{escape(note_id)}[/dim white] | [green]{escape(title)}[/green]"
                    if tags_str:
                        formatted_tags = ", ".join(
                            t.strip() for t in tags_str.split(",") if t.strip())
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
            f'{html.escape(r[4])}</note></context>'
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
    if not row or row[3] != 'Project':
        return f"Project '{project_name}' not found."

    note_id, title, content, category, _, updated_at = row
    return (
        f'<context><note id="{html.escape(note_id)}" title="{html.escape(title)}" '
        f'category="{html.escape(category)}" last_updated="{html.escape(str(updated_at))}">'
        f'{html.escape(content)}</note></context>'
    )


@mcp.tool()
def create_ostraca_note(title: str, para: str, content: str, tags: Optional[List[str]] = None) -> str:
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
                    (note_id, final_title, full_content,
                     final_para, final_tags),
                )
                conn.commit()
                backup_db()
                return f"Note '{final_title}' created successfully with ID {note_id}."
            except sqlite3.IntegrityError as e:
                # Handle collision on short ID (extremely rare but possible)
                if ("UNIQUE constraint failed: notes.id" in str(e)
                        and attempt < max_retries - 1):
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
        backup_db()
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
        backup_db()

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
        backup_db()

    return f"Content appended to note '{title}'."


@app.command()
def mcp_start() -> None:
    """
    Start the FastMCP server for AI agent integration.

    Uses standard input/output (stdio) for communication.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
