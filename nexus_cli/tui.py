from typing import List, Optional, Tuple, Any
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Tree, Header, Footer, Static, Label, Select, Button, OptionList
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual import on

from nexus_cli.db import PARA_CATEGORIES
from nexus_cli.config import get_preference, set_preference


class MoveCategoryScreen(ModalScreen[str]):
    """A modal screen for selecting a new PARA category."""

    def __init__(self, current_category: str):
        super().__init__()
        self.current_category = current_category

    def compose(self) -> ComposeResult:
        options = [
            Option(cat, id=cat) for cat in PARA_CATEGORIES
        ]
        yield Vertical(
            Label("Select target PARA category:"),
            OptionList(*options, id="category_list"),
            Horizontal(
                Static("Enter to Confirm | Escape to Cancel", id="help_text"),
                classes="footer"
            ),
            id="modal_dialog"
        )

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id:
            self.dismiss(str(event.option_id))

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_down(self) -> None:
        self.query_one(OptionList).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(OptionList).action_cursor_up()

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]


class DeleteConfirmationScreen(ModalScreen[bool]):
    """A modal screen for confirming note deletion."""

    def __init__(self, note_title: str):
        super().__init__()
        self.note_title = note_title

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Are you sure you want to delete [bold red]'{self.note_title}'[/bold red]?"),
            Horizontal(
                Button("Delete", variant="error", id="confirm"),
                Button("Cancel", variant="primary", id="cancel"),
                classes="modal_buttons"
            ),
            id="modal_dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def action_cancel(self) -> None:
        self.dismiss(False)


class NexusListApp(App[Optional[Tuple[str, Any]]]):
    """An interactive TUI for browsing and acting on Nexus notes."""

    TITLE = "Nexus CLI - PARA Navigator"
    CSS = """
    Screen {
        background: $surface;
    }

    MoveCategoryScreen, DeleteConfirmationScreen {
        align: center middle;
    }

    #modal_dialog {
        padding: 1 2;
        background: $panel;
        border: thick $primary;
        width: 60;
        height: auto;
    }

    .modal_buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }

    .modal_buttons Button {
        margin: 0 1;
    }

    .footer {
        margin-top: 1;
        height: 1;
        content-align: center middle;
    }

    #help_text {
        color: $text-disabled;
    }

    #category_list {
        height: 6;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("o", "open_note", "Open", show=True),
        Binding("e", "edit_note", "Edit", show=True),
        Binding("m", "move_note", "Move", show=True),
        Binding("d", "delete_note", "Delete", show=True),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("h", "collapse_node", "Collapse", show=False),
        Binding("l", "expand_node", "Expand", show=False),
        Binding("enter", "select_node", "Select", show=False),
    ]

    def action_cursor_down(self) -> None:
        self.query_one(Tree).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(Tree).action_cursor_up()

    def action_expand_node(self) -> None:
        node = self.query_one(Tree).cursor_node
        if node:
            node.expand()

    def action_collapse_node(self) -> None:
        node = self.query_one(Tree).cursor_node
        if node:
            node.collapse()

    def __init__(self, results: List[Tuple]):
        super().__init__()
        self.results = results
        self.theme = get_preference("theme")

    def watch_theme(self, theme: str) -> None:
        """Watch for theme changes and persist them to config."""
        set_preference("theme", theme)

    def compose(self) -> ComposeResult:
        yield Header()
        tree: Tree[Optional[str]] = Tree("Nexus", id="notes_tree")
        tree.root.expand()

        categories = {}
        for note_id, title, cat, tags_str in self.results:
            categories.setdefault(cat, []).append((note_id, title, tags_str))

        for cat in PARA_CATEGORIES:
            if cat in categories:
                cat_node = tree.root.add(f"[bold cyan]{cat}s[/bold cyan]", expand=True, data=None)
                for note_id, title, tags_str in sorted(categories[cat], key=lambda x: x[1].lower()):
                    node_text = Text.assemble(
                        (note_id, "dim white"),
                        " | ",
                        (title, "green")
                    )
                    if tags_str:
                        formatted_tags = ", ".join(
                            t.strip() for t in tags_str.split(",") if t.strip())
                        if formatted_tags:
                            node_text.append(f" ({formatted_tags})", style="dim")
                    cat_node.add_leaf(node_text, data=note_id)

        yield tree
        yield Footer()

    def action_open_note(self) -> None:
        tree = self.query_one(Tree)
        node = tree.cursor_node
        if node and node.data:
            self.exit(("open", node.data))

    def action_edit_note(self) -> None:
        tree = self.query_one(Tree)
        node = tree.cursor_node
        if node and node.data:
            self.exit(("edit", node.data))

    def action_delete_note(self) -> None:
        tree = self.query_one(Tree)
        node = tree.cursor_node
        if node and node.data:
            note_id = node.data
            note_title = "Unknown Note"
            for nid, title, _, _ in self.results:
                if nid == note_id:
                    note_title = title
                    break

            def check_delete(confirmed: bool) -> None:
                if confirmed:
                    self.exit(("delete", note_id))

            self.push_screen(DeleteConfirmationScreen(note_title), check_delete)

    async def action_move_note(self) -> None:
        tree = self.query_one(Tree)
        node = tree.cursor_node
        if node and node.data:
            note_id = node.data
            # We need to find the current category to pre-select it
            current_cat = "Project"  # Default fallback
            for nid, title, cat, _ in self.results:
                if nid == note_id:
                    current_cat = cat
                    break
            
            def check_move(target_category: Optional[str]) -> None:
                if target_category and target_category != current_cat:
                    self.exit(("move", (note_id, target_category)))

            self.push_screen(MoveCategoryScreen(current_cat), check_move)

    def action_select_node(self) -> None:
        self.action_edit_note()

    def action_quit(self) -> None:
        self.exit(None)
