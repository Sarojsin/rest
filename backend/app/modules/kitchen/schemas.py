from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.schemas import ORMModel


class KitchenTicketItemOut(ORMModel):
    id: UUID
    order_item_id: UUID
    status: str
    quantity_snapshot: int
    instructions_snapshot: str
    item_name: str | None = None
    table_display_name: str | None = None


class KitchenTicketOut(ORMModel):
    id: UUID
    order_id: UUID
    ticket_number: int
    status: str
    created_at: datetime
    started_at: datetime | None
    ready_at: datetime | None
    table_display_name: str | None = None
    items: list[KitchenTicketItemOut]


class KitchenItemStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
