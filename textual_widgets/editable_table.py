"""
EditableDataTable — a Textual DataTable subclass with inline cell editing.

Usage
-----
    from editable_table import EditableDataTable

    table = EditableDataTable(id="my_table", cursor_type="row",
                               show_row_labels=False)
    table.add_column("Name",     key="name")
    table.add_column("Priority", key="priority")
    table.mark_editable("name", "priority")

    # Trigger from an app keybinding — targets the named column:
    table.start_edit(column_key="name")

    # Or bind F2 to edit the cell under the cursor:
    table.start_edit()

    # Handle the result anywhere in the widget tree:
    def on_editable_data_table_cell_edited(
        self, event: EditableDataTable.CellEdited
    ) -> None:
        event.row_key     # RowKey of the edited row
        event.column_key  # ColumnKey of the edited column
        event.old_value   # str — value before edit
        event.new_value   # str — value after edit

CSS requirement
---------------
Add to your app's .tcss so the editor floats above all content:

    Screen {
        layers: base floating;
    }

    #_cell_editor {
        layer: floating;
        border: none transparent;   /* REQUIRED — Input default border eats height */
        height: 1;
        /* background, color, padding as desired */
    }
"""

from __future__ import annotations

from textual import events
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.geometry import Offset
from textual.message import Message
from textual.widgets import DataTable, Input
from rich.text import Text


# ---------------------------------------------------------------------------
# Key helpers — Textual changed ColumnKey/RowKey from str subclasses to
# dataclasses in newer releases.  These helpers work with both forms.
# ---------------------------------------------------------------------------

def _key_str(key) -> str:
    """Return the plain string value of a ColumnKey or RowKey."""
    if hasattr(key, "value") and key.value is not None:
        return str(key.value)
    return str(key)


# ---------------------------------------------------------------------------
# Floating editor widget
# ---------------------------------------------------------------------------

class _CellEditor(Input):
    """
    Single-line Input that floats over the cell being edited.
    Communicates back to EditableDataTable via direct callbacks.
    """

    def __init__(self, prefill: str, on_submit, on_cancel, **kwargs) -> None:
        super().__init__(**kwargs)
        self._prefill   = prefill
        self._on_submit = on_submit
        self._on_cancel = on_cancel

    def on_mount(self) -> None:
        self.value           = self._prefill
        self.cursor_position = len(self._prefill)
        self.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._on_submit(self.value)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self._on_cancel()


# ---------------------------------------------------------------------------
# EditableDataTable
# ---------------------------------------------------------------------------

class EditableDataTable(DataTable):
    """DataTable with inline cell editing.  See module docstring for full usage."""

    BINDINGS = [
        Binding("f2", "start_edit", "Edit cell", show=False),
    ]

    # Rich style applied to a cell while it is the active edit target
    EDITING_STYLE = "bold reverse"

    # ------------------------------------------------------------------
    # Public message
    # ------------------------------------------------------------------

    class CellEdited(Message):
        """Posted when the user commits a cell edit (presses Enter)."""

        def __init__(
            self, row_key, column_key, old_value: str, new_value: str
        ) -> None:
            super().__init__()
            self.row_key    = row_key
            self.column_key = column_key
            self.old_value  = old_value
            self.new_value  = new_value

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._editable:       set  = set()
        self._editing:        bool = False
        self._edit_row_key         = None
        self._edit_col_key         = None
        self._edit_col_idx:   int  = 0
        self._edit_old_val:   str  = ""
        self._edit_old_cell        = None   # original cell content (may be Rich Text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_editable(self, *column_keys: str) -> None:
        """Mark one or more column keys (plain strings) as user-editable."""
        self._editable.update(column_keys)

    def start_edit(self, column_key: str | None = None) -> None:
        """
        Begin editing.

        *column_key* — plain-string key of the column to edit.  Works with
        ``cursor_type="row"`` because the column is resolved by name, not by
        the cursor column position.  When omitted the cursor column is used.

        Exits silently if already editing, no rows exist, or the column is
        not in the editable set.
        """
        if self._editing or not self.row_count:
            return

        coord = self.cursor_coordinate

        # --- resolve row --------------------------------------------------
        rows = list(self.ordered_rows)
        if not rows or coord.row >= len(rows):
            return
        row_key = rows[coord.row].key

        # --- resolve column -----------------------------------------------
        if column_key is not None:
            col_key, col_idx = self._find_col(column_key)
        else:
            cols = list(self.ordered_columns)
            if not cols or coord.column >= len(cols):
                return
            col_key  = cols[coord.column].key
            col_idx  = coord.column

        if col_key is None:
            return

        if self._editable and _key_str(col_key) not in self._editable:
            return

        # --- get current cell content ------------------------------------
        try:
            old_cell = self.get_cell_at(Coordinate(coord.row, col_idx))
            old_val  = old_cell.plain if hasattr(old_cell, "plain") else str(old_cell or "")
        except Exception:
            old_cell = ""
            old_val  = ""

        self._editing       = True
        self._edit_row_key  = row_key
        self._edit_col_key  = col_key
        self._edit_col_idx  = col_idx
        self._edit_old_val  = old_val
        self._edit_old_cell = old_cell

        # Highlight the cell so the user can see which field is active
        self._set_cell_editing_style(row_key, col_key, old_val)
        self._mount_editor(old_val)

    def action_start_edit(self) -> None:
        self.start_edit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_col(self, key_str: str):
        """Return (ColumnKey, index) for the named column, or (None, None)."""
        for idx, col in enumerate(self.ordered_columns):
            if _key_str(col.key) == key_str:
                return col.key, idx
        return None, None

    def _col_render_width(self, col) -> int:
        """Render width of a column: content width + padding on both sides."""
        try:
            return col.get_render_width(self)
        except Exception:
            return col.width + 2 * getattr(self, "cell_padding", 1)

    def _editor_geometry(self) -> tuple[int, int, int] | None:
        """
        Return (x, y, width) in screen coordinates for the active edit cell,
        or None if the row is scrolled out of view.
        """
        r           = self.region
        scroll_rows = int(self.scroll_y)
        visible_row = self.cursor_row - scroll_rows
        header_off  = 1 if self.show_header else 0
        usable      = r.height - header_off

        if not (0 <= visible_row < usable):
            return None

        y = r.y + header_off + visible_row

        # Sum column render widths to find this column's x offset
        x = r.x
        for idx, col in enumerate(self.ordered_columns):
            rw = self._col_render_width(col)
            if idx == self._edit_col_idx:
                return x, y, rw
            x += rw

        return None

    def _set_cell_editing_style(self, row_key, col_key, val: str) -> None:
        """Apply the editing highlight to the cell."""
        try:
            self.update_cell(
                row_key, col_key,
                Text(val, style=self.EDITING_STYLE),
                update_width=False,
            )
        except Exception:
            pass

    def _restore_cell(self) -> None:
        """Restore the original cell content (used on cancel)."""
        try:
            self.update_cell(
                self._edit_row_key,
                self._edit_col_key,
                self._edit_old_cell,
                update_width=False,
            )
        except Exception:
            pass

    def _mount_editor(self, prefill: str) -> None:
        geo = self._editor_geometry()
        if geo is None:
            self._editing = False
            self._restore_cell()
            return

        x, y, w = geo
        editor = _CellEditor(
            prefill   = prefill,
            on_submit = self._commit_edit,
            on_cancel = self._cancel_edit,
            id        = "_cell_editor",
        )
        editor.styles.offset = Offset(x, y)
        editor.styles.width  = w
        editor.styles.height = 1
        try:
            editor.styles.layer = "floating"
        except Exception:
            pass

        self.app.screen.mount(editor)

    def _remove_editor(self) -> None:
        try:
            self.app.screen.query_one("#_cell_editor").remove()
        except Exception:
            pass
        self._editing = False
        self.focus()

    def _commit_edit(self, new_val: str) -> None:
        row_key = self._edit_row_key
        col_key = self._edit_col_key
        old_val = self._edit_old_val

        self._remove_editor()

        # Put plain new value in the cell; the CellEdited handler can
        # re-apply any Rich formatting it needs.
        try:
            self.update_cell(row_key, col_key, new_val, update_width=True)
        except Exception:
            pass

        if new_val != old_val:
            self.post_message(self.CellEdited(row_key, col_key, old_val, new_val))

    def _cancel_edit(self) -> None:
        self._restore_cell()
        self._remove_editor()
