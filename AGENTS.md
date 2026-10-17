# Application Tracker working guide

Read `README.md` and `docs/PROJECT.md` before changing behavior. Keep this a small offline desktop app. The UI in `ui/TrackerApp.py` calls the separate `create` and `update` operations in `services/ApplicationService.py`. `services/ApplicationMapper.py` owns normalization and validation for both; the service owns transactions and audit events; `storage/database.py` owns SQLite upgrades and backups. SQLAlchemy models live in `models/`. Keep each class in a matching PascalCase file. Preserve existing user data and linked source files. Never commit personal databases or attachments.

Run `make quality PYTHON_BIN=<supported-python>` in an environment with dev dependencies. `make dev` owns the source run; `make compile` owns the Linux AppImage and CI calls it under Xvfb. For UI changes, check the real Kivy event loop at normal and 200% display scale before claiming the UI verified. Keep commands and known limits current in the docs.
