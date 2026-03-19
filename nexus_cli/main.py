"""
Nexus CLI - Personal Knowledge Base enforcing the PARA method.

This module provides the main CLI entry point using Typer and exposes
MCP (Model Context Protocol) tools for AI agents to interact with the notes.
"""

import os
import re
import sqlite3
import subprocess
import tempfile
from typing import List, Optional, Tuple

import shortuuid
import typer
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from nexus_cli.db import get_db, init_db, PARA_CATEGORIES
from nexus_cli.frontmatter import extract_frontmatter
from nexus_cli.tui import NexusListApp

# Initialize Typer app and FastMCP server
app = typer.Typer(
    help="Nexus CLI - A terminal-based personal knowledge base enforcing the PARA method.",
    add_completion=True,
)
mcp = FastMCP("Nexus")
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
                       snippet(notes_fts, -1, '[bold yellow]', '[/bold yellow]', '...', 20)
                FROM notes_fts
                JOIN notes n ON notes_fts.rowid = n.rowid
                WHERE notes_fts MATCH ? AND n.para_category = ?
                ORDER BY rank
            """
            params = (query, category)
        else:
            sql = """
                SELECT n.id, n.title, n.para_category, n.updated_at, n.content,
                       snippet(notes_fts, -1, '[bold yellow]', '[/bold yellow]', '...', 20)
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
                break
            except sqlite3.IntegrityError as e:
                # Handle collision on short ID (extremely rare but possible)
                if ("UNIQUE constraint failed: notes.id" in str(e)
                        and attempt < max_retries - 1):
                    note_id = str(shortuuid.uuid())[:8]
                    continue
                console.print(f"[red]Error saving note: {e}[/red]")
                raise typer.Exit(1) from e
    console.print(f"[green]Note '{final_title}' added successfully.[/green]")


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
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
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
    console.print(
        f"[green]Note '{final_title}' updated successfully.[/green]")


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
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    _, title, content, _, _, _ = row
    edit_content(content)
    console.print(
        f"[red]Opened in read-only mode.[/red] [bold red]No changes saved.[/bold red] "
        f"To make changes run \"nexus edit '{title}'\"."
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
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, content, old_para, _, _ = row
    if old_para == to:
        console.print(f"Note '{title}' is already in {to}.")
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
        console.print(f"[green]Note '{title}' moved to {to}.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]Failed to move note: {e}[/red]")
        raise typer.Exit(1) from e


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
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, _, _, _, _ = row
    if typer.confirm(f"Are you sure you want to delete '{title}'?"):
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
                conn.commit()
            console.print(
                f"[green]Note '{title}' deleted successfully.[/green]")
        except sqlite3.Error as e:
            console.print(f"[red]Failed to delete note: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        console.print("Deletion cancelled.")


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
                f'<context><note id="{note_id}" title="{title}" '
                f'category="{category}" last_updated="{updated_at}">{content}'
                '</note></context>'
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
            table.add_row(note_id, title, category, (snippet or "").replace(
                "\n", " "), str(updated_at))
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
            app_instance = NexusListApp(results)
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
                    console.print("[green]Note deleted successfully.[/green]")
                except sqlite3.Error as e:
                    console.print(f"[red]Failed to delete note: {e}[/red]")
            elif action == "move":
                note_id, target_category = data
                move(note_id, to=target_category)
    else:
        results = get_filtered_notes(para, tags)
        if not results:
            console.print("No notes found matching the criteria.")
            return

        # Render static tree
        tree = Tree("Nexus")
        categories = {}
        for note_id, title, cat, tags_str in results:
            categories.setdefault(cat, []).append((note_id, title, tags_str))

        for cat in PARA_CATEGORIES:
            if cat in categories:
                cat_node = tree.add(f"[bold cyan]{cat}s[/bold cyan]")
                for note_id, title, tags_str in sorted(categories[cat], key=lambda x: x[1].lower()):
                    node_text = f"[dim white]{note_id}[/dim white] | [green]{title}[/green]"
                    if tags_str:
                        formatted_tags = ", ".join(
                            t.strip() for t in tags_str.split(",") if t.strip())
                        if formatted_tags:
                            node_text += f" [dim]({formatted_tags})[/dim]"
                    cat_node.add(node_text)
        console.print(tree)


@mcp.tool()
def search_nexus_notes(query: str, category: Optional[str] = None) -> str:
    """
    Search your personal knowledge base using FTS5.

    This tool is intended for AI agents to retrieve context.
    """
    try:
        results = perform_search(query, category)
        out = [
            f'<context><note id="{r[0]}" title="{r[1]}" category="{r[2]}" '
            f'last_updated="{r[3]}">{r[4]}</note></context>'
            for r in results
        ]
        return "\n".join(out) if out else "No notes found."
    except sqlite3.OperationalError:
        return "<error>Malformed search query</error>"


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
        f'<context><note id="{note_id}" title="{title}" category="{category}" '
        f'last_updated="{updated_at}">{content}</note></context>'
    )


@app.command()
def mcp_start() -> None:
    """
    Start the FastMCP server for AI agent integration.

    Uses standard input/output (stdio) for communication.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
