from datetime import datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from application_tracker.models.Base import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_event_application_id_id", "application_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]  # No FK: history survives deletion of the application.
    happened_at: Mapped[datetime] = mapped_column(default=datetime.now)
    action: Mapped[str]
    detail: Mapped[str]
