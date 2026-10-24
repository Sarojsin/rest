from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrderItemIn


class TableOut(BaseModel):
    id: UUID
    table_code: str
    display_name: str
    seating_capacity: int | None
    status: str
    sort_order: int
    occupancy: str
    active_session_id: UUID | None
    pending_qr_count: int
    qr_token: str | None = None


class CreateWaiterOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: UUID
    items: list[OrderItemIn] = Field(min_length=1, max_length=40)
    customer_note: str = Field(default="", max_length=280)


class RejectOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(min_length=2, max_length=64)
    note: str = Field(default="", max_length=280)


class KitchenItemStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class CashPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_minor: int = Field(ge=1)
    note: str = Field(default="", max_length=120)


class MenuItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    current_price_minor: int = Field(ge=0)
    category_id: UUID
    status: str = "PUBLISHED"
    image_emoji: str = Field(default="", max_length=8)


class MenuItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    current_price_minor: int | None = Field(default=None, ge=0)
    status: str | None = None
    image_emoji: str | None = None


class RestaurantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    currency_code: str
    tax_rate_bps: int
    qr_ordering_enabled: bool


class AuditEventOut(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: str
    occurred_at: datetime
    detail: str


class SalesReportOut(BaseModel):
    currency_code: str
    order_count: int
    accepted_order_count: int
    cancelled_order_count: int
    gross_sales_minor: int
    tax_minor: int
    collected_minor: int
    outstanding_minor: int
    top_items: list[dict]
