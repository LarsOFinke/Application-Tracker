"""Installed command entry point."""

from application_tracker.ui.TrackerApp import TrackerApp


def main() -> None:
    TrackerApp().run()


if __name__ == "__main__":
    main()
