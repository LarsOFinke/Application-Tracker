from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationInput:
    company: str
    role: str
    status: str
    url: str
    summary: str
    hints: str
    files: tuple[str, ...] = ()
    field_of_work: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    location: str = ""
