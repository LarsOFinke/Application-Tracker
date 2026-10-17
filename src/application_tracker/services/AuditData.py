from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditData:
    application_id: int
    happened_at: datetime
    action: str
    detail: str
