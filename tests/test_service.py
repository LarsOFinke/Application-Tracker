import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from application_tracker.services.ApplicationInput import ApplicationInput
from application_tracker.services.ApplicationMapper import ApplicationMapper
from application_tracker.services.ApplicationService import ApplicationService
from application_tracker.storage.database import backup_database, make_session_factory


def form(**changes):
    fields = dict(
        company="Example GmbH",
        role="Engineer",
        status="Interested",
        url="https://example.org/job",
        summary="Interesting role",
        hints="Ask about remote work",
        files=(),
    )
    fields.update(changes)
    return ApplicationInput(**fields)


def test_create_edit_reopen_and_delete_preserves_linked_file(tmp_path):
    database = tmp_path / "tracker.sqlite3"
    attachment = tmp_path / "resume.pdf"
    attachment.write_bytes(b"private example")
    service = ApplicationService(make_session_factory(database))
    created = service.create(form(files=(str(attachment),)))
    assert created.files == (str(attachment),)
    assert created.created_at == created.updated_at
    assert [event.action for event in service.history(created.id)] == ["file_added", "created"]

    reopened = ApplicationService(make_session_factory(database))
    assert reopened.get(created.id).summary == "Interesting role"
    updated = reopened.update(
        created.id,
        form(
            status="Applied",
            hints="Follow up on Monday",
            url="https://example.org/job\nhttps://example.org/company",
            contact_name="Ada Lovelace",
            contact_email="ada@example.org",
            contact_phone="+49 30 123456",
            location="Berlin",
        ),
    )
    assert updated.status == "Applied"
    assert updated.contact_email == "ada@example.org"
    assert updated.updated_at >= created.updated_at
    assert len(updated.url.splitlines()) == 2
    assert reopened.get(created.id).location == "Berlin"
    assert any(
        event.action == "status_changed" and event.detail == "Status: Interested → Applied"
        for event in reopened.history(created.id)
    )
    assert [item.id for item in reopened.list("applied")] == [created.id]
    assert [item.id for item in reopened.list("Ada")] == [created.id]
    history_count = len(reopened.history(created.id))
    reopened.update(
        created.id,
        form(
            status="Applied",
            hints="Follow up on Monday",
            url="https://example.org/job\nhttps://example.org/company",
            contact_name="Ada Lovelace",
            contact_email="ada@example.org",
            contact_phone="+49 30 123456",
            location="Berlin",
        ),
    )
    assert reopened.get(created.id).updated_at == updated.updated_at
    assert len(reopened.history(created.id)) == history_count
    reopened.delete(created.id)
    assert reopened.list() == []
    assert attachment.read_bytes() == b"private example"
    assert reopened.history(created.id)[0].action == "deleted"


def test_invalid_input_does_not_change_record(tmp_path):
    service = ApplicationService(make_session_factory(tmp_path / "tracker.sqlite3"))
    created = service.create(form())
    with pytest.raises(ValueError, match="Company and role"):
        service.update(created.id, form(company=" "))
    with pytest.raises(ValueError, match="links beginning"):
        service.update(created.id, form(url="file:///secret"))
    with pytest.raises(ValueError, match="contact email"):
        service.update(created.id, form(contact_email="not-an-email"))
    assert service.get(created.id).company == "Example GmbH"
    assert len(service.history(created.id)) == 1


def test_mapper_normalizes_input_and_rejects_bad_status(tmp_path):
    path = tmp_path / "resume.pdf"
    mapped = ApplicationMapper.normalize(
        form(
            company="  Example GmbH  ",
            role="  Engineer ",
            contact_email="  ada@example.org  ",
            url=" https://example.org/job  \n\n https://example.org/team ",
            files=(str(path), str(path)),
        )
    )
    assert mapped.company == "Example GmbH"
    assert mapped.role == "Engineer"
    assert mapped.contact_email == "ada@example.org"
    assert mapped.url == "https://example.org/job\nhttps://example.org/team"
    assert mapped.files == (str(path),)
    with pytest.raises(ValueError, match="valid status"):
        ApplicationMapper.normalize(form(status="Unknown"))


def test_create_and_update_are_distinct_operations(tmp_path):
    service = ApplicationService(make_session_factory(tmp_path / "tracker.sqlite3"))
    with pytest.raises(ValueError, match="Company and role"):
        service.create(form(company=" "))
    assert service.list() == []
    first = service.create(form(company="  Example GmbH  "))
    assert first.company == "Example GmbH"
    second = service.create(form(company="Second Co"))
    assert first.id != second.id
    with pytest.raises(ValueError, match="no longer exists"):
        service.update(999, form(company="Changed"))
    changed = service.update(first.id, form(company="Changed"))
    assert changed.id == first.id
    assert len(service.list()) == 2
    assert service.get(second.id).company == "Second Co"


def test_file_removal_is_logged_without_deleting_file(tmp_path):
    attachment = tmp_path / "resume.pdf"
    attachment.write_bytes(b"keep")
    service = ApplicationService(make_session_factory(tmp_path / "tracker.sqlite3"))
    created = service.create(form(files=(str(attachment),)))
    service.update(created.id, form(files=()))
    assert service.history(created.id)[0].detail == "resume.pdf"
    assert service.history(created.id)[0].action == "file_removed"
    assert attachment.read_bytes() == b"keep"


def test_backup_restores_data_and_future_schema_is_rejected(tmp_path):
    database = tmp_path / "tracker.sqlite3"
    service = ApplicationService(make_session_factory(database))
    created = service.create(form())
    backup = backup_database(database, tmp_path / "backups" / "snapshot.sqlite3")
    restored = ApplicationService(make_session_factory(backup))
    assert restored.get(created.id).role == "Engineer"

    with pytest.raises(FileExistsError):
        backup_database(database, backup)
    with restored.sessions.begin() as session:
        session.execute(text("PRAGMA user_version=99"))
    with pytest.raises(RuntimeError, match="newer"):
        make_session_factory(backup)
    assert Path(backup).exists()


def test_version_one_database_migrates_and_keeps_data(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE application (
                id INTEGER PRIMARY KEY, company VARCHAR NOT NULL, role VARCHAR NOT NULL,
                status VARCHAR NOT NULL, url VARCHAR NOT NULL, summary VARCHAR NOT NULL,
                hints VARCHAR NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL
            );
            CREATE TABLE file_reference (
                id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL REFERENCES application(id),
                path VARCHAR NOT NULL
            );
            INSERT INTO application VALUES (
                1, 'Legacy Co', 'Designer', 'Interested', '', 'Old summary', '',
                '2026-01-01 12:00:00', '2026-01-02 12:00:00'
            );
            INSERT INTO file_reference VALUES (1, 1, '/tmp/old.pdf');
            PRAGMA user_version=1;
        """)
    service = ApplicationService(make_session_factory(database))
    old = service.get(1)
    assert (old.company, old.files, old.contact_email) == ("Legacy Co", ("/tmp/old.pdf",), "")
    assert service.history(1) == []
    snapshots = list((tmp_path / "backups").glob("before-schema-2-*.sqlite3"))
    assert len(snapshots) == 1
    with sqlite3.connect(snapshots[0]) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT company FROM application").fetchone()[0] == "Legacy Co"
    service.update(
        1,
        form(
            company="Legacy Co",
            role="Designer",
            status="Applied",
            url="",
            summary="Old summary",
            hints="",
            files=("/tmp/old.pdf",),
        ),
    )
    assert service.history(1)[0].detail == "Status: Interested → Applied"
