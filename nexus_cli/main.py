"""
Nexus CLI - Personal Knowledge Base enforcing the PARA method.
"""

import os
import re
import sqlite3
import subprocess
import tempfile
import shortuuid
from typing import List, Optional

import typer
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from nexus_cli.db import get_db, init_db
from nexus_cli.frontmatter import extract_frontmatter

app = typer.Typer(help="Nexus CLI - Personal Knowledge Base")
mcp = FastMCP("Nexus")
console = Console()

# Run DB initialization when the application starts
try:
    init_db()
except sqlite3.Error as e:
    console.print(f"[red]Failed to initialize database: {e}[/red]")
    raise typer.Exit(1) from e


def get_editor() -> str:
    """Get the preferred editor from the environment or fallback to vim."""
    return os.environ.get("EDITOR", "vim")


def format_yaml_frontmatter(title: str, category: str, tags: List[str]) -> str:
    """Format title, category and tags into standard YAML frontmatter."""
    # Escape double quotes in title
    safe_title = title.replace('"', '\\"')
    tags_str = ", ".join(f'"{t}"' for t in tags)
    return f'---\ntitle: "{safe_title}"\npara: {category}\ntags: [{tags_str}]\n---\n\n'


@app.command()
def add(
    title: str,
    para: str = typer.Option(
        ..., help="PARA category: Project, Area, Resource, Archive"
    ),
) -> None:
    """Add a new note."""
    if para not in ["Project", "Area", "Resource", "Archive"]:
        console.print(
            "[red]Error: Category must be Project, Area, Resource, or Archive.[/red]"
        )
        raise typer.Exit(1)

    note_id = str(shortuuid.uuid())[:8]
    initial_content = format_yaml_frontmatter(title, para, [])

    fd, tmp_path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(initial_content)

        editor = get_editor()
        try:
            subprocess.run([editor, tmp_path], check=False)
        except FileNotFoundError as exc:
            console.print(f"[red]Error: Editor '{editor}' not found.[/red]")
            raise typer.Exit(1) from exc

        with open(tmp_path, "r", encoding="utf-8") as f:
            edited_content = f.read()

        metadata, _ = extract_frontmatter(edited_content)
        if not metadata:
            console.print("[red]Error: Invalid frontmatter. Note not saved.[/red]")
            raise typer.Exit(1)

        final_title = metadata.get("title", title)
        final_para = metadata.get("para", para)

        if final_para not in ["Project", "Area", "Resource", "Archive"]:
            console.print(
                "[yellow]Warning: Invalid category in frontmatter. Defaulting to provided category.[/yellow]"
            )
            final_para = para

        final_tags = ",".join(metadata.get("tags", []))

        with get_db() as conn:
            cursor = conn.cursor()
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    cursor.execute(
                        "INSERT INTO notes (id, title, content, para_category, tags) VALUES (?, ?, ?, ?, ?)",
                        (note_id, final_title, edited_content, final_para, final_tags),
                    )
                    conn.commit()
                    break
                except sqlite3.IntegrityError as e:
                    if "UNIQUE constraint failed: notes.id" in str(e) and attempt < max_retries - 1:
                        note_id = str(shortuuid.uuid())[:8]
                        continue
                    console.print(f"[red]Error saving note: {e}[/red]")
                    raise typer.Exit(1) from e
        console.print(f"[green]Note '{final_title}' added successfully.[/green]")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.command()
def edit(identifier: str) -> None:
    """Edit an existing note by ID or Title."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content FROM notes WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        row = cursor.fetchone()

    if not row:
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, old_title, old_content = row

    fd, tmp_path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(old_content)

        editor = get_editor()
        try:
            subprocess.run([editor, tmp_path], check=False)
        except FileNotFoundError as exc:
            console.print(f"[red]Error: Editor '{editor}' not found.[/red]")
            raise typer.Exit(1) from exc

        with open(tmp_path, "r", encoding="utf-8") as f:
            new_content = f.read()

        if new_content == old_content:
            console.print("No changes made.")
            return

        metadata, _ = extract_frontmatter(new_content)
        if not metadata:
            console.print("[red]Error: Invalid frontmatter format. Changes not saved.[/red]")
            return

        final_title = metadata.get("title", old_title)
        final_para = metadata.get("para")

        final_tags = ",".join(metadata.get("tags", []))

        with get_db() as conn:
            cursor = conn.cursor()
            if final_para and final_para in ["Project", "Area", "Resource", "Archive"]:
                cursor.execute(
                    "UPDATE notes SET title = ?, content = ?, para_category = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (final_title, new_content, final_para, final_tags, note_id),
                )
            else:
                cursor.execute(
                    "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (final_title, new_content, final_tags, note_id),
                )
            conn.commit()
        console.print(f"[green]Note '{final_title}' updated successfully.[/green]")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.command(name="open")
def open_note(identifier: str) -> None:
    """Open a note in read-only mode."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content FROM notes WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        row = cursor.fetchone()

    if not row:
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, content = row

    fd, tmp_path = tempfile.mkstemp(suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        editor = get_editor()
        try:
            subprocess.run([editor, tmp_path], check=False)
        except FileNotFoundError as exc:
            console.print(f"[red]Error: Editor '{editor}' not found.[/red]")
            raise typer.Exit(1) from exc

        console.print(
            f"[red]Opened in read-only mode.[/red] [bold red]No changes saved.[/bold red] To make changes run \"nexus edit '{title}'\"."
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.command()
def move(
    identifier: str, to: str = typer.Option(..., help="New PARA category")
) -> None:
    """Move a note to a different PARA category."""
    if to not in ["Project", "Area", "Resource", "Archive"]:
        console.print(
            "[red]Error: Category must be Project, Area, Resource, or Archive.[/red]"
        )
        raise typer.Exit(1)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content FROM notes WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        row = cursor.fetchone()

    if not row:
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title, content = row

    # Safer move: Parse and reconstruct frontmatter
    metadata, body = extract_frontmatter(content)
    if not metadata:
        # Fallback to regex if parsing fails for some reason
        console.print("[yellow]Warning: Could not parse frontmatter robustly. Falling back to regex replacement.[/yellow]")
        new_content = re.sub(r"^(para:\s*).+$", rf"\g<1>{to}", content, flags=re.MULTILINE)
    else:
        metadata["para"] = to
        # Reconstruct YAML block
        yaml_lines = ["---"]
        for k, v in metadata.items():
            if k == "tags" and isinstance(v, list):
                v_str = "[" + ", ".join(f'"{t}"' for t in v) + "]"
                yaml_lines.append(f"{k}: {v_str}")
            else:
                # Escape quotes in values if they are strings
                if isinstance(v, str):
                    v_safe = v.replace('"', '\\"')
                    yaml_lines.append(f'{k}: "{v_safe}"')
                else:
                    yaml_lines.append(f"{k}: {v}")
        yaml_lines.append("---")
        new_content = "\n".join(yaml_lines) + "\n\n" + body

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET content = ?, para_category = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_content, to, note_id),
            )
            conn.commit()
        console.print(f"[green]Note '{title}' moved to {to}.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]Failed to move note: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def delete(identifier: str) -> None:
    """Delete a note by ID or Title."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title FROM notes WHERE id = ? OR title = ?",
            (identifier, identifier),
        )
        row = cursor.fetchone()

    if not row:
        console.print(f"[red]Error: Note '{identifier}' not found.[/red]")
        raise typer.Exit(1)

    note_id, title = row
    confirm = typer.confirm(f"Are you sure you want to delete '{title}'?")
    if not confirm:
        console.print("Deletion cancelled.")
        return

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
        console.print(f"[green]Note '{title}' deleted successfully.[/green]")
    except sqlite3.Error as e:
        console.print(f"[red]Failed to delete note: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def search(
    query: str,
    para: Optional[str] = typer.Option(None, help="Filter by PARA category"),
    raw: bool = typer.Option(False, "--raw", help="Output raw XML"),
) -> None:
    """Search for notes."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            if para:
                sql = """
                    SELECT n.id, n.title, n.para_category, n.updated_at, n.content,
                           snippet(notes_fts, -1, '[bold yellow]', '[/bold yellow]', '...', 20)
                    FROM notes_fts
                    JOIN notes n ON notes_fts.rowid = n.rowid
                    WHERE notes_fts MATCH ? AND n.para_category = ?
                    ORDER BY rank
                """
                params = (query, para)
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
            results = cursor.fetchall()

    except sqlite3.OperationalError as exc:
        if raw:
            print("<error>Malformed search query</error>")
        else:
            console.print("[red]Error: Malformed search query.[/red]")
        raise typer.Exit(1) from exc

    if raw:
        xml_output = []
        for note_id, title, category, updated_at, content, snippet in results:
            xml_output.append(
                f'<context><note id="{note_id}" title="{title}" category="{category}" last_updated="{updated_at}">{content}</note></context>'
            )
        print("\n".join(xml_output))
    else:
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("ID", style="dim white")
        table.add_column("Title", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Snippet", style="white")
        table.add_column("Last Updated", style="green")

        for note_id, title, category, updated_at, content, snippet in results:
            # Replace literal newlines in snippet to keep table clean
            clean_snippet = (snippet or "").replace("\n", " ")
            table.add_row(note_id, title, category, clean_snippet, str(updated_at))

        console.print(table)


@app.command(name="list")
def list_notes(
    para: Optional[str] = typer.Option(None, help="Filter by PARA category"),
    tags: Optional[str] = typer.Option(None, help="Filter by comma-separated tags"),
) -> None:
    """List notes in a directory tree format."""
    if para and para not in ["Project", "Area", "Resource", "Archive"]:
        console.print(
            "[red]Error: Category must be Project, Area, Resource, or Archive.[/red]"
        )
        raise typer.Exit(1)

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
        filtered_results = []
        for note_id, title, cat, tags_str in results:
            note_tags = [
                t.strip().lower() for t in (tags_str or "").split(",") if t.strip()
            ]
            if any(ft in note_tags for ft in filter_tags):
                filtered_results.append((note_id, title, cat, tags_str))
        results = filtered_results

    if not results:
        console.print("No notes found matching the criteria.")
        return

    tree = Tree("Nexus")

    categories = {}
    for note_id, title, cat, tags_str in results:
        categories.setdefault(cat, []).append((note_id, title, tags_str))

    for cat in ["Project", "Area", "Resource", "Archive"]:
        if cat in categories:
            cat_display = f"[bold cyan]{cat}s[/bold cyan]"
            cat_node = tree.add(cat_display)
            for (
                note_id,
                title,
                tags_str,
            ) in sorted(categories[cat], key=lambda x: x[1].lower()):
                node_text = f"[dim white]{note_id}[/dim white] | [green]{title}[/green]"
                if tags_str:
                    formatted_tags = ", ".join(
                        t.strip() for t in tags_str.split(",") if t.strip()
                    )
                    if formatted_tags:
                        node_text += f" [dim]({formatted_tags})[/dim]"
                cat_node.add(node_text)

    console.print(tree)


@mcp.tool()
def search_nexus_notes(query: str, category: Optional[str] = None) -> str:
    """Search notes using FTS5."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if category:
                sql = """
                    SELECT n.id, n.title, n.para_category, n.updated_at, n.content 
                    FROM notes_fts f
                    JOIN notes n ON f.rowid = n.rowid
                    WHERE notes_fts MATCH ? AND n.para_category = ?
                    ORDER BY rank
                """
                params = (query, category)
            else:
                sql = """
                    SELECT n.id, n.title, n.para_category, n.updated_at, n.content 
                    FROM notes_fts f
                    JOIN notes n ON f.rowid = n.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY rank
                """
                params = (query,)

            cursor.execute(sql, params)
            results = cursor.fetchall()

            out = []
            for note_id, title, cat, updated_at, content in results:
                out.append(
                    f'<context><note id="{note_id}" title="{title}" category="{cat}" last_updated="{updated_at}">{content}</note></context>'
                )
            return "\n".join(out) if out else "No notes found."

    except sqlite3.OperationalError:
        return "<error>Malformed search query</error>"


@mcp.tool()
def get_project_context(project_name: str) -> str:
    """Get context for a specific project."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, para_category, updated_at, content FROM notes WHERE title = ? AND para_category = 'Project'",
            (project_name,),
        )
        row = cursor.fetchone()

    if not row:
        return f"Project '{project_name}' not found."

    note_id, title, category, updated_at, content = row
    return f'<context><note id="{note_id}" title="{title}" category="{category}" last_updated="{updated_at}">{content}</note></context>'


@app.command()
def mcp_start() -> None:
    """Start the FastMCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    app()
