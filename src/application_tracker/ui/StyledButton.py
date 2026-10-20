"""Rounded buttons with clear primary, selected, and danger states."""

from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.button import Button

from application_tracker.ui.palette import ACCENT, BG, GREEN, MUTED, PANEL_LIGHT, RED, WHITE


class StyledButton(Button):
    def __init__(self, *, kind: str = "secondary", **kwargs):
        self.kind = kind
        super().__init__(background_normal="", background_down="", **kwargs)
        self.background_color = (0, 0, 0, 0)
        self.font_size = dp(14)
        self.bold = kind in {"primary", "selected"}
        with self.canvas.before:
            self._fill = Color()
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(9)])
        self.bind(pos=self._place_shape, size=self._place_shape)
        self.bind(disabled=self._update_colors, state=self._update_colors)
        self._update_colors()

    def _place_shape(self, *_args) -> None:
        self._shape.pos = self.pos
        self._shape.size = self.size

    def _update_colors(self, *_args) -> None:
        background = {
            "primary": ACCENT,
            "selected": ACCENT,
            "danger": RED,
            "danger_outline": PANEL_LIGHT,
            "success": PANEL_LIGHT,
            "secondary": PANEL_LIGHT,
        }[self.kind]
        foreground = {
            "primary": BG,
            "selected": BG,
            "danger": WHITE,
            "danger_outline": RED,
            "success": GREEN,
            "secondary": WHITE,
        }[self.kind]
        if self.disabled:
            self._fill.rgba = (*PANEL_LIGHT[:3], 0.45)
            self.color = MUTED
        elif self.state == "down":
            self._fill.rgba = tuple(max(0, component * 0.82) for component in background[:3]) + (1,)
            self.color = foreground
        else:
            self._fill.rgba = background
            self.color = foreground
