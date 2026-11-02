from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import ORMModel


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


class PaymentOut(ORMModel):
    id: UUID
    method: str
    status: str
    amount_minor: int
    currency_code: str
    note: str = ""
    created_at: datetime
    succeeded_at: datetime | None
