from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import ORMModel


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


# Backed by `_validate_code` in services/tables.py: the raw input is trimmed and
# uppercased there so " t7 " still works; the stored value matches this pattern.
_TABLE_CODE_MAX = 32


class TableCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_code: str = Field(min_length=1, max_length=_TABLE_CODE_MAX)
    display_name: str = Field(min_length=1, max_length=80)
    seating_capacity: int | None = Field(default=None, ge=1, le=40)
    sort_order: int | None = None
    branch_id: UUID | None = Field(default=None, description="Branch ID; defaults to restaurant_id")


class TableUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    seating_capacity: int | None = Field(default=None, ge=1, le=40)
    sort_order: int | None = Field(default=None, ge=0, le=1000)
    status: str | None = Field(default=None, pattern=r"^(ACTIVE|OUT_OF_SERVICE)$")


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
    # Plan 08 — waiter claim picture for the order queue.
    claim_state: str = ""
    claimed_by_membership_id: UUID | None = None
    claimed_at: datetime | None = None
    claim_timeout_at: datetime | None = None
    escalated_by_membership_id: UUID | None = None
    escalated_at: datetime | None = None
    items: list[OrderItemOut]
    subtotal_minor: int = 0
    tax_minor: int = 0
    total_minor: int = 0
    currency_code: str = ""


class CreateWaiterOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: UUID
    items: list[OrderItemIn] = Field(min_length=1, max_length=40)
    customer_note: str = Field(default="", max_length=280)


class RejectOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(min_length=2, max_length=64)
    note: str = Field(default="", max_length=280)


class EscalateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(default="", max_length=280)


class CancelOrderRequest(BaseModel):
    reason: str = Field(default="", max_length=140)


class RateOrderRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=280)


class SubmitQrOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OrderItemIn] = Field(min_length=1, max_length=40)
    customer_note: str = Field(default="", max_length=280)


class SubmitQrOrderResponse(BaseModel):
    order: OrderOut
    status_token: str
    message: str = "Submitted — awaiting staff confirmation"


class PublicOrderStatusOut(BaseModel):
    order_id: UUID
    status: str
    restaurant_name: str
    table_display_name: str
    submitted_at: str
    accepted_at: str | None
    rejected_at: str | None
    rejection_note: str
    items: list[dict]
    total_minor: int
    currency_code: str


# ── Dashboard / Sales Analytics ──────────────────────────────────────────────

class DashboardRevenueOut(BaseModel):
    total_revenue_minor: int
    total_revenue_display: str  # formatted for display


class DashboardOrdersOut(BaseModel):
    total_orders: int
    orders_by_status: dict


class DashboardDailySalesOut(BaseModel):
    day: str
    revenue_minor: int


class DashboardBestDishesOut(BaseModel):
    dish: str
    total_quantity: int
    revenue_minor: int


class DashboardPeriodSummaryOut(BaseModel):
    period_days: int
    total_revenue_minor: int
    total_orders: int
    daily_breakdown: list[DashboardDailySalesOut]
