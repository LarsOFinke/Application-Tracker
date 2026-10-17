"""SQLite initialization, version upgrades, and backups."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from application_tracker.models import Base

SCHEMA_VERSION = 3


def default_database_path() -> Path:
    override = os.environ.get("APPLICATION_TRACKER_DB")
    if override:
        return Path(override).expanduser().resolve()
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "application-tracker" / "applications.sqlite3"


def make_session_factory(path: Path) -> sessionmaker:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        with engine.begin() as connection:
            version = connection.execute(text("PRAGMA user_version")).scalar_one()
            if version > SCHEMA_VERSION:
                raise RuntimeError(f"Database schema {version} is newer than this app supports")
            if version == 0:
                existing = connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='application'")
                ).first()
                if existing:
                    raise RuntimeError(
                        "Unversioned application table found; database left unchanged"
                    )
                Base.metadata.create_all(connection)
                connection.execute(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
        if version in (1, 2):
            destination = (
                path.parent
                / "backups"
                / f"before-schema-{version + 1}-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3"
            )
            backup_database(path, destination)
            with engine.begin() as connection:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                if version == 1:
                    for column in ("contact_name", "contact_email", "contact_phone", "location"):
                        statement = f"ALTER TABLE application ADD COLUMN {column} VARCHAR NOT NULL "
                        connection.execute(text(statement + "DEFAULT ''"))
                    Base.metadata.tables["audit_event"].create(connection)
                connection.execute(
                    text(
                        "ALTER TABLE application ADD COLUMN field_of_work "
                        "VARCHAR NOT NULL DEFAULT ''"
                    )
                )
                connection.execute(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
    except Exception:
        engine.dispose()
        raise
    return sessionmaker(engine, expire_on_commit=False)


def backup_database(source: Path, destination: Path) -> Path:
    """Create a consistent SQLite snapshot without changing the live database."""
    source = Path(source).resolve()
    destination = Path(destination).expanduser().resolve()
    if source == destination:
        raise ValueError("Backup destination must differ from the live database")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    try:
        with sqlite3.connect(source) as live, sqlite3.connect(temporary) as snapshot:
            live.backup(snapshot)
            result = snapshot.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError(f"Backup integrity check failed: {result}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
