"""
CalendarView and DatePicker widgets for Textual.

CalendarView — embeddable calendar widget
------------------------------------------
Can be used inline (composed directly into an app or screen) or inside the
DatePicker modal.  Posts messages when the user confirms or cancels::

    class MyApp(App):
        def compose(self):
            yield CalendarView(id="cal")

        def on_calendar_view_date_selected(self, event):
            print(event.date)   # "YYYY-MM-DD"

        def on_calendar_view_cancelled(self, event):
            pass  # user pressed Escape

    # To activate the calendar from a key binding:
    def action_edit_date(self):
        cal = self.query_one(CalendarView)
        cal.set_date("2026-04-15")   # optional pre-fill
        cal.focus()

DatePicker — modal wrapper
---------------------------
Push with push_screen and a callback::

    self.push_screen(DatePicker(initial="2026-04-15"), callback=self._on_date)

    def _on_date(self, result):
        if result:          # "YYYY-MM-DD" or None
            ...

Calendar display::

    <  Apr,2026  >
    Wk  Mo  Tu  We  Th  Fr  Sa  Su
    13  30  31  1   2   3   4   5
    ...

Keyboard (when CalendarView is focused)
---------------------------------------
- ``←`` / ``→``  — previous / next day
- ``↑`` / ``↓``  — previous / next week
- ``[`` / ``]``  — previous / next month (cursor clamped to last day if needed)
- ``Enter``      — confirm selected date
- ``Escape``     — cancel

Mouse
-----
- Click a day to confirm it immediately.
- Click the left half of the header to go to the previous month.
- Click the right half of the header to go to the next month.
"""

from __future__ import annotations

import calendar
import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget

__all__ = ["CalendarView", "DatePicker"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_week(d: datetime.date) -> int:
    return d.isocalendar()[1]


def _first_of_prev(d: datetime.date) -> datetime.date:
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=1)
    return d.replace(month=d.month - 1, day=1)


def _first_of_next(d: datetime.date) -> datetime.date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


def _clamp_to_month(year: int, month: int, day: int) -> datetime.date:
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day, last))


# ---------------------------------------------------------------------------
# CalendarView — public embeddable widget
# ---------------------------------------------------------------------------

class CalendarView(Widget, can_focus=True):
    """
    An embeddable calendar widget.

    When focused it accepts keyboard and mouse input.  Posts
    ``CalendarView.DateSelected`` when a date is confirmed and
    ``CalendarView.Cancelled`` when Escape is pressed.
    """

    # ---------------------------------------------------------------- messages

    class DateSelected(Message):
        """Posted when the user confirms a date."""
        def __init__(self, date: str) -> None:
            self.date = date   # "YYYY-MM-DD"
            super().__init__()

    class Cancelled(Message):
        """Posted when the user presses Escape."""

    # ---------------------------------------------------------------- bindings

    BINDINGS = [
        Binding("left",   "prev_day",   show=False),
        Binding("right",  "next_day",   show=False),
        Binding("up",     "prev_week",  show=False),
        Binding("down",   "next_week",  show=False),
        Binding("[",      "prev_month", show=False),
        Binding("]",      "next_month", show=False),
        Binding("enter",  "select",     show=False),
        Binding("escape", "cancel",     show=False),
    ]

    # Each column (Wk + 7 day columns) is this many characters wide.
    COL_W = 4

    def __init__(
        self,
        initial: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._today  = datetime.date.today()
        start        = self._parse(initial) or self._today
        self._cursor = start
        self._month  = start.replace(day=1)

    # ---------------------------------------------------------------- public API

    def set_date(self, date_str: str | None) -> None:
        """Update the highlighted date without posting a message."""
        d = self._parse(date_str)
        if d:
            self._cursor = d
            self._month  = d.replace(day=1)
            self.refresh()

    # ---------------------------------------------------------------- grid

    @staticmethod
    def _parse(s: str | None) -> datetime.date | None:
        if not s:
            return None
        try:
            return datetime.date.fromisoformat(str(s))
        except (ValueError, TypeError):
            return None

    def _build_grid(self) -> list[list[datetime.date]]:
        """6 rows × 7 cols (Mon–Sun), including days from adjacent months."""
        cal   = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self._month.year, self._month.month)
        while len(weeks) < 6:
            last_day = weeks[-1][-1]
            extra    = [last_day + datetime.timedelta(days=i + 1) for i in range(7)]
            weeks.append(extra)
        return weeks[:6]

    # ---------------------------------------------------------------- render

    def render(self):  # -> RenderableType
        from rich.text import Text

        cw    = self.COL_W
        year  = self._month.year
        month = self._month.month
        mname = self._month.strftime("%b")
        total = cw * 8

        lines: list[Text] = []

        # Month navigation header
        hdr_str = f"<  {mname},{year}  >"
        lines.append(Text(hdr_str.center(total), style="bold #5E8B87"))

        # Day-name header
        day_names = Text()
        day_names.append(f"{'Wk':<{cw}}", style="#7A6E64")
        for abbr in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"):
            day_names.append(f"{abbr:<{cw}}", style="#C4AA82")
        lines.append(day_names)

        # Week rows
        grid = self._build_grid()
        for week in grid:
            row    = Text()
            wk_num = _iso_week(week[0])
            row.append(f"{wk_num:<{cw}}", style="#7A6E64")
            for d in week:
                label = f"{d.day:<{cw}}"
                if d == self._cursor:
                    style = "bold reverse"
                elif d == self._today:
                    style = "bold #6FA7A2"
                elif d.month != month:
                    style = "#4A443D"
                else:
                    style = "#E1D4C0"
                row.append(label, style=style)
            lines.append(row)

        result = Text()
        for i, line in enumerate(lines):
            if i:
                result.append("\n")
            result.append_text(line)
        return result

    # ---------------------------------------------------------------- sizing

    def get_content_width(self, container, viewport) -> int:  # type: ignore[override]
        return self.COL_W * 8

    def get_content_height(self, container, viewport, width) -> int:  # type: ignore[override]
        return 8  # 2 header rows + 6 week rows

    # ---------------------------------------------------------------- actions

    def _sync_month(self) -> None:
        self._month = self._cursor.replace(day=1)

    def action_prev_day(self) -> None:
        self._cursor -= datetime.timedelta(days=1)
        self._sync_month()
        self.refresh()

    def action_next_day(self) -> None:
        self._cursor += datetime.timedelta(days=1)
        self._sync_month()
        self.refresh()

    def action_prev_week(self) -> None:
        self._cursor -= datetime.timedelta(weeks=1)
        self._sync_month()
        self.refresh()

    def action_next_week(self) -> None:
        self._cursor += datetime.timedelta(weeks=1)
        self._sync_month()
        self.refresh()

    def action_prev_month(self) -> None:
        new_first    = _first_of_prev(self._month)
        self._month  = new_first
        self._cursor = _clamp_to_month(new_first.year, new_first.month, self._cursor.day)
        self.refresh()

    def action_next_month(self) -> None:
        new_first    = _first_of_next(self._month)
        self._month  = new_first
        self._cursor = _clamp_to_month(new_first.year, new_first.month, self._cursor.day)
        self.refresh()

    def action_select(self) -> None:
        self.post_message(self.DateSelected(self._cursor.strftime("%Y-%m-%d")))

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())

    # ---------------------------------------------------------------- mouse

    def on_click(self, event) -> None:
        cw      = self.COL_W
        col_idx = event.x // cw
        row_idx = event.y

        if row_idx == 0:
            if event.x < (cw * 8) // 2:
                self.action_prev_month()
            else:
                self.action_next_month()
            return

        if row_idx == 1 or col_idx == 0:
            return

        day_col  = col_idx - 1
        week_idx = row_idx - 2
        grid     = self._build_grid()

        if week_idx >= len(grid) or day_col > 6:
            return

        clicked      = grid[week_idx][day_col]
        self._cursor = clicked
        self._month  = clicked.replace(day=1)
        self.refresh()
        self.post_message(self.DateSelected(self._cursor.strftime("%Y-%m-%d")))


# ---------------------------------------------------------------------------
# DatePicker — modal wrapper around CalendarView
# ---------------------------------------------------------------------------

class DatePicker(ModalScreen):
    """
    Modal calendar date picker.

    Push with ``push_screen`` and a callback::

        self.push_screen(DatePicker(initial="2026-04-15"), callback=self._on_date)

        def _on_date(self, result):
            if result:   # "YYYY-MM-DD" or None
                ...
    """

    DEFAULT_CSS = """
    DatePicker {
        align: center middle;
    }
    DatePicker > Vertical {
        width: auto;
        height: auto;
        background: #2E2A26;
        border: solid #5E8B87;
        padding: 1 2;
    }
    DatePicker CalendarView {
        width: auto;
        height: auto;
    }
    """

    def __init__(
        self,
        initial: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical():
            yield CalendarView(initial=self._initial)

    def on_mount(self) -> None:
        self.query_one(CalendarView).focus()

    def on_calendar_view_date_selected(self, event: CalendarView.DateSelected) -> None:
        self.dismiss(event.date)

    def on_calendar_view_cancelled(self, event: CalendarView.Cancelled) -> None:
        self.dismiss(None)
