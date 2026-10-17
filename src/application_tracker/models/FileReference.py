from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from application_tracker.models.Base import Base

if TYPE_CHECKING:
    from application_tracker.models.Application import Application


class FileReference(Base):
    __tablename__ = "file_reference"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"))
    path: Mapped[str]
    application: Mapped[Application] = relationship(back_populates="files")
