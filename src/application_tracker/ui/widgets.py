from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.label import Label


def label(value: str, *, height: int = 26) -> Label:
    return Label(
        text=value,
        size_hint_y=None,
        height=dp(height),
        halign="left",
        valign="middle",
        text_size=(None, None),
        color=(0.85, 0.89, 0.94, 1),
    )


def button(value: str, callback, *, width: int | None = None) -> Button:
    kwargs = {"size_hint_y": None, "height": dp(42)}
    if width is not None:
        kwargs.update(size_hint_x=None, width=dp(width))
    widget = Button(text=value, **kwargs)
    widget.bind(on_release=lambda *_: callback())
    return widget
