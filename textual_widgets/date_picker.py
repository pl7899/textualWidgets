"""
DatePicker — a modal calendar widget for Textual.

Usage
-----
Push the screen and await the result::

    date = await self.app.push_screen_wait(DatePicker())
    date = await self.app.push_screen_wait(DatePicker(initial="2026-04-15"))

Returns a ``"YYYY-MM-DD"`` string, or ``None`` if the user pressed Escape.

Calendar display::

    <  Apr,2026  >
    Wk    Mo    Tu    We    Th    Fr    Sa    Su
    13    30    31    1     2     3     4     5
    14    6     7     8     9     10    11    12
    15    13    14    15    16    17    18    19
    16    20    21    22    23    24    25    26
    17    27    28    29    30    1     2     3
    18    4     5     6     7     8     9     10

Keyboard navigation
-------------------
- ``←`` / ``→``  — previous / next day
- ``↑`` / ``↓``  — previous / next week
- ``[`` / ``]``  — previous / next month (cursor clamped to last day if needed)
- ``Enter``      — confirm selected date
- ``Escape``     — cancel (returns None)

Mouse
-----
- Click a day to select and confirm it immediately.
- Click the left half of the header to go to the previous month.
- Click the right half of the header to go to the next month.
"""

from __future__ import annotations

import calendar
import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widget import Widget

__all__ = ["DatePicker"]


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
# Internal calendar widget
# ---------------------------------------------------------------------------

class _CalendarView(Widget, can_focus=True):
    """
    Renders a month calendar and handles keyboard/mouse interaction.
    Calls ``self.screen.dismiss(date_str)`` when a date is confirmed.
    """

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

    def __init__(self, initial: datetime.date) -> None:
        super().__init__()
        self._today  = datetime.date.today()
        self._cursor = initial
        self._month  = initial.replace(day=1)

    # ---------------------------------------------------------------- grid

    def _build_grid(self) -> list[list[datetime.date]]:
        """
        Return 6 complete Mon–Sun weeks that cover the current month.
        Weeks that spill into adjacent months are included.
        """
        cal   = calendar.Calendar(firstweekday=0)  # Monday first
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
        total = cw * 8  # total character width

        lines: list[Text] = []

        # Month navigation header — centred
        hdr_str = f"<  {mname},{year}  >"
        header  = Text(hdr_str.center(total), style="bold #5E8B87")
        lines.append(header)

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
        """Keep the viewed month in sync with the cursor after day navigation."""
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
        new_first     = _first_of_prev(self._month)
        self._month   = new_first
        self._cursor  = _clamp_to_month(new_first.year, new_first.month, self._cursor.day)
        self.refresh()

    def action_next_month(self) -> None:
        new_first     = _first_of_next(self._month)
        self._month   = new_first
        self._cursor  = _clamp_to_month(new_first.year, new_first.month, self._cursor.day)
        self.refresh()

    def action_select(self) -> None:
        self.screen.dismiss(self._cursor.strftime("%Y-%m-%d"))

    def action_cancel(self) -> None:
        self.screen.dismiss(None)

    # ---------------------------------------------------------------- mouse

    def on_click(self, event) -> None:
        cw      = self.COL_W
        col_idx = event.x // cw   # 0 = Wk column, 1‒7 = Mon–Sun
        row_idx = event.y          # 0 = month header, 1 = day names, 2‒7 = weeks

        if row_idx == 0:
            # Header: left half → previous month, right half → next month
            if event.x < (cw * 8) // 2:
                self.action_prev_month()
            else:
                self.action_next_month()
            return

        if row_idx == 1 or col_idx == 0:
            return  # day-name header row or week-number column

        day_col  = col_idx - 1   # 0 = Monday … 6 = Sunday
        week_idx = row_idx - 2

        grid = self._build_grid()
        if week_idx >= len(grid) or day_col > 6:
            return

        clicked      = grid[week_idx][day_col]
        self._cursor = clicked
        self._month  = clicked.replace(day=1)
        self.refresh()
        self.screen.dismiss(self._cursor.strftime("%Y-%m-%d"))


# ---------------------------------------------------------------------------
# Public modal screen
# ---------------------------------------------------------------------------

class DatePicker(ModalScreen):
    """
    Modal calendar date picker.

    Push with ``push_screen_wait`` and await the result::

        date = await self.app.push_screen_wait(DatePicker())
        date = await self.app.push_screen_wait(DatePicker(initial="2026-04-15"))

    Returns a ``"YYYY-MM-DD"`` string, or ``None`` if Escape was pressed.
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

    _CalendarView {
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
        if initial:
            try:
                self._initial = datetime.date.fromisoformat(initial)
            except (ValueError, TypeError):
                self._initial = datetime.date.today()
        else:
            self._initial = datetime.date.today()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield _CalendarView(initial=self._initial)

    def on_mount(self) -> None:
        self.query_one(_CalendarView).focus()
