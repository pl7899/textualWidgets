"""
Tests for DatePicker.

Run from the project root:
    pytest tests/ -v
    pytest tests/test_date_picker.py -v     # this file only
"""

import datetime
import pytest
from textual.app import App, ComposeResult

from textual_widgets import CalendarView, DatePicker
from textual_widgets.date_picker import _clamp_to_month, _iso_week


# ---------------------------------------------------------------------------
# Unit tests — pure helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_iso_week(self):
        # 2026-04-06 is ISO week 15
        assert _iso_week(datetime.date(2026, 4, 6)) == 15

    def test_clamp_within_month(self):
        assert _clamp_to_month(2026, 4, 15) == datetime.date(2026, 4, 15)

    def test_clamp_exceeds_month(self):
        # April has 30 days — day 31 should clamp to 30
        assert _clamp_to_month(2026, 4, 31) == datetime.date(2026, 4, 30)

    def test_clamp_february_non_leap(self):
        assert _clamp_to_month(2025, 2, 29) == datetime.date(2025, 2, 28)

    def test_clamp_february_leap(self):
        assert _clamp_to_month(2024, 2, 29) == datetime.date(2024, 2, 29)


# ---------------------------------------------------------------------------
# Shared fixture: app that pushes DatePicker via callback
# ---------------------------------------------------------------------------

def _make_picker_app(initial: str) -> App:
    """App that opens DatePicker(initial) immediately and stores the result."""
    class _PickerApp(App):
        CSS = "Screen { layers: base floating; }"
        picked: str | None = "NOT_SET"

        def on_mount(self) -> None:
            self.push_screen(
                DatePicker(initial=initial),
                callback=self._store,
            )

        def _store(self, result: str | None) -> None:
            self.picked = result

    return _PickerApp()


# ---------------------------------------------------------------------------
# DatePicker — rendering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calendar_view_has_positive_height():
    """The CalendarView must render with a non-zero content height."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        view = app.query_one(CalendarView)
        assert view.content_size.height > 0


@pytest.mark.asyncio
async def test_calendar_view_is_focused_on_open():
    """The calendar widget should receive focus automatically."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        view = app.query_one(CalendarView)
        assert view.has_focus


# ---------------------------------------------------------------------------
# DatePicker — selection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enter_returns_initial_date():
    """Pressing Enter without navigation returns the initial date."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.picked == "2026-04-15"


@pytest.mark.asyncio
async def test_escape_returns_none():
    """Pressing Escape dismisses with None."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.picked is None


# ---------------------------------------------------------------------------
# DatePicker — keyboard navigation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_right_moves_forward_one_day():
    """→ moves the cursor forward by one day."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("right", "enter")
        await pilot.pause()
        assert app.picked == "2026-04-16"


@pytest.mark.asyncio
async def test_left_moves_back_one_day():
    """← moves the cursor back by one day."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("left", "enter")
        await pilot.pause()
        assert app.picked == "2026-04-14"


@pytest.mark.asyncio
async def test_down_moves_forward_one_week():
    """↓ moves the cursor forward by seven days."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down", "enter")
        await pilot.pause()
        assert app.picked == "2026-04-22"


@pytest.mark.asyncio
async def test_up_moves_back_one_week():
    """↑ moves the cursor back by seven days."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("up", "enter")
        await pilot.pause()
        assert app.picked == "2026-04-08"


@pytest.mark.asyncio
async def test_bracket_next_month():
    """] moves to the same day in the next month."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("]", "enter")
        await pilot.pause()
        assert app.picked == "2026-05-15"


@pytest.mark.asyncio
async def test_bracket_prev_month():
    """[ moves to the same day in the previous month."""
    app = _make_picker_app("2026-04-15")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("[", "enter")
        await pilot.pause()
        assert app.picked == "2026-03-15"


@pytest.mark.asyncio
async def test_next_month_clamps_day():
    """Moving from Jan 31 → Feb clamps to last day of February."""
    app = _make_picker_app("2026-01-31")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("]", "enter")
        await pilot.pause()
        assert app.picked == "2026-02-28"


@pytest.mark.asyncio
async def test_right_key_crosses_month_boundary():
    """Navigating right past the end of April lands on May 1."""
    app = _make_picker_app("2026-04-30")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("right", "enter")
        await pilot.pause()
        assert app.picked == "2026-05-01"


@pytest.mark.asyncio
async def test_left_key_crosses_month_boundary():
    """Navigating left from April 1 lands on March 31."""
    app = _make_picker_app("2026-04-01")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("left", "enter")
        await pilot.pause()
        assert app.picked == "2026-03-31"


# ---------------------------------------------------------------------------
# DatePicker — defaults
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_initial_defaults_to_today():
    """DatePicker() with no argument pre-selects today."""
    today = datetime.date.today().strftime("%Y-%m-%d")

    class _TodayApp(App):
        CSS = "Screen { layers: base floating; }"
        picked: str | None = "NOT_SET"

        def on_mount(self) -> None:
            self.push_screen(DatePicker(), callback=lambda r: setattr(self, "picked", r))

    app = _TodayApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.picked == today


@pytest.mark.asyncio
async def test_invalid_initial_falls_back_to_today():
    """An unparseable initial string should not crash — falls back to today."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    app = _make_picker_app("not-a-date")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.picked == today
