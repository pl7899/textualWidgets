# CLAUDE.md — textualWidgets

## Purpose

A collection of reusable Textual widgets, each independently importable and
tested.  Designed as a personal library to be shared across the monorepo.

## Project layout

```
textualWidgets/
├── textual_widgets/          # importable package
│   ├── __init__.py           # re-exports all public widgets
│   └── editable_table.py     # EditableDataTable
├── demo/
│   └── demo_editable_table.py
├── tests/
│   ├── conftest.py
│   └── test_editable_table.py
└── requirements.txt
```

## Running

```bash
# Interactive demo
python3 demo/demo_editable_table.py

# Full test suite
python3 -m pytest tests/ -v
```

## Importing widgets

```python
# Preferred — top-level package import
from textual_widgets import EditableDataTable

# Or directly from the module
from textual_widgets.editable_table import EditableDataTable
```

## Using in another project

Copy `textual_widgets/` into the project directory, then import as above.
(consoleDo keeps its own copy of `editable_table.py` for self-containment.)

---

## Widgets

### EditableDataTable

A `DataTable` subclass with inline cell editing.

**Key API**

| Call | Effect |
|------|--------|
| `table.mark_editable("col_key", ...)` | Mark columns as editable |
| `table.start_edit(column_key="foo")` | Open editor on named column, current row |
| `table.start_edit()` | Open editor on cursor cell (needs `cursor_type="cell"`) |
| `F2` binding | Same as `start_edit()` |

**Message**: `EditableDataTable.CellEdited`
- `event.row_key` — RowKey of the edited row
- `event.column_key` — ColumnKey of the edited column
- `event.old_value` — value before edit (str)
- `event.new_value` — value after edit (str)

**Required CSS** (add to your app's `.tcss`):
```css
Screen {
    layers: base floating;
}

#_cell_editor {
    layer: floating;
    border: none transparent;   /* required — Input default border collapses height */
    height: 1;
    background: #5E8B87;        /* style as desired */
    color: #2E2A26;
    padding: 0 1;
}
```

**Design notes**
- Works with `cursor_type="row"` — `start_edit(column_key=...)` targets the
  column by name, not by cursor column position.
- `_key_str(key)` handles both str-subclass keys (older Textual) and
  dataclass keys with `.value` (newer Textual).
- Editor is mounted on the Screen (not DataTable) to avoid clipping.
- Callbacks (not messages) used for commit/cancel — no app-level routing needed.
- `border: none transparent` must override Textual's `Input` default
  `border: tall`, which collapses `content_size.height` to 0 at `height: 1`.

---

---

### DatePicker

A modal calendar screen for selecting a date.  Push it with `push_screen` and capture the result via callback.

**Usage**

```python
from textual_widgets import DatePicker

# In an action or event handler:
def action_pick_date(self) -> None:
    self.push_screen(
        DatePicker(initial="2026-04-15"),
        callback=self._on_date_picked,
    )

def _on_date_picked(self, result: str | None) -> None:
    if result:
        # result is "YYYY-MM-DD"
        ...
```

`initial` accepts `"YYYY-MM-DD"` or `None` (defaults to today).  
Returns `"YYYY-MM-DD"` on confirm, `None` on Escape.

**Keyboard**

| Key | Action |
|-----|--------|
| `←` / `→` | Previous / next day |
| `↑` / `↓` | Previous / next week |
| `[` / `]` | Previous / next month (cursor clamped to last day if needed) |
| `Enter` | Confirm selected date |
| `Escape` | Cancel (returns `None`) |

**Mouse** — click any day to confirm it immediately; click the left / right half of the month header to change months.

**Calendar format**
```
<  Apr,2026  >
Wk    Mo    Tu    We    Th    Fr    Sa    Su
13    30    31    1     2     3     4     5
14    6     7     8     9     10    11    12
...
```
Always renders 6 week rows (padded with days from the next month) for a stable height.

**Required CSS** — the `DEFAULT_CSS` embedded in the class covers layout and colours, no external CSS needed.  If you want to re-theme the overlay container, target `DatePicker > Vertical`.

---

## Adding a new widget

1. Create `textual_widgets/<widget_name>.py`
2. Add a public re-export to `textual_widgets/__init__.py`
3. Add `tests/test_<widget_name>.py` following the pattern in
   `tests/test_editable_table.py`:
   - Unit tests for any pure helper functions
   - Integration tests via `App.run_test()` + `Pilot`
   - At least one test that verifies the widget's content is actually visible
     (e.g., check `content_size.height > 0`)

## Projects using this library

| Project | Widgets used |
|---------|-------------|
| `consoleDo/` | EditableDataTable (local copy) |
