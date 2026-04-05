"""
demo.py — interactive demo for EditableDataTable.

Run:  python demo.py

Keys
----
  e        edit the Description column of the highlighted row
  p        edit the Priority column of the highlighted row
  F2       edit whatever column the cursor is on (cursor_type=cell only)
  q        quit
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label

from textual_widgets import EditableDataTable

SAMPLE_DATA = [
    ("1", "Buy groceries",           "Home"),
    ("3", "Write quarterly report",  "Work"),
    ("2", "Call dentist",            "Personal"),
    ("5", "Fix kitchen light",       "Home"),
    ("1", "Review pull requests",    "Work"),
    ("4", "Book flights",            "Personal"),
]


class DemoApp(App):
    CSS = """
    Screen {
        layers: base floating;
    }

    #table {
        height: 1fr;
    }

    #table > .datatable--cursor {
        background: #4A443D;
        color: #F4F1E8;
    }

    #_cell_editor {
        layer: floating;
        background: #5E8B87;
        color: #2E2A26;
        border: none transparent;
        height: 1;
        padding: 0 1;
    }

    #status {
        height: 1;
        padding: 0 1;
        color: #6FA7A2;
        background: #3A332C;
    }
    """

    BINDINGS = [
        Binding("e", "edit_desc",     "Edit description"),
        Binding("p", "edit_priority", "Edit priority"),
        Binding("q", "quit",          "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield EditableDataTable(id="table", cursor_type="row", show_row_labels=False)
        yield Label("Select a row then press  e  to edit description,  p  for priority", id="status")
        yield Footer()

    def on_mount(self) -> None:
        tbl = self.query_one("#table", EditableDataTable)
        tbl.add_column("Pri",         key="pri",  width=3)
        tbl.add_column("Description", key="desc", width=40)
        tbl.add_column("Project",     key="proj", width=12)
        tbl.mark_editable("pri", "desc")

        for row in SAMPLE_DATA:
            tbl.add_row(*row)

    def action_edit_desc(self) -> None:
        self.query_one("#table", EditableDataTable).start_edit(column_key="desc")

    def action_edit_priority(self) -> None:
        self.query_one("#table", EditableDataTable).start_edit(column_key="pri")

    def on_editable_data_table_cell_edited(
        self, event: EditableDataTable.CellEdited
    ) -> None:
        col = event.column_key.value if hasattr(event.column_key, "value") else str(event.column_key)
        self.query_one("#status", Label).update(
            f"Saved  [{col}]  '{event.old_value}'  →  '{event.new_value}'"
        )


if __name__ == "__main__":
    DemoApp().run()
