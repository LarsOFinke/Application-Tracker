"""Small Kivy desktop UI for the local tracker."""

from __future__ import annotations

import logging
import os
import webbrowser
from datetime import datetime
from pathlib import Path

os.environ.setdefault("KIVY_DESKTOP_PATH_ID", "ApplicationTracker")
os.environ.setdefault("KIVY_CLIPBOARD", "sdl2")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.logger import Logger  # noqa: E402
from kivy.metrics import Metrics, dp  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.filechooser import FileChooserListView  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.spinner import Spinner  # noqa: E402
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem  # noqa: E402
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
from application_tracker.ui.palette import ACCENT, BG, MUTED, PANEL, PANEL_LIGHT, WHITE  # noqa: E402
from application_tracker.ui.scale_settings import SCALES, load_scale, save_scale  # noqa: E402
from application_tracker.ui.widgets import button as _button  # noqa: E402
from application_tracker.ui.widgets import dialog as _dialog  # noqa: E402
from application_tracker.ui.widgets import label as _label  # noqa: E402
from application_tracker.ui.widgets import scroll_view as _scroll_view  # noqa: E402
from application_tracker.ui.widgets import spinner as _spinner  # noqa: E402
from application_tracker.ui.widgets import surface as _surface  # noqa: E402
from application_tracker.ui.widgets import text_field as _text_field  # noqa: E402


def _hide_optional_cutbuffer_warning(record: logging.LogRecord) -> bool:
    return not record.getMessage().startswith(
        "Cutbuffer: Unable to find any valuable Cutbuffer provider."
    )


class TrackerApp(App):
    title = "Application Tracker"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database_path = default_database_path()
        self.service = ApplicationService(make_session_factory(self.database_path))
        self.selected: ApplicationData | None = None
        self.files: list[str] = []
        self.links: list[str] = []
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
        Window.clearcolor = BG
        # Kivy probes optional X11 primary-selection tools when TextInput is first built.
        # Normal copy/paste uses SDL2; the missing cutbuffer needs no user action.
        Logger.addFilter(_hide_optional_cutbuffer_warning)
        try:
            root = self.build_shell()
        finally:
            Logger.removeFilter(_hide_optional_cutbuffer_warning)
        self.refresh_list()
        self.clear_form()
        Window.bind(on_drop_file=self.on_drop_file)
        return root

    def build_shell(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        header = _surface(
            BoxLayout(size_hint_y=None, height=dp(76), padding=dp(14), spacing=dp(12))
        )
        identity = BoxLayout(orientation="vertical", spacing=dp(2))
        identity.add_widget(_label("Application Tracker", height=35, size=22, bold=True))
        identity.add_widget(
            _label("Your opportunities, in one place", height=18, size=12, color=MUTED)
        )
        header.add_widget(identity)
        controls = BoxLayout(size_hint_x=None, width=dp(295), spacing=dp(7))
        controls.add_widget(_button("History", self.show_history, width=64))
        controls.add_widget(_button("Backup", self.backup, width=64))
        scale = _spinner(f"Scale {self.ui_scale:.0%}", [f"Scale {value:.0%}" for value in SCALES])
        scale.size_hint_x = None
        scale.width = dp(92)
        scale.bind(text=self.change_scale)
        controls.add_widget(scale)
        controls.add_widget(_button("Exit", lambda: self.guard_changes(self.stop), width=54))
        header.add_widget(controls)
        root.add_widget(header)

        body = BoxLayout(spacing=dp(12))
        left = _surface(
            BoxLayout(orientation="vertical", size_hint_x=0.36, padding=dp(12), spacing=dp(9))
        )
        self.list_heading = _label("Applications", height=32, size=18, bold=True)
        left.add_widget(self.list_heading)
        left.add_widget(_button("+  New application", self.new, kind="primary"))
        self.search = _text_field("Search company, role, status…")
        self.search.bind(text=lambda *_: self.refresh_list())
        left.add_widget(self.search)
        self.done_filter = _button("Show done", self.toggle_done)
        left.add_widget(self.done_filter)
        self.list_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.list_scroll = _scroll_view()
        self.list_scroll.add_widget(self.list_box)
        left.add_widget(self.list_scroll)
        body.add_widget(left)

        editor = _surface(
            BoxLayout(orientation="vertical", size_hint_x=0.64, padding=dp(12), spacing=dp(8))
        )
        self.heading = _label("New application", height=38, size=20, bold=True)
        editor.add_widget(self.heading)
        self.timestamps = _label("", height=26, size=12, color=MUTED)
        editor.add_widget(self.timestamps)

        self.tabs = TabbedPanel(
            do_default_tab=False,
            tab_height=dp(42),
            tab_width=dp(104),
            background_image="",
            background_color=PANEL,
        )
        self.tab_scrolls = {}
        self.overview_tab, overview = self.tab_content("Overview")
        self.info_tab, info = self.tab_content("Info")
        self.files_tab, files = self.tab_content("Files")
        self.build_overview(overview)
        self.build_info(info)
        self.build_files(files)
        self.configure_field_navigation()
        self.tabs.switch_to(self.overview_tab)
        editor.add_widget(self.tabs)

        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.create_button = _button("Create application", self.create_application, kind="primary")
        actions.add_widget(self.create_button)
        self.update_button = _button("Update application", self.update_application, kind="primary")
        actions.add_widget(self.update_button)
        editor.add_widget(actions)
        body.add_widget(editor)
        root.add_widget(body)
        return root

    def tab_content(self, title: str) -> tuple[TabbedPanelItem, BoxLayout]:
        tab = TabbedPanelItem(
            text=title,
            background_normal="",
            background_down="",
            background_color=PANEL_LIGHT,
            color=WHITE,
            font_size=dp(14),
        )
        tab.bind(
            state=lambda item, state: setattr(
                item, "background_color", ACCENT if state == "down" else PANEL_LIGHT
            )
        )
        tab.bind(state=lambda item, state: setattr(item, "color", BG if state == "down" else WHITE))
        scroll = _surface(_scroll_view())
        content = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(10)
        )
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        tab.add_widget(scroll)
        self.tabs.add_widget(tab)
        self.tab_scrolls[title] = scroll
        return tab, content

    def build_overview(self, content: BoxLayout) -> None:
        content.add_widget(_label("The opportunity", height=30, size=16, bold=True))
        row = self.field_row(content)
        self.company = self.field(row, "Company", "Company name")
        self.role = self.field(row, "Role", "Position")
        row = self.field_row(content)
        self.field_of_work = self.field(row, "Field of work (optional)", "e.g. Engineering")
        self.location = self.field(row, "Location (optional)", "City or remote")
        status_group = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(4)
        )
        status_group.add_widget(_label("Status", height=24, color=MUTED))
        self.status = _spinner(STATUSES[0], STATUSES)
        status_group.add_widget(self.status)
        content.add_widget(status_group)

    def build_info(self, content: BoxLayout) -> None:
        content.add_widget(_label("Contact", height=30, size=16, bold=True))
        row = self.field_row(content)
        self.contact_name = self.field(row, "Name (optional)", "Recruiter or manager")
        self.contact_email = self.field(row, "Email (optional)", "name@example.org")
        self.contact_phone = self.field(content, "Phone (optional)", "+49 …")
        content.add_widget(_label("Notes and links", height=30, size=16, bold=True))
        self.summary = self.field(
            content, "Summary", "What is this opportunity?", multiline=True, height=108
        )
        self.hints = self.field(
            content,
            "Hints / next steps",
            "Deadlines, questions, follow-up…",
            multiline=True,
            height=108,
        )
        row = self.field_row(content)
        self.link_input = self.field(row, "Add a link", "https://…")
        self.link_input.bind(on_text_validate=lambda *_: self.add_link())
        row.add_widget(_button("Add link", self.add_link, width=100))
        content.add_widget(_label("Links", height=26, color=MUTED))
        self.links_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        self.links_box.bind(minimum_height=self.links_box.setter("height"))
        content.add_widget(self.links_box)

    def build_files(self, content: BoxLayout) -> None:
        content.add_widget(_label("Linked files", height=30, size=16, bold=True))
        content.add_widget(
            _label(
                "Files stay in their original location. Add or drop them onto the window.",
                height=50,
                color=MUTED,
            )
        )
        content.add_widget(_button("Add file", self.choose_file, kind="primary"))
        self.files_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        self.files_box.bind(minimum_height=self.files_box.setter("height"))
        content.add_widget(self.files_box)

    def field_row(self, content: BoxLayout) -> BoxLayout:
        row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(8))

        def adapt_width(_row, width):
            compact = width < dp(520)
            row.orientation = "vertical" if compact else "horizontal"
            row.height = dp(152 if compact else 72)

        row.bind(width=adapt_width)
        content.add_widget(row)
        return row

    def configure_field_navigation(self) -> None:
        overview = (self.company, self.role, self.field_of_work, self.location)
        information = (
            self.contact_name,
            self.contact_email,
            self.contact_phone,
            self.summary,
            self.hints,
            self.link_input,
        )
        fields = (self.search, *overview, *information)
        for current, next_field in zip(fields, (*fields[1:], fields[0]), strict=True):
            current.write_tab = False
            current.focus_next = next_field
            next_field.focus_previous = current
        for tab, tab_fields in ((self.overview_tab, overview), (self.info_tab, information)):
            for field in tab_fields:
                field.bind(
                    focus=lambda _field, focused, target=tab: self.focus_tab(target, focused)
                )

    def focus_tab(self, tab: TabbedPanelItem, focused: bool) -> None:
        if focused and self.tabs.current_tab is not tab:
            self.tabs.switch_to(tab)

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
        list_y = self.list_scroll.scroll_y
        tab_name = self.tabs.current_tab.text
        tab_y = {name: scroll.scroll_y for name, scroll in self.tab_scrolls.items()}
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
            self.field_of_work.text,
            self.status.text,
            links,
            self.link_input.text,
            self.summary.text,
            self.hints.text,
            self.location.text,
            self.contact_name.text,
            self.contact_email.text,
            self.contact_phone.text,
            files,
        ) = values
        self.links = list(links)
        self.refresh_links()
        self.files = list(files)
        self.refresh_files()
        self.selected, self.baseline = selected, baseline
        self.heading.text = f"Application #{selected.id}" if selected else "New application"
        self.update_actions()
        self.timestamps.text = timestamps
        self.refresh_list()
        Clock.schedule_once(lambda _dt: self.restore_scroll(list_y, tab_y, tab_name), 0.05)

    def restore_scroll(self, list_y: float, tab_y: dict[str, float], tab_name: str) -> None:
        self.tabs.switch_to(
            {"Overview": self.overview_tab, "Info": self.info_tab, "Files": self.files_tab}[
                tab_name
            ]
        )
        self.list_scroll.scroll_y = list_y
        for name, value in tab_y.items():
            self.tab_scrolls[name].scroll_y = value

    def toggle_done(self) -> None:
        self.show_done = not self.show_done
        self.done_filter.text = "Hide done" if self.show_done else "Show done"
        self.refresh_list()

    def field(
        self,
        parent: BoxLayout,
        title: str,
        hint: str,
        *,
        multiline: bool = False,
        height: int = 42,
    ) -> TextInput:
        group = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(height + 30), spacing=dp(4)
        )
        group.add_widget(_label(title, height=24, color=MUTED))
        field = _text_field(hint, multiline=multiline, height=height)
        group.add_widget(field)
        parent.add_widget(group)
        return field

    def current_values(self) -> tuple:
        return (
            self.company.text,
            self.role.text,
            self.field_of_work.text,
            self.status.text,
            tuple(self.links),
            self.link_input.text,
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
        popup = _dialog(
            title="Unsaved changes", content=layout, size_hint=(None, None), size=(dp(380), dp(180))
        )
        buttons.add_widget(_button("Keep editing", popup.dismiss))

        def discard():
            popup.dismiss()
            action()

        buttons.add_widget(_button("Discard", discard, kind="danger"))
        layout.add_widget(buttons)
        popup.open()

    def new(self) -> None:
        self.guard_changes(self.clear_form)

    def clear_form(self) -> None:
        self.selected = None
        self.heading.text = "New application"
        self.update_actions()
        for field in (
            self.company,
            self.role,
            self.field_of_work,
            self.link_input,
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
        self.links = []
        self.refresh_links()
        self.files = []
        self.refresh_files()
        self.tabs.switch_to(self.overview_tab)
        self.baseline = self.current_values()
        self.refresh_list()

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
        self.update_actions()
        self.company.text, self.role.text, self.status.text = (
            record.company,
            record.role,
            record.status,
        )
        self.field_of_work.text = record.field_of_work
        self.links = [item.strip() for item in record.url.splitlines() if item.strip()]
        self.link_input.text = ""
        self.refresh_links()
        self.summary.text, self.hints.text = record.summary, record.hints
        self.location.text = record.location
        self.contact_name.text = record.contact_name
        self.contact_email.text = record.contact_email
        self.contact_phone.text = record.contact_phone
        self.show_timestamps(record)
        self.files = list(record.files)
        self.refresh_files()
        self.tabs.switch_to(self.overview_tab)
        self.baseline = self.current_values()
        self.refresh_list()

    def refresh_list(self) -> None:
        self.list_box.clear_widgets()
        try:
            records = self.service.list(self.search.text)
        except Exception as exc:
            self.show_error(exc)
            return
        if not self.show_done:
            records = [record for record in records if record.status != "Done"]
        self.list_heading.text = f"Applications  ·  {len(records)}"
        if not records:
            self.list_box.add_widget(_label("No applications to show", height=46, color=MUTED))
        for record in records:
            label = f"{record.company}  ·  {record.role}"
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(96), spacing=dp(4))
            selected = self.selected is not None and self.selected.id == record.id
            select_button = _button(
                label,
                lambda record_id=record.id: self.select(record_id),
                height=52,
                kind="selected" if selected else "secondary",
            )
            select_button.halign = "left"
            select_button.valign = "middle"
            select_button.shorten = True
            select_button.shorten_from = "right"
            select_button.padding = (dp(10), 0)
            select_button.bind(
                size=lambda item, *_: setattr(item, "text_size", (item.width - dp(20), item.height))
            )
            row.add_widget(select_button)
            details = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            details.add_widget(_label(record.status, height=40, size=12, color=MUTED))
            done_button = _button(
                "Done",
                lambda record_id=record.id: self.mark_done(record_id),
                width=56,
                height=40,
                kind="success",
            )
            done_button.font_size = dp(12)
            done_button.disabled = record.status == "Done"
            details.add_widget(done_button)
            delete_button = _button(
                "Delete",
                lambda record_id=record.id: self.confirm_delete(record_id),
                width=56,
                height=40,
                kind="danger_outline",
            )
            delete_button.font_size = dp(12)
            details.add_widget(delete_button)
            row.add_widget(details)
            self.list_box.add_widget(row)

    def refresh_files(self) -> None:
        self.files_box.clear_widgets()
        if not self.files:
            self.files_box.add_widget(_label("No files linked yet", height=42))
        for path in self.files:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            row.add_widget(_button(Path(path).name, lambda item=path: self.open_file(item)))
            row.add_widget(_button("×", lambda item=path: self.remove_file(item), width=42))
            self.files_box.add_widget(row)

    def refresh_links(self) -> None:
        self.links_box.clear_widgets()
        if not self.links:
            self.links_box.add_widget(_label("No links added yet", height=42))
        for index, link in enumerate(self.links):
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
            open_button = _button(link, lambda value=link: self.open_link(value))
            open_button.halign = "left"
            open_button.shorten = True
            open_button.bind(
                width=lambda button, width: setattr(button, "text_size", (width - dp(16), None))
            )
            row.add_widget(open_button)
            row.add_widget(
                _button("×", lambda position=index: self.remove_link(position), width=42)
            )
            self.links_box.add_widget(row)

    def add_link(self) -> bool:
        link = self.link_input.text.strip()
        if not link:
            return False
        if any(character.isspace() for character in link) or not link.startswith(
            ("https://", "http://")
        ):
            self.show_error(ValueError("Enter one http:// or https:// link without spaces"))
            return False
        if link in self.links:
            self.show_error(ValueError("This link is already in the list"))
            return False
        if len(self.links) >= 10 or len("\n".join((*self.links, link))) > 2000:
            self.show_error(ValueError("Use at most 10 links totaling 2000 characters"))
            return False
        self.links.append(link)
        self.link_input.text = ""
        self.refresh_links()
        return True

    def remove_link(self, index: int) -> None:
        self.links.pop(index)
        self.refresh_links()

    def choose_file(self) -> None:
        chooser = FileChooserListView(path=str(Path.home()), filters=[])
        layout = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        layout.add_widget(chooser)
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = _dialog(title="Choose a file", content=layout, size_hint=(0.85, 0.85))
        buttons.add_widget(_button("Cancel", popup.dismiss))

        def add():
            if chooser.selection:
                selected = Path(chooser.selection[0]).resolve()
                if self.add_file(selected):
                    popup.dismiss()

        buttons.add_widget(_button("Add", add, kind="primary"))
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
        if self.add_file(Path(os.fsdecode(filename))):
            self.tabs.switch_to(self.files_tab)

    def remove_file(self, path: str) -> None:
        self.files.remove(path)
        self.refresh_files()

    def form_input(self) -> ApplicationInput:
        return ApplicationInput(
            company=self.company.text,
            role=self.role.text,
            field_of_work=self.field_of_work.text,
            status=self.status.text,
            url="\n".join(self.links),
            summary=self.summary.text,
            hints=self.hints.text,
            files=tuple(self.files),
            location=self.location.text,
            contact_name=self.contact_name.text,
            contact_email=self.contact_email.text,
            contact_phone=self.contact_phone.text,
        )

    def update_actions(self) -> None:
        self.create_button.disabled = self.selected is not None
        self.update_button.disabled = self.selected is None

    def create_application(self) -> None:
        if self.selected is None:
            self.save_record(self.service.create)

    def update_application(self) -> None:
        if self.selected is not None:
            record_id = self.selected.id
            self.save_record(lambda data: self.service.update(record_id, data))

    def save_record(self, operation) -> None:
        if self.link_input.text.strip() and not self.add_link():
            return
        self.link_input.text = ""
        try:
            record = operation(self.form_input())
        except Exception as exc:
            self.show_error(exc)
            return
        self.selected = record
        self.heading.text = f"Application #{record.id}"
        self.update_actions()
        self.show_timestamps(record)
        self.baseline = self.current_values()
        self.refresh_list()

    def mark_done(self, record_id: int) -> None:
        if self.selected is not None and self.selected.id == record_id:
            self.guard_changes(lambda: self.finish_mark_done(record_id))
        else:
            self.finish_mark_done(record_id)

    def finish_mark_done(self, record_id: int) -> None:
        try:
            self.service.mark_done(record_id)
        except Exception as exc:
            self.show_error(exc)
            return
        if self.selected is not None and self.selected.id == record_id:
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
                    height=72,
                    shorten=False,
                )
            )
        scroll = _scroll_view()
        scroll.add_widget(rows)
        layout.add_widget(scroll)
        popup = _dialog(title="Change history", content=layout, size_hint=(0.82, 0.75))
        layout.add_widget(_button("Close", popup.dismiss))
        popup.open()

    def confirm_delete(self, record_id: int) -> None:
        try:
            record = self.service.get(record_id)
        except Exception as exc:
            self.show_error(exc)
            return
        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        layout.add_widget(
            Label(text=f"Delete {record.company} · {record.role}?\nLinked files stay on disk.")
        )
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = _dialog(
            title="Delete application",
            content=layout,
            size_hint=(None, None),
            size=(dp(460), dp(180)),
        )
        buttons.add_widget(_button("Cancel", popup.dismiss))

        def delete():
            popup.dismiss()

            def apply_delete():
                try:
                    self.service.delete(record_id)
                except Exception as exc:
                    self.show_error(exc)
                    return
                if self.selected is not None and self.selected.id == record_id:
                    self.clear_form()
                self.refresh_list()

            if self.selected is not None and self.selected.id == record_id:
                self.guard_changes(apply_delete)
            else:
                apply_delete()

        buttons.add_widget(_button("Delete", delete, kind="danger"))
        layout.add_widget(buttons)
        popup.open()

    def open_link(self, link: str) -> None:
        if not link.startswith(("https://", "http://")):
            self.show_error(ValueError("Links must begin with https:// or http://"))
            return
        webbrowser.open(link)

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
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        layout.add_widget(label)
        popup = _dialog(
            title=title, content=layout, size_hint=(None, None), size=(dp(540), dp(220))
        )
        layout.add_widget(_button("Close", popup.dismiss, kind="primary"))
        popup.open()
