from pydantic import BaseModel, Field


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


class CancelOrderRequest(BaseModel):
    reason: str = Field(default="", max_length=140)


class RateOrderRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=280)
