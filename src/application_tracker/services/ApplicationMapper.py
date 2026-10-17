"""Convert editor input and ORM rows into consistent application data."""

from __future__ import annotations

import re
from pathlib import Path

from application_tracker.models.Application import Application
from application_tracker.services.ApplicationData import ApplicationData
from application_tracker.services.ApplicationInput import ApplicationInput

STATUSES = ("Interested", "Preparing", "Applied", "Interview", "Offer", "Closed")


class ApplicationMapper:
    @staticmethod
    def normalize(raw: ApplicationInput) -> ApplicationInput:
        company, role = raw.company.strip(), raw.role.strip()
        contact_name = raw.contact_name.strip()
        contact_email = raw.contact_email.strip()
        contact_phone = raw.contact_phone.strip()
        location = raw.location.strip()
        if not company or not role:
            raise ValueError("Company and role are required")
        if raw.status not in STATUSES:
            raise ValueError("Choose a valid status")
        if any(len(value) > 200 for value in (company, role, contact_name, location)):
            raise ValueError("Company, role, contact name or location is too long")
        if len(contact_email) > 254 or (
            contact_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email)
        ):
            raise ValueError("Enter a valid contact email")
        if len(contact_phone) > 80:
            raise ValueError("Contact phone is too long")
        if len(raw.summary) > 20000 or len(raw.hints) > 20000:
            raise ValueError("Summary or hints is too long")
        links = [item.strip() for item in raw.url.splitlines() if item.strip()]
        if len(links) > 10 or any(not item.startswith(("https://", "http://")) for item in links):
            raise ValueError("Use at most 10 links beginning with https:// or http://")
        url = "\n".join(links)
        if len(url) > 2000:
            raise ValueError("Links are too long")
        paths = tuple(dict.fromkeys(str(Path(item).expanduser().resolve()) for item in raw.files))
        if len(paths) > 30 or any(len(path) > 4000 for path in paths):
            raise ValueError("Too many files or a file path is too long")
        return ApplicationInput(
            company=company,
            role=role,
            status=raw.status,
            url=url,
            summary=raw.summary,
            hints=raw.hints,
            files=paths,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            location=location,
        )

    @staticmethod
    def to_data(record: Application) -> ApplicationData:
        return ApplicationData(
            record.id,
            record.company,
            record.role,
            record.status,
            record.url,
            record.summary,
            record.hints,
            record.contact_name,
            record.contact_email,
            record.contact_phone,
            record.location,
            tuple(item.path for item in record.files),
            record.created_at,
            record.updated_at,
        )
