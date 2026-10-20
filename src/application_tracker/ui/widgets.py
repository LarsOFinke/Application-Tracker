"""Small shared constructors for the desktop interface."""

from kivy.effects.scroll import ScrollEffect
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from application_tracker.ui.palette import ACCENT, MUTED, PANEL, PANEL_LIGHT, WHITE
from application_tracker.ui.StyledButton import StyledButton


def surface(widget: BoxLayout, color=PANEL, radius: int = 12) -> BoxLayout:
    with widget.canvas.before:
        Color(*color)
        shape = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
    widget.bind(pos=lambda instance, *_: setattr(shape, "pos", instance.pos))
    widget.bind(size=lambda instance, *_: setattr(shape, "size", instance.size))
    return widget


def label(
    value: str,
    *,
    height: int = 26,
    size: int = 14,
    color=WHITE,
    bold=False,
    shorten: bool = True,
) -> Label:
    widget = Label(
        text=value,
        size_hint_y=None,
        height=dp(height),
        font_size=dp(size),
        bold=bold,
        halign="left",
        valign="middle",
        color=color,
        shorten=shorten,
    )
    widget.bind(size=lambda item, *_: setattr(item, "text_size", item.size))
    return widget


def button(
    value: str,
    callback,
    *,
    width: int | None = None,
    height: int = 42,
    kind: str = "secondary",
) -> StyledButton:
    kwargs = {"size_hint_y": None, "height": dp(height)}
    if width is not None:
        kwargs.update(size_hint_x=None, width=dp(width))
    widget = StyledButton(text=value, kind=kind, **kwargs)
    widget.shorten = True
    widget.shorten_from = "right"
    widget.halign = "center"
    widget.valign = "middle"
    widget.bind(
        size=lambda item, *_: setattr(item, "text_size", (item.width - dp(16), item.height))
    )
    widget.bind(on_release=lambda *_: callback())
    return widget


def text_field(hint: str, *, multiline: bool = False, height: int = 42) -> TextInput:
    return TextInput(
        hint_text=hint,
        multiline=multiline,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_active="",
        background_color=PANEL_LIGHT,
        foreground_color=WHITE,
        cursor_color=ACCENT,
        hint_text_color=MUTED,
        font_size=dp(15),
        padding=[dp(12), dp(10)],
    )


def spinner(value: str, values) -> Spinner:
    return Spinner(
        text=value,
        values=values,
        size_hint_y=None,
        height=dp(42),
        background_normal="",
        background_color=PANEL_LIGHT,
        color=WHITE,
        font_size=dp(15),
    )


def scroll_view(**kwargs) -> ScrollView:
    return ScrollView(
        effect_cls=ScrollEffect,
        scroll_wheel_distance=dp(88),
        bar_width=dp(8),
        **kwargs,
    )


def dialog(title: str, content, **kwargs) -> Popup:
    return Popup(
        title=title,
        content=content,
        background_color=PANEL,
        separator_color=ACCENT,
        title_color=WHITE,
        **kwargs,
    )
