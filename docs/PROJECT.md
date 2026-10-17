# Project brief and architecture

## First useful outcome

Keep a personal list of possible applications and reopen it after restarting the app. The first complete flow is create → add a file reference → save → restart → search → edit status and hints → inspect history → back up. This is a single-user, offline prototype, with no hosting or remote API.

## Design

`Kivy UI → ApplicationService → SQLAlchemy sessions → SQLite` is the whole runtime path. `ui/TrackerApp.py` owns the editor and chooses **Save new** or **Update** from the selected record. `services/ApplicationService.py` exposes separate `create` and `update` operations and owns transactions and audit events. `services/ApplicationMapper.py` normalizes and validates `ApplicationInput` at both service entry points, then maps ORM rows to `ApplicationData` for the UI. `models/` owns the SQLAlchemy classes, and `storage/database.py` owns schema initialization, upgrades, and backup. Each class has a PascalCase file. The UI never issues SQL. The direct local boundary follows AI Project Toolkit's local desktop profile.

The database lives outside the repository. `APPLICATION_TRACKER_DB` overrides the XDG default path. Schema version is stored in SQLite `user_version`. Startup creates schema 2 for a fresh database. Version 1 is upgraded in place after a consistent SQLite backup is written beside the database; contact columns and the audit table are added without removing old entries or file references. Existing version 1 changes have no reconstructed audit entries. Future versions and an unversioned `application` table are rejected. File paths are absolute references. The app owns the references, never the source files.

Validation requires company and role, limits text and file counts, checks optional email format, and accepts only HTTP(S) job links. Each saved change and its audit events share one transaction. Audit details retain old and new company, role, and status, but record only that free-text or contact fields changed. File events store a filename rather than its full path. A no-change save creates no event and leaves `updated_at` intact. Deletion keeps its audit history using an application ID without a foreign key. Timestamps use local computer time. A failed save leaves the editor content visible. Switching entries asks before discarding unsaved changes. Disk work is synchronous because each operation is a small local query; revisit this when a large dataset or slow volume causes visible pauses.

Done is a regular persisted status. The UI hides Done entries by default and can show them again; the service keeps all entries available for search and history. Mark done saves current form values with the status change, then clears the editor. The Scale selector rebuilds the Kivy controls at the chosen density while preserving the current form and selection; `ui.ini` beside the database stores that preference. Exit uses the same unsaved-change guard as switching entries.

## Quality checks

Run `make quality` with a supported `PYTHON_BIN` and installed dev dependencies for mapper normalization and rejection, distinct create/update behavior, a SQLite create/edit/reopen/delete journey, Done status, scale preference, validation rollback, file audit, version 1 migration, backup restoration, future-schema rejection, and Ruff. A real Kivy event-loop smoke exercised saving, marking done, filtering, and changing between normal and 200% density without losing unsaved form content on 2026-10-17. Visual layout, mouse-based chooser, and physical drag-and-drop still need manual inspection on the target desktop.

`make compile` uses PyInstaller to create one Linux executable, wraps it in an AppDir, and produces an AppImage with checksum-verified `appimagetool`. It extracts the embedded runtime from that tool so packaging needs no separate runtime download. The script runs version and bundled-import checks on the finished artifact. Build command output is stored in `build/logs/`; successful steps print a short tail, and failed steps print the last 80 lines. GitHub Actions runs quality on pull requests and builds/uploads the x86-64 AppImage on `main` or manual dispatch. A full installed GUI journey on another Linux machine is not covered by those checks.

## Next slices

Potential refinements after use: due dates and reminders, multiple named links, attachment relinking, more status filters, and a safer guided restore. Add them only if the personal workflow needs them.
