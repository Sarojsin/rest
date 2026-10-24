from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import OrderStatus, PaymentStatus
from app.models.billing import Payment
from app.models.identity import Restaurant
from app.models.orders import Order
from app.schemas.staff import AuditEventOut, SalesReportOut
from app.models.audit import AuditEvent


def sales_report(db: Session, restaurant_id: UUID) -> SalesReportOut:
    restaurant = db.get(Restaurant, restaurant_id)
    orders = db.scalars(
        select(Order).options(selectinload(Order.items)).where(Order.restaurant_id == restaurant_id)
    ).unique().all()
    payments = db.scalars(select(Payment).where(Payment.restaurant_id == restaurant_id)).all()
    counts: dict[str, int] = defaultdict(int)
    gross = 0
    tax = 0
    item_sales: dict[str, dict] = {}
    for order in orders:
        counts[order.status] += 1
        if order.status in {OrderStatus.ACCEPTED, OrderStatus.COMPLETED}:
            for item in order.items:
                gross += item.unit_price_minor * item.quantity
                tax += item.tax_minor
                bucket = item_sales.setdefault(
                    item.item_name_snapshot, {"name": item.item_name_snapshot, "quantity": 0, "sales_minor": 0}
                )
                bucket["quantity"] += item.quantity
                bucket["sales_minor"] += item.unit_price_minor * item.quantity
    collected = sum(p.amount_minor for p in payments if p.status == PaymentStatus.SUCCEEDED)
    outstanding = max(gross + tax - collected, 0)
    top_items = sorted(item_sales.values(), key=lambda x: x["sales_minor"], reverse=True)[:5]
    return SalesReportOut(
        currency_code=restaurant.currency_code if restaurant else "USD",
        order_count=len(orders),
        accepted_order_count=counts[OrderStatus.ACCEPTED] + counts[OrderStatus.COMPLETED],
        cancelled_order_count=counts[OrderStatus.CANCELLED] + counts[OrderStatus.REJECTED],
        gross_sales_minor=gross,
        tax_minor=tax,
        collected_minor=collected,
        outstanding_minor=outstanding,
        top_items=top_items,
    )


def list_audit(db: Session, restaurant_id: UUID, limit: int = 50) -> list[AuditEventOut]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.restaurant_id == restaurant_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [AuditEventOut.model_validate(row) for row in rows]
