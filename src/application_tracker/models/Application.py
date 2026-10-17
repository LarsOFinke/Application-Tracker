from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from application_tracker.models.Base import Base

if TYPE_CHECKING:
    from application_tracker.models.FileReference import FileReference


class Application(Base):
    __tablename__ = "application"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str]
    role: Mapped[str]
    status: Mapped[str]
    url: Mapped[str] = mapped_column(default="")
    summary: Mapped[str] = mapped_column(default="")
    hints: Mapped[str] = mapped_column(default="")
    contact_name: Mapped[str] = mapped_column(default="")
    contact_email: Mapped[str] = mapped_column(default="")
    contact_phone: Mapped[str] = mapped_column(default="")
    location: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)
    files: Mapped[list[FileReference]] = relationship(
        back_populates="application", cascade="all, delete-orphan", order_by="FileReference.id"
    )
