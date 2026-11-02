from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ServiceCallOut(BaseModel):
    id: UUID
    kind: str = "GUEST"
    table_id: UUID
    table_display_name: str
    ticket_number: int | None = None
    items_summary: str = ""
    status: str
    requested_at: datetime
    acknowledged_at: datetime | None


class PublicServiceCallOut(BaseModel):
    id: UUID
    status: str
    requested_at: str
    acknowledged_at: str | None
    deduplicated: bool = False
