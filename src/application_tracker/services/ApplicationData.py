from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ApplicationData:
    id: int
    company: str
    role: str
    status: str
    url: str
    summary: str
    hints: str
    contact_name: str
    contact_email: str
    contact_phone: str
    location: str
    files: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
