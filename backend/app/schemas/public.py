from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrderItemIn, OrderOut


class PublicMenuItem(BaseModel):
    id: UUID
    name: str
    description: str
    current_price_minor: int
    currency_code: str
    status: str
    display_order: int
    image_emoji: str
    image_path: str = Field(default="", max_length=255)
    model_path: str = Field(default="", max_length=255)
    ingredients_text: str = Field(default="", max_length=500)


class PublicMenuCategory(BaseModel):
    id: UUID
    name: str
    description: str
    display_order: int
    items: list[PublicMenuItem]


class PublicMenuOut(BaseModel):
    restaurant_name: str
    currency_code: str
    table_id: UUID
    table_display_name: str
    qr_ordering_enabled: bool
    categories: list[PublicMenuCategory]


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
    table_display_name: str
    submitted_at: str
    accepted_at: str | None
    rejected_at: str | None
    rejection_note: str
    items: list[dict]
    total_minor: int
    currency_code: str


class PublicServiceCallOut(BaseModel):
    id: UUID
    status: str
    requested_at: str
    acknowledged_at: str | None
    deduplicated: bool = False
