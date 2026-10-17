# Application Tracker

A small, offline desktop app for keeping possible job applications in one place. Each entry has a company, role, status, location, optional contact name, email and phone, links, summary, hints or next steps, and file references. Search filters by company, role, status, or contact name.

## Run and build

Use Python 3.11–3.13 with Kivy 2.3.1, or Python 3.14 with Kivy 3.0.0.dev0. From this directory:

```bash
make dev
```

`make dev` creates `.venv` and installs the app when needed. Set `PYTHON_BIN` to choose a supported interpreter, or `DEV_PYTHON` to run with an existing compatible environment. `make test` and `make quality` use `PYTHON_BIN` (default `python3`); that interpreter must have the development dependencies from `pip install -e '.[dev]'`.

On Linux, `make compile` creates `dist/linux/ApplicationTracker-<arch>.AppImage` for x86-64 or arm64. It builds in `.build-venv` with PyInstaller and packages the executable with a checksum-verified `appimagetool`. The build downloads Python packages, `appimagetool`, and its runtime on first use. Set `PYTHON_BIN` for the build interpreter. `BUILD_PYTHON`, `APPIMAGETOOL`, and `APPIMAGE_RUNTIME` can point to existing local tools for an offline build. The AppImage contains the Python runtime and app dependencies; run it directly after `chmod +x`.

GitHub Actions runs quality checks on pull requests. Pushes to `main` and manual **Actions → Linux AppImage → Run workflow** runs build and upload `application-tracker-linux-x86_64` as a downloadable artifact. The workflow builds only the Linux x86-64 AppImage. Installing and opening the artifact on another Linux machine remains a separate runtime check.

The database defaults to `$XDG_DATA_HOME/application-tracker/applications.sqlite3`, or `~/.local/share/application-tracker/applications.sqlite3` when `XDG_DATA_HOME` is unset. Set `APPLICATION_TRACKER_DB` to an absolute or home-relative SQLite path to use another location. Data stays on this computer; there is no server or account.

**Files are linked, not copied.** Use Add file or drop a file onto the window, then Save. Moving or deleting the original file breaks that link. Removing an entry or a file reference never deletes the file. The Backup button creates a consistent SQLite copy in a `backups/` folder beside the database. Backups include application details, audit history, and file paths, but not the linked files. To restore, close the app and replace the database with a backup; retain your original until you verify the restored copy. To move to another computer, copy the referenced files too and relink any paths that changed.

## Prototype scope

This version supports create, search, edit, delete, file links, up to ten web links per entry, contact details, a change history, and a one-click database backup. The editor shows **Save new** for a new entry and **Update** for an existing one. Created and updated times appear in the editor. History records status and main information changes, plus file references added or removed, when an entry is saved. It retains a deletion entry after the application is removed. The most recent 100 events are shown per application, or globally when no application is selected. It has no reminders, cloud sync, automatic application submission, or file copying. The database uses schema version 2 and upgrades version 1 after making a `before-schema-2-*` backup. It refuses a newer or unknown schema rather than replacing it. [Architecture and checks](docs/PROJECT.md) describe the design and known limits.
