"""
Interactive demo for DatePicker.

Run from the project root:
    python demo/demo_date_picker.py

Press 'd' to open the date picker.  The selected date appears in the label.
Press 'q' to quit.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label, Footer

from textual_widgets import DatePicker


class DemoApp(App):
    CSS = """
    Screen {
        align: center middle;
        background: #2E2A26;
        color: #F4F1E8;
    }
    #result {
        width: auto;
        height: auto;
        padding: 1 3;
        background: #3A332C;
        border: solid #5E8B87;
        color: #6FA7A2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("d", "pick_date", "Pick date"),
        Binding("q", "quit",      "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Press 'd' to open the date picker", id="result")
        yield Footer()

    _last_date: str | None = None

    def action_pick_date(self) -> None:
        self.push_screen(
            DatePicker(initial=self._last_date),
            callback=self._on_picked,
        )

    def _on_picked(self, result: str | None) -> None:
        label = self.query_one("#result", Label)
        if result:
            self._last_date = result
            label.update(result)
        else:
            label.update("(cancelled)")


if __name__ == "__main__":
    DemoApp().run()
