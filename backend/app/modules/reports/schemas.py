from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.shared.schemas import ORMModel


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
