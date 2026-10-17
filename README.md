# Application Tracker

A small, offline desktop app for keeping possible job applications in one place. Each entry has a company, role, status, location, optional contact name, email and phone, links, summary, hints or next steps, and file references. Search filters by company, role, status, or contact name.

## Run and build

Use Python 3.11–3.13 with Kivy 2.3.1. From this directory:

```bash
make dev
```

`make dev` creates `.venv` and installs the app and development checks when needed. It prefers a Python 3.11–3.13 executable on `PATH` and also detects the local Python 3.13 toolchain used by sibling projects. Set `PYTHON_BIN` to choose another supported interpreter, or `DEV_PYTHON` to run with an existing compatible environment. If an earlier run created `.venv` with unsupported Python 3.14, `make dev` replaces that disposable environment. `make test` and `make quality` use `.venv` by default; set `PYTHON_BIN` to use another environment with the development dependencies installed.

On Linux, `make compile` creates `dist/linux/ApplicationTracker-<arch>.AppImage` for x86-64 or arm64. It builds in `.build-venv` with PyInstaller and packages the executable with a checksum-verified `appimagetool`. The build downloads Python packages and `appimagetool` on first use, then uses the runtime embedded in that tool. Set `PYTHON_BIN` for the build interpreter. `BUILD_PYTHON`, `APPIMAGETOOL`, and `APPIMAGE_RUNTIME` can point to existing local tools for an offline build. The AppImage contains the Python runtime and app dependencies; run it directly after `chmod +x`.

GitHub Actions runs quality checks on pull requests. Pushes to `main` and manual **Actions → Linux AppImage → Run workflow** runs build and upload `application-tracker-linux-x86_64` as a downloadable artifact. The workflow builds only the Linux x86-64 AppImage. Installing and opening the artifact on another Linux machine remains a separate runtime check.

The database defaults to `$XDG_DATA_HOME/application-tracker/applications.sqlite3`, or `~/.local/share/application-tracker/applications.sqlite3` when `XDG_DATA_HOME` is unset. Set `APPLICATION_TRACKER_DB` to an absolute or home-relative SQLite path to use another location. Data stays on this computer; there is no server or account.

**Files are linked, not copied.** Use Add file or drop a file onto the window, then Save. Moving or deleting the original file breaks that link. Removing an entry or a file reference never deletes the file. The Backup button creates a consistent SQLite copy in a `backups/` folder beside the database. Backups include application details, audit history, and file paths, but not the linked files. To restore, close the app and replace the database with a backup; retain your original until you verify the restored copy. To move to another computer, copy the referenced files too and relink any paths that changed.

Use **Mark done** on a saved application to keep its record and history while removing it from the default list. **Show done** reveals completed entries again, so they can be reopened or deleted. **Delete** asks for confirmation and removes the record while keeping its linked files on disk and a deletion event in history. The **Scale** control offers 100–200% and saves the choice in `ui.ini` beside the database. **Exit** asks before discarding unsaved edits.

## Prototype scope

This version supports create, search, edit, mark done, delete, file links, up to ten web links per entry, contact details, a change history, and a one-click database backup. The editor shows **Save new** for a new entry and **Update** for an existing one. Created and updated times appear in the editor. History records status and main information changes, plus file references added or removed, when an entry is saved. It retains a deletion entry after the application is removed. The most recent 100 events are shown per application, or globally when no application is selected. It has no reminders, cloud sync, automatic application submission, or file copying. The database uses schema version 2 and upgrades version 1 after making a `before-schema-2-*` backup. It refuses a newer or unknown schema rather than replacing it. [Architecture and checks](docs/PROJECT.md) describe the design and known limits.
