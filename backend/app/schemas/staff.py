from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel, OrderItemIn


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


class TableUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    seating_capacity: int | None = Field(default=None, ge=1, le=40)
    sort_order: int | None = Field(default=None, ge=0, le=1000)
    status: str | None = Field(default=None, pattern=r"^(ACTIVE|OUT_OF_SERVICE)$")


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


class RecordPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_id: UUID
    amount_minor: int = Field(ge=1)
    note: str = Field(default="", max_length=120)


class PaymentMethodOut(BaseModel):
    id: UUID
    label: str
    kind: str
    account_hint: str
    instructions: str
    is_active: bool
    display_order: int
    has_qr_image: bool
    qr_image_url: str | None = None


class PaymentMethodWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    kind: str = Field(pattern=r"^(CASH|QR)$")
    account_hint: str = Field(default="", max_length=160)
    instructions: str = Field(default="", max_length=500)
    is_active: bool = True
    display_order: int = Field(default=0, ge=0, le=1000)


class PaymentMethodPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=80)
    account_hint: str | None = Field(default=None, max_length=160)
    instructions: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0, le=1000)


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


class MenuItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    current_price_minor: int = Field(ge=0)
    category_id: UUID
    status: str = "PUBLISHED"
    ingredients_text: str = Field(default="", max_length=500)
    image_emoji: str = Field(default="", max_length=8)
    image_path: str = Field(
        default="",
        max_length=255,
        pattern=r"^$|^/menu/food/[A-Za-z0-9._-]+\.(webp|jpg|jpeg|png|avif)$",
    )
    model_path: str = Field(
        default="",
        max_length=255,
        pattern=r"^$|^/menu/models/[A-Za-z0-9._-]+\.glb$",
    )


class MenuItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    current_price_minor: int | None = Field(default=None, ge=0)
    status: str | None = None
    ingredients_text: str | None = Field(default=None, max_length=500)
    image_emoji: str | None = None
    image_path: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^$|^/menu/food/[A-Za-z0-9._-]+\.(webp|jpg|jpeg|png|avif)$",
    )
    model_path: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^$|^/menu/models/[A-Za-z0-9._-]+\.glb$",
    )


class RestaurantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    currency_code: str
    tax_rate_bps: int
    qr_ordering_enabled: bool


class AuditEventOut(ORMModel):
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
