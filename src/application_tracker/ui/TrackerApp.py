"""Small Kivy desktop UI for the local tracker."""

from __future__ import annotations

import os
import webbrowser
from dataclasses import replace
from datetime import datetime
from pathlib import Path

os.environ.setdefault("KIVY_DESKTOP_PATH_ID", "ApplicationTracker")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.metrics import Metrics, dp  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.filechooser import FileChooserListView  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.popup import Popup  # noqa: E402
from kivy.uix.scrollview import ScrollView  # noqa: E402
from kivy.uix.spinner import Spinner  # noqa: E402
from kivy.uix.textinput import TextInput  # noqa: E402

from application_tracker.services.ApplicationData import ApplicationData  # noqa: E402
from application_tracker.services.ApplicationInput import ApplicationInput  # noqa: E402
from application_tracker.services.ApplicationMapper import STATUSES  # noqa: E402
from application_tracker.services.ApplicationService import ApplicationService  # noqa: E402
from application_tracker.storage.database import (  # noqa: E402
    backup_database,
    default_database_path,
    make_session_factory,
)
from application_tracker.ui.scale_settings import SCALES, load_scale, save_scale  # noqa: E402
from application_tracker.ui.widgets import button as _button  # noqa: E402
from application_tracker.ui.widgets import label as _label  # noqa: E402


class TrackerApp(App):
    title = "Application Tracker"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database_path = default_database_path()
        self.service = ApplicationService(make_session_factory(self.database_path))
        self.selected: ApplicationData | None = None
        self.files: list[str] = []
        self.baseline: tuple | None = None
        self.show_done = False
        self.scale_path = self.database_path.with_name("ui.ini")
        self.ui_scale = load_scale(self.scale_path)
        self.base_density = Metrics.density

    def build(self):
        Metrics.density = self.base_density * self.ui_scale
        Window.minimum_width = 860
        Window.minimum_height = 620
        Window.size = (1120, 780)
        Window.clearcolor = (0.10, 0.13, 0.18, 1)
        root = self.build_shell()
        self.refresh_list()
        self.clear_form()
        Window.bind(on_drop_file=self.on_drop_file)
        return root

    def build_shell(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(90), spacing=dp(4))
        title = Label(text="Application Tracker", font_size="22sp", bold=True, halign="left")
        title.bind(size=lambda widget, *_: setattr(widget, "text_size", widget.size))
        header.add_widget(title)
        controls = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        controls.add_widget(_button("History", self.show_history))
        controls.add_widget(_button("Backup", self.backup))
        controls.add_widget(_button("New", self.new))
        scale = Spinner(
            text=f"Scale {self.ui_scale:.0%}",
            values=[f"Scale {value:.0%}" for value in SCALES],
        )
        scale.bind(text=self.change_scale)
        controls.add_widget(scale)
        controls.add_widget(_button("Exit", lambda: self.guard_changes(self.stop)))
        header.add_widget(controls)
        root.add_widget(header)

        body = BoxLayout(spacing=dp(14))
        left = BoxLayout(orientation="vertical", size_hint_x=0.36, spacing=dp(8))
        self.search = TextInput(
            hint_text="Search company, role or status",
            multiline=False,
            size_hint_y=None,
            height=dp(42),
        )
        self.search.bind(text=lambda *_: self.refresh_list())
        left.add_widget(self.search)
        self.done_filter = _button("Show done", self.toggle_done)
        self.done_filter.size_hint_y = None
        self.done_filter.height = dp(42)
        left.add_widget(self.done_filter)
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.list_scroll = ScrollView()
        self.list_scroll.add_widget(self.list_box)
        left.add_widget(self.list_scroll)
        body.add_widget(left)

        self.right_scroll = ScrollView(size_hint_x=0.64)
        self.form = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
            padding=[dp(8), 0, dp(8), dp(10)],
        )
        self.form.bind(minimum_height=self.form.setter("height"))
        self.heading = _label("New application", height=38)
        self.form.add_widget(self.heading)
        self.company = self.field("Company", "Company name")
        self.role = self.field("Role", "Position or opportunity")
        self.form.add_widget(_label("Status"))
        self.status = Spinner(text=STATUSES[0], values=STATUSES, size_hint_y=None, height=dp(42))
        self.form.add_widget(self.status)
        self.location = self.field("Location (optional)", "City or remote")
        self.contact_name = self.field("Contact name (optional)", "Recruiter or hiring manager")
        self.contact_email = self.field("Contact email (optional)", "name@example.org")
        self.contact_phone = self.field("Contact phone (optional)", "+49 …")
        self.url = self.field("Links (one per line)", "https://…", multiline=True, height=84)
        self.summary = self.field(
            "Summary", "What is this opportunity?", multiline=True, height=108
        )
        self.hints = self.field(
            "Hints / next steps", "Contacts, deadlines, questions…", multiline=True, height=108
        )
        file_heading = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        file_heading.add_widget(_label("Files (add or drop onto window)"))
        file_heading.add_widget(_button("Add file", self.choose_file, width=100))
        self.form.add_widget(file_heading)
        self.files_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.files_box.bind(minimum_height=self.files_box.setter("height"))
        self.form.add_widget(self.files_box)
        self.timestamps = _label("", height=30)
        self.form.add_widget(self.timestamps)
        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.submit_button = _button("Save new", self.submit)
        actions.add_widget(self.submit_button)
        actions.add_widget(_button("Open link", self.open_link))
        self.done_button = _button("Mark done", self.mark_done)
        actions.add_widget(self.done_button)
        actions.add_widget(_button("Delete", self.confirm_delete))
        self.form.add_widget(actions)
        self.right_scroll.add_widget(self.form)
        body.add_widget(self.right_scroll)
        root.add_widget(body)
        return root

    def change_scale(self, _spinner: Spinner, label: str) -> None:
        value = float(label.removeprefix("Scale ").removesuffix("%")) / 100
        if value == self.ui_scale:
            return
        try:
            save_scale(self.scale_path, value)
        except (OSError, ValueError) as exc:
            self.show_error(exc)
            return
        values = self.current_values()
        selected, baseline = self.selected, self.baseline
        search = self.search.text
        timestamps = self.timestamps.text
        list_y, right_y = self.list_scroll.scroll_y, self.right_scroll.scroll_y
        self.ui_scale = value
        Metrics.density = self.base_density * value
        replacement = self.build_shell()
        self.root.clear_widgets()
        self.root.padding = replacement.padding
        self.root.spacing = replacement.spacing
        for child in reversed(replacement.children[:]):
            replacement.remove_widget(child)
            self.root.add_widget(child)
        self.done_filter.text = "Hide done" if self.show_done else "Show done"
        self.search.text = search
        (
            self.company.text,
            self.role.text,
            self.status.text,
            self.url.text,
            self.summary.text,
            self.hints.text,
            self.location.text,
            self.contact_name.text,
            self.contact_email.text,
            self.contact_phone.text,
            files,
        ) = values
        self.files = list(files)
        self.refresh_files()
        self.selected, self.baseline = selected, baseline
        self.heading.text = f"Application #{selected.id}" if selected else "New application"
        self.submit_button.text = "Update" if selected else "Save new"
        self.done_button.disabled = selected is None or selected.status == "Done"
        self.timestamps.text = timestamps
        self.refresh_list()
        Clock.schedule_once(
            lambda _dt: self.restore_scroll(list_y, right_y), 0
        )

    def restore_scroll(self, list_y: float, right_y: float) -> None:
        self.list_scroll.scroll_y = list_y
        self.right_scroll.scroll_y = right_y

    def toggle_done(self) -> None:
        self.show_done = not self.show_done
        self.done_filter.text = "Hide done" if self.show_done else "Show done"
        self.refresh_list()

    def field(
        self, title: str, hint: str, *, multiline: bool = False, height: int = 42
    ) -> TextInput:
        self.form.add_widget(_label(title))
        field = TextInput(hint_text=hint, multiline=multiline, size_hint_y=None, height=dp(height))
        self.form.add_widget(field)
        return field

    def current_values(self) -> tuple:
        return (
            self.company.text,
            self.role.text,
            self.status.text,
            self.url.text,
            self.summary.text,
            self.hints.text,
            self.location.text,
            self.contact_name.text,
            self.contact_email.text,
            self.contact_phone.text,
            tuple(self.files),
        )

    def guard_changes(self, action) -> None:
        if self.current_values() == self.baseline:
            action()
            return
        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        layout.add_widget(Label(text="Discard unsaved changes?"))
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(
            title="Unsaved changes", content=layout, size_hint=(None, None), size=(dp(380), dp(180))
        )
        buttons.add_widget(_button("Keep editing", popup.dismiss))

        def discard():
            popup.dismiss()
            action()

        buttons.add_widget(_button("Discard", discard))
        layout.add_widget(buttons)
        popup.open()

    def new(self) -> None:
        self.guard_changes(self.clear_form)

    def clear_form(self) -> None:
        self.selected = None
        self.heading.text = "New application"
        self.submit_button.text = "Save new"
        self.done_button.disabled = True
        for field in (
            self.company,
            self.role,
            self.url,
            self.summary,
            self.hints,
            self.location,
            self.contact_name,
            self.contact_email,
            self.contact_phone,
        ):
            field.text = ""
        self.status.text = STATUSES[0]
        self.timestamps.text = ""
        self.files = []
        self.refresh_files()
        self.baseline = self.current_values()

    def select(self, record_id: int) -> None:
        self.guard_changes(lambda: self.load(record_id))

    def load(self, record_id: int) -> None:
        try:
            record = self.service.get(record_id)
        except Exception as exc:
            self.show_error(exc)
            return
        self.selected = record
        self.heading.text = f"Application #{record.id}"
        self.submit_button.text = "Update"
        self.done_button.disabled = record.status == "Done"
        self.company.text, self.role.text, self.status.text = (
            record.company,
            record.role,
            record.status,
        )
        self.url.text, self.summary.text, self.hints.text = record.url, record.summary, record.hints
        self.location.text = record.location
        self.contact_name.text = record.contact_name
        self.contact_email.text = record.contact_email
        self.contact_phone.text = record.contact_phone
        self.show_timestamps(record)
        self.files = list(record.files)
        self.refresh_files()
        self.baseline = self.current_values()

    def refresh_list(self) -> None:
        self.list_box.clear_widgets()
        try:
            records = self.service.list(self.search.text)
        except Exception as exc:
            self.show_error(exc)
            return
        if not self.show_done:
            records = [record for record in records if record.status != "Done"]
        if not records:
            self.list_box.add_widget(_label("No applications to show", height=46))
        for record in records:
            label = f"{record.company}  ·  {record.role}\n{record.status}"
            button = _button(label, lambda record_id=record.id: self.select(record_id))
            button.height = dp(64)
            button.halign = "left"
            self.list_box.add_widget(button)

    def refresh_files(self) -> None:
        self.files_box.clear_widgets()
        for path in self.files:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            row.add_widget(_button(Path(path).name, lambda item=path: self.open_file(item)))
            row.add_widget(_button("×", lambda item=path: self.remove_file(item), width=42))
            self.files_box.add_widget(row)

    def choose_file(self) -> None:
        chooser = FileChooserListView(path=str(Path.home()), filters=[])
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        layout.add_widget(chooser)
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title="Choose a file", content=layout, size_hint=(0.85, 0.85))
        buttons.add_widget(_button("Cancel", popup.dismiss))

        def add():
            if chooser.selection:
                selected = Path(chooser.selection[0]).resolve()
                if self.add_file(selected):
                    popup.dismiss()

        buttons.add_widget(_button("Add", add))
        layout.add_widget(buttons)
        popup.open()

    def add_file(self, path: Path) -> bool:
        path = path.resolve()
        if not path.is_file() or str(path) in self.files:
            return False
        self.files.append(str(path))
        self.refresh_files()
        return True

    def on_drop_file(self, _window, filename: bytes, *_args) -> None:
        self.add_file(Path(os.fsdecode(filename)))

    def remove_file(self, path: str) -> None:
        self.files.remove(path)
        self.refresh_files()

    def form_input(self) -> ApplicationInput:
        return ApplicationInput(
            company=self.company.text,
            role=self.role.text,
            status=self.status.text,
            url=self.url.text,
            summary=self.summary.text,
            hints=self.hints.text,
            files=tuple(self.files),
            location=self.location.text,
            contact_name=self.contact_name.text,
            contact_email=self.contact_email.text,
            contact_phone=self.contact_phone.text,
        )

    def submit(self) -> None:
        try:
            data = self.form_input()
            record = (
                self.service.create(data)
                if self.selected is None
                else self.service.update(self.selected.id, data)
            )
        except Exception as exc:
            self.show_error(exc)
            return
        self.selected = record
        self.heading.text = f"Application #{record.id}"
        self.submit_button.text = "Update"
        self.done_button.disabled = record.status == "Done"
        self.show_timestamps(record)
        self.baseline = self.current_values()
        self.refresh_list()

    def mark_done(self) -> None:
        if self.selected is None:
            return
        try:
            self.service.update(self.selected.id, replace(self.form_input(), status="Done"))
        except Exception as exc:
            self.show_error(exc)
            return
        self.clear_form()
        self.refresh_list()

    def show_timestamps(self, record: ApplicationData) -> None:
        self.timestamps.text = (
            f"Created {record.created_at:%Y-%m-%d %H:%M}  ·  "
            f"Updated {record.updated_at:%Y-%m-%d %H:%M}"
        )

    def show_history(self) -> None:
        try:
            events = self.service.history(self.selected.id if self.selected else None)
        except Exception as exc:
            self.show_error(exc)
            return
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))
        rows = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        rows.bind(minimum_height=rows.setter("height"))
        if not events:
            rows.add_widget(_label("No history yet", height=40))
        for item in events:
            rows.add_widget(
                _label(
                    f"{item.happened_at:%Y-%m-%d %H:%M}  ·  #{item.application_id}  "
                    f"{item.action}: {item.detail}",
                    height=52,
                )
            )
        scroll = ScrollView()
        scroll.add_widget(rows)
        layout.add_widget(scroll)
        popup = Popup(title="Change history", content=layout, size_hint=(0.82, 0.75))
        layout.add_widget(_button("Close", popup.dismiss))
        popup.open()

    def confirm_delete(self) -> None:
        if self.selected is None:
            return
        record_id = self.selected.id
        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        layout.add_widget(Label(text="Delete this application? Linked files stay on disk."))
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(
            title="Delete application",
            content=layout,
            size_hint=(None, None),
            size=(dp(460), dp(180)),
        )
        buttons.add_widget(_button("Cancel", popup.dismiss))

        def delete():
            try:
                self.service.delete(record_id)
                popup.dismiss()
                self.clear_form()
                self.refresh_list()
            except Exception as exc:
                popup.dismiss()
                self.show_error(exc)

        buttons.add_widget(_button("Delete", delete))
        layout.add_widget(buttons)
        popup.open()

    def open_link(self) -> None:
        links = [item.strip() for item in self.url.text.splitlines() if item.strip()]
        if not links:
            return
        if any(not item.startswith(("https://", "http://")) for item in links):
            self.show_error(ValueError("Links must begin with https:// or http://"))
            return
        if len(links) == 1:
            webbrowser.open(links[0])
            return
        layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        popup = Popup(title="Open a link", content=layout, size_hint=(0.7, 0.7))
        for link in links:

            def open_selected(value=link):
                webbrowser.open(value)
                popup.dismiss()

            layout.add_widget(_button(link, open_selected))
        popup.open()

    def open_file(self, path: str) -> None:
        if not Path(path).is_file():
            self.show_error(FileNotFoundError(f"File is missing: {path}"))
            return
        webbrowser.open(Path(path).as_uri())

    def backup(self) -> None:
        destination = (
            self.database_path.parent
            / "backups"
            / f"applications-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        )
        try:
            backup_database(self.database_path, destination)
        except Exception as exc:
            self.show_error(exc)
            return
        self.message("Backup created", str(destination))

    def show_error(self, exc: Exception) -> None:
        self.message("Could not complete action", str(exc))

    def message(self, title: str, body: str) -> None:
        label = Label(text=body, text_size=(dp(480), None), halign="center")
        Popup(title=title, content=label, size_hint=(None, None), size=(dp(540), dp(220))).open()
