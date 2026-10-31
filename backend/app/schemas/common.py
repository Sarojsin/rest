from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoneyFields(BaseModel):
    amount_minor: int
    currency_code: str


class PaginatedMeta(BaseModel):
    total: int
    limit: int
    offset: int


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    menu_item_id: UUID
    quantity: int = Field(ge=1, le=50)
    special_instructions: str = Field(default="", max_length=280)


class OrderItemOut(ORMModel):
    id: UUID
    menu_item_id: UUID | None
    item_name_snapshot: str
    quantity: int
    unit_price_minor: int
    tax_minor: int
    line_total_minor: int
    currency_code: str
    special_instructions: str


class OrderOut(ORMModel):
    id: UUID
    table_id: UUID
    dining_session_id: UUID | None
    source: str
    status: str
    customer_note: str
    submitted_at: datetime
    accepted_at: datetime | None
    rejected_at: datetime | None
    rejection_reason_code: str | None
    rejection_note: str
    version: int
    items: list[OrderItemOut]
    subtotal_minor: int = 0
    tax_minor: int = 0
    total_minor: int = 0
    currency_code: str = ""


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


class BillItemOut(ORMModel):
    id: UUID
    description_snapshot: str
    quantity: int
    unit_price_minor: int
    tax_minor: int
    line_total_minor: int


class PaymentOut(ORMModel):
    id: UUID
    method: str
    status: str
    amount_minor: int
    currency_code: str
    note: str = ""
    created_at: datetime
    succeeded_at: datetime | None


class BillOut(ORMModel):
    id: UUID
    dining_session_id: UUID
    status: str
    currency_code: str
    subtotal_minor: int
    tax_minor: int
    total_minor: int
    paid_minor: int
    balance_due_minor: int
    version: int
    issued_at: datetime | None
    items: list[BillItemOut] = []
    payments: list[PaymentOut] = []
