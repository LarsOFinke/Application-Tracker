"""Explicit create/update operations and their audit transactions."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from application_tracker.models import Application, AuditEvent, FileReference
from application_tracker.services.ApplicationData import ApplicationData
from application_tracker.services.ApplicationInput import ApplicationInput
from application_tracker.services.ApplicationMapper import ApplicationMapper
from application_tracker.services.AuditData import AuditData

LABELS = {
    "company": "Company",
    "role": "Role",
    "status": "Status",
    "url": "Links",
    "summary": "Summary",
    "hints": "Hints",
    "contact_name": "Contact name",
    "contact_email": "Contact email",
    "contact_phone": "Contact phone",
    "location": "Location",
}


class ApplicationService:
    def __init__(self, sessions: sessionmaker):
        self.sessions = sessions

    def list(self, query: str = "") -> list[ApplicationData]:
        with self.sessions() as session:
            records = session.scalars(
                select(Application)
                .options(selectinload(Application.files))
                .order_by(Application.updated_at.desc(), Application.id.desc())
            ).all()
            needle = query.strip().casefold()
            return [
                ApplicationMapper.to_data(record)
                for record in records
                if not needle
                or needle
                in " ".join(
                    (record.company, record.role, record.status, record.contact_name)
                ).casefold()
            ]

    def get(self, record_id: int) -> ApplicationData:
        with self.sessions() as session:
            record = session.scalar(
                select(Application)
                .options(selectinload(Application.files))
                .where(Application.id == record_id)
            )
            if record is None:
                raise ValueError("Application no longer exists")
            return ApplicationMapper.to_data(record)

    def history(self, record_id: int | None = None) -> list[AuditData]:
        with self.sessions() as session:
            query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)
            if record_id is not None:
                query = query.where(AuditEvent.application_id == record_id)
            return [
                AuditData(item.application_id, item.happened_at, item.action, item.detail)
                for item in session.scalars(query)
            ]

    def create(self, raw: ApplicationInput) -> ApplicationData:
        data = ApplicationMapper.normalize(raw)
        values = asdict(data)
        paths = values.pop("files")
        now = datetime.now()
        with self.sessions.begin() as session:
            record = Application(**values, created_at=now, updated_at=now)
            record.files = [FileReference(path=path) for path in paths]
            session.add(record)
            session.flush()
            events = [("created", f"{data.company} · {data.role}")]
            events.extend(("file_added", Path(path).name) for path in paths)
            self._add_events(session, record.id, now, events)
            return ApplicationMapper.to_data(record)

    def update(self, record_id: int, raw: ApplicationInput) -> ApplicationData:
        data = ApplicationMapper.normalize(raw)
        values = asdict(data)
        paths = values.pop("files")
        now = datetime.now()
        with self.sessions.begin() as session:
            record = session.scalar(
                select(Application)
                .options(selectinload(Application.files))
                .where(Application.id == record_id)
            )
            if record is None:
                raise ValueError("Application no longer exists")
            events = []
            for key, value in values.items():
                old = getattr(record, key)
                if old != value:
                    detail = (
                        f"{LABELS[key]}: {old} → {value}"
                        if key in {"company", "role", "status"}
                        else f"{LABELS[key]} updated"
                    )
                    events.append(("status_changed" if key == "status" else "changed", detail))
                    setattr(record, key, value)
            old_paths = {item.path for item in record.files}
            new_paths = set(paths)
            events.extend(("file_added", Path(path).name) for path in sorted(new_paths - old_paths))
            events.extend(
                ("file_removed", Path(path).name) for path in sorted(old_paths - new_paths)
            )
            if new_paths != old_paths:
                record.files = [FileReference(path=path) for path in paths]
            if events:
                record.updated_at = now
                self._add_events(session, record.id, now, events)
            session.flush()
            return ApplicationMapper.to_data(record)

    @staticmethod
    def _add_events(
        session: Session, record_id: int, now: datetime, events: list[tuple[str, str]]
    ) -> None:
        session.add_all(
            AuditEvent(application_id=record_id, happened_at=now, action=action, detail=detail)
            for action, detail in events
        )

    def delete(self, record_id: int) -> None:
        with self.sessions.begin() as session:
            record = session.get(Application, record_id)
            if record is None:
                raise ValueError("Application no longer exists")
            self._add_events(
                session,
                record_id,
                datetime.now(),
                [("deleted", f"{record.company} · {record.role}")],
            )
            session.delete(record)
