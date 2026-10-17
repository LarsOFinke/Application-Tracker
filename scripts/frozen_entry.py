"""Entry point for the PyInstaller executable."""

import os
import sys

if __name__ == "__main__":
    if sys.argv[1:] == ["--version"]:
        print("Application Tracker 0.1.0")
    else:
        os.environ.setdefault("KIVY_NO_ARGS", "1")
        from application_tracker.app import main

        if sys.argv[1:] == ["--check-imports"]:
            print("Application Tracker imports OK")
        else:
            main()
