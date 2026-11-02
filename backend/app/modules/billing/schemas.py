from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.payments.schemas import PaymentOut
from app.shared.schemas import ORMModel


class BillItemOut(ORMModel):
    id: UUID
    description_snapshot: str
    quantity: int
    unit_price_minor: int
    tax_minor: int
    line_total_minor: int


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


class PublicBillItemOut(BaseModel):
    name: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int
    currency_code: str


class PublicBillOut(BaseModel):
    bill_id: str
    status: str
    currency_code: str
    subtotal_minor: int
    tax_minor: int
    total_minor: int
    paid_minor: int
    balance_due_minor: int
    items: list[PublicBillItemOut]
    payments: list[dict]
