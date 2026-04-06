"""
textual_widgets — a collection of reusable Textual widgets.

Available widgets
-----------------
EditableDataTable
    A DataTable subclass with inline cell editing.

    from textual_widgets import EditableDataTable

DatePicker
    A modal calendar screen.  Push with push_screen_wait and await the result.

    from textual_widgets import DatePicker
    date = await self.app.push_screen_wait(DatePicker())
    date = await self.app.push_screen_wait(DatePicker(initial="2026-04-15"))
    # Returns "YYYY-MM-DD" or None if cancelled.
"""

from textual_widgets.editable_table import EditableDataTable
from textual_widgets.date_picker import CalendarView, DatePicker

__all__ = ["EditableDataTable", "CalendarView", "DatePicker"]
