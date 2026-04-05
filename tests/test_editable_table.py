"""
Tests for EditableDataTable.

Run from the project root:
    pytest tests/ -v
    pytest tests/test_editable_table.py -v     # this file only
"""

import pytest
from rich.text import Text as RichText
from textual.app import App, ComposeResult

from textual_widgets import EditableDataTable
from textual_widgets.editable_table import _key_str


# ---------------------------------------------------------------------------
# Shared fixture app
# ---------------------------------------------------------------------------

class _TableApp(App):
    """Minimal app used by most tests: three columns, two editable."""
    CSS = "Screen { layers: base floating; } #_cell_editor { border: none transparent; height: 1; }"

    def compose(self) -> ComposeResult:
        yield EditableDataTable(id="t", cursor_type="row", show_row_labels=False)

    def on_mount(self) -> None:
        t = self.query_one("#t", EditableDataTable)
        t.add_column("Priority",    key="pri",  width=3)
        t.add_column("Description", key="desc", width=30)
        t.add_column("Project",     key="proj", width=12)
        t.mark_editable("pri", "desc")
        t.add_row("1", "Buy groceries",  "Home",     key="r1")
        t.add_row("3", "Write report",   "Work",     key="r2")
        t.add_row("2", "Call dentist",   "Personal", key="r3")


class _RichTableApp(App):
    """Same structure but rows use Rich Text cells (mirrors consoleDo usage)."""
    CSS = "Screen { layers: base floating; } #_cell_editor { border: none transparent; height: 1; }"

    def compose(self) -> ComposeResult:
        yield EditableDataTable(id="t", cursor_type="row", show_row_labels=False)

    def on_mount(self) -> None:
        t = self.query_one("#t", EditableDataTable)
        t.add_column("Priority",    key="pri",  width=3)
        t.add_column("Description", key="desc", width=30)
        t.add_column("Project",     key="proj", width=12)
        t.mark_editable("pri", "desc")
        t.add_row(
            RichText("1", style="#FF6B6B"),
            RichText("Buy groceries",  style="#E1D4C0"),
            RichText("Home",           style="dim"),
            key="r1",
        )
        t.add_row(
            RichText("3", style="#E1D4C0"),
            RichText("Write report",   style="#E1D4C0"),
            RichText("Work",           style="dim"),
            key="r2",
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _open_editor(pilot, tbl: EditableDataTable, column_key: str) -> None:
    """Wait for layout to settle, start editing, wait for mount."""
    await pilot.pause()
    tbl.start_edit(column_key=column_key)
    await pilot.pause()


# ---------------------------------------------------------------------------
# Unit tests — _key_str helper
# ---------------------------------------------------------------------------

class TestKeyStr:
    def test_plain_string(self):
        assert _key_str("hello") == "hello"

    def test_str_subclass(self):
        class _StrKey(str):
            pass
        assert _key_str(_StrKey("desc")) == "desc"

    def test_dataclass_style(self):
        """Simulate modern Textual ColumnKey with a .value attribute."""
        class _Key:
            def __init__(self, v):
                self.value = v
            def __str__(self):
                return f"ColumnKey(value='{self.value}')"
        assert _key_str(_Key("desc")) == "desc"

    def test_none_value_falls_back_to_str(self):
        class _Key:
            value = None
            def __str__(self):
                return "raw"
        assert _key_str(_Key()) == "raw"


# ---------------------------------------------------------------------------
# EditableDataTable — editor lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_editor_opens_with_correct_prefill_plain():
    """Plain-string cells: editor opens pre-filled with the cell value."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        assert app.screen.query_one("#_cell_editor").value == "Buy groceries"


@pytest.mark.asyncio
async def test_editor_opens_with_correct_prefill_rich_text():
    """Rich Text cells: plain value is correctly extracted for the editor."""
    app = _RichTableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        assert app.screen.query_one("#_cell_editor").value == "Buy groceries"


@pytest.mark.asyncio
async def test_editor_opens_for_priority():
    """start_edit on 'pri' pre-fills with the priority value."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "pri")
        assert app.screen.query_one("#_cell_editor").value == "1"


@pytest.mark.asyncio
async def test_editor_content_area_is_visible():
    """The editor must have a non-zero content height (border bug regression)."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        editor = app.screen.query_one("#_cell_editor")
        assert editor.content_size.height > 0, (
            "content_size.height is 0 — likely caused by a border consuming the "
            "full height. Add 'border: none transparent' to #_cell_editor CSS."
        )


# ---------------------------------------------------------------------------
# EditableDataTable — commit / cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_commit_posts_cell_edited_message():
    """Enter commits: CellEdited posted with correct old/new values."""
    captured = []

    class _App(_TableApp):
        def on_editable_data_table_cell_edited(self, event):
            captured.append(event)

    app = _App()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        app.screen.query_one("#_cell_editor").value = "Pick up prescriptions"
        await pilot.press("enter")
        await pilot.pause()

        assert len(captured) == 1
        assert captured[0].old_value == "Buy groceries"
        assert captured[0].new_value == "Pick up prescriptions"


@pytest.mark.asyncio
async def test_commit_removes_editor():
    """Editor widget is removed from the screen after committing."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        await pilot.press("enter")
        await pilot.pause()
        assert not app.screen.query("#_cell_editor")


@pytest.mark.asyncio
async def test_identical_value_does_not_post_message():
    """Committing the same value as the original emits no CellEdited message."""
    captured = []

    class _App(_TableApp):
        def on_editable_data_table_cell_edited(self, event):
            captured.append(event)

    app = _App()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        # Don't change the value, just press Enter
        await pilot.press("enter")
        await pilot.pause()
        assert len(captured) == 0


@pytest.mark.asyncio
async def test_escape_cancels_no_message():
    """Escape: no CellEdited posted, editor removed."""
    captured = []

    class _App(_TableApp):
        def on_editable_data_table_cell_edited(self, event):
            captured.append(event)

    app = _App()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        app.screen.query_one("#_cell_editor").value = "Something different"
        await pilot.press("escape")
        await pilot.pause()

        assert len(captured) == 0
        assert not app.screen.query("#_cell_editor")


@pytest.mark.asyncio
async def test_escape_restores_original_cell():
    """After escape the cell displays its original value, not the edited one."""
    from textual.coordinate import Coordinate

    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        app.screen.query_one("#_cell_editor").value = "Changed"
        await pilot.press("escape")
        await pilot.pause()

        cell = tbl.get_cell_at(Coordinate(0, 1))
        plain = cell.plain if hasattr(cell, "plain") else str(cell)
        assert plain == "Buy groceries"


# ---------------------------------------------------------------------------
# EditableDataTable — editability rules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_editable_column_does_not_open_editor():
    """start_edit on a column not in mark_editable does nothing."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "proj")
        assert not app.screen.query("#_cell_editor")
        assert not tbl._editing


@pytest.mark.asyncio
async def test_second_start_edit_ignored_while_editing():
    """A second start_edit while one is active is a no-op."""
    app = _TableApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "desc")
        tbl.start_edit(column_key="pri")
        await pilot.pause()
        assert len(app.screen.query("#_cell_editor")) == 1


@pytest.mark.asyncio
async def test_empty_table_no_crash():
    """start_edit on an empty table exits silently without error."""
    class _EmptyApp(App):
        CSS = "Screen { layers: base floating; }"
        def compose(self):
            yield EditableDataTable(id="t", show_row_labels=False)
        def on_mount(self):
            t = self.query_one("#t", EditableDataTable)
            t.add_column("Name", key="name")
            t.mark_editable("name")

    app = _EmptyApp()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        tbl.start_edit(column_key="name")
        await pilot.pause()
        assert not app.screen.query("#_cell_editor")


# ---------------------------------------------------------------------------
# EditableDataTable — navigation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_second_row_prefill():
    """After navigating down one row the editor shows that row's value."""
    app = _TableApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")
        await _open_editor(pilot, app.query_one("#t", EditableDataTable), "desc")
        assert app.screen.query_one("#_cell_editor").value == "Write report"


@pytest.mark.asyncio
async def test_row_cursor_type_targets_correct_column():
    """With cursor_type='row', start_edit(column_key=) targets the right column."""
    captured = []

    class _App(_TableApp):
        def on_editable_data_table_cell_edited(self, event):
            captured.append(event)

    app = _App()
    async with app.run_test() as pilot:
        tbl = app.query_one("#t", EditableDataTable)
        await _open_editor(pilot, tbl, "pri")   # target priority, not desc
        app.screen.query_one("#_cell_editor").value = "9"
        await pilot.press("enter")
        await pilot.pause()

        assert len(captured) == 1
        col = _key_str(captured[0].column_key)
        assert col == "pri", f"expected 'pri', got '{col}'"
        assert captured[0].new_value == "9"
