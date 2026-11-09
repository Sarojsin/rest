from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.audit.models import AuditEvent
from app.modules.kitchen.models import KitchenTicket
from app.modules.operations.models import Order
from app.modules.payments.models import Payment
from app.modules.reports.schemas import AuditEventOut, SalesReportOut
from app.modules.tenancy.models import Restaurant
from app.shared.enums import OrderStatus, PaymentStatus


def sales_report(db: Session, restaurant_id: UUID) -> SalesReportOut:
    restaurant = db.get(Restaurant, restaurant_id)
    orders = (
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.restaurant_id == restaurant_id)
        )
        .unique()
        .all()
    )
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
                    item.item_name_snapshot,
                    {"name": item.item_name_snapshot, "quantity": 0, "sales_minor": 0},
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


def advanced_report(
    db: Session, restaurant_id: UUID, *, days: int = 30
) -> dict:
    """Composite report gated by the ``advanced_reports`` plan feature.

    Returns the standard sales summary plus a daily bucketed series and a few
    derived KPIs. Kept as a plain dict so the platform plan can evolve the
    payload without another response-model migration.
    """
    days = max(1, min(days, 365))
    since = datetime.now(UTC) - timedelta(days=days)

    orders = (
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.restaurant_id == restaurant_id, Order.submitted_at >= since)
        )
        .unique()
        .all()
    )

    daily: dict[str, dict[str, int]] = defaultdict(
        lambda: {"order_count": 0, "gross_sales_minor": 0}
    )
    for order in orders:
        day = order.submitted_at.date().isoformat()
        daily[day]["order_count"] += 1
        if order.status in {OrderStatus.ACCEPTED, OrderStatus.COMPLETED}:
            daily[day]["gross_sales_minor"] += sum(
                item.unit_price_minor * item.quantity for item in order.items
            )

    sales = sales_report(db, restaurant_id)
    accepted = sales.accepted_order_count
    average_order_minor = (
        round(sales.gross_sales_minor / accepted) if accepted else 0
    )

    return {
        "window_days": days,
        "currency_code": sales.currency_code,
        "sales": sales.model_dump(),
        "average_order_minor": average_order_minor,
        "daily": [
            {"date": day, **values} for day, values in sorted(daily.items())
        ],
    }


def list_audit(db: Session, restaurant_id: UUID, limit: int = 50) -> list[AuditEventOut]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.restaurant_id == restaurant_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [AuditEventOut.model_validate(row) for row in rows]


def payments_report(db: Session, restaurant_id: UUID, *, days: int = 30) -> dict:
    """Breakdown of recorded payments by configured method label.

    ``Payment.method`` stores the payment method config's label (e.g. "Cash"),
    which is unique per restaurant, so grouping on it is deterministic. Only
    succeeded payments count towards collected totals; failed ones are counted
    separately so the payment page can surface them.
    """
    days = max(1, min(days, 365))
    since = datetime.now(UTC) - timedelta(days=days)

    restaurant = db.get(Restaurant, restaurant_id)
    payments = (
        db.scalars(
            select(Payment).where(
                Payment.restaurant_id == restaurant_id,
                Payment.created_at >= since,
            )
        )
        .all()
    )

    methods: dict[str, dict] = {}
    succeeded_count = 0
    failed_count = 0
    for payment in payments:
        if payment.status == PaymentStatus.SUCCEEDED:
            succeeded_count += 1
            bucket = methods.setdefault(
                payment.method,
                {"method": payment.method, "payment_count": 0, "amount_minor": 0},
            )
            bucket["payment_count"] += 1
            bucket["amount_minor"] += payment.amount_minor
        elif payment.status == PaymentStatus.FAILED:
            failed_count += 1

    return {
        "window_days": days,
        "currency_code": restaurant.currency_code if restaurant else "USD",
        "total_collected_minor": sum(b["amount_minor"] for b in methods.values()),
        "succeeded_count": succeeded_count,
        "failed_count": failed_count,
        "methods": sorted(methods.values(), key=lambda b: b["amount_minor"], reverse=True),
    }


def kitchen_speed_report(db: Session, restaurant_id: UUID, *, days: int = 30) -> dict:
    """Ticket prep speed: created -> ready over the recent window.

    Only tickets that actually reached READY within the window count towards
    the stats; the slowest list helps spot bottlenecks without loading items.
    """
    days = max(1, min(days, 365))
    since = datetime.now(UTC) - timedelta(days=days)

    tickets = (
        db.scalars(
            select(KitchenTicket).where(
                KitchenTicket.restaurant_id == restaurant_id,
                KitchenTicket.ready_at.is_not(None),
                KitchenTicket.ready_at >= since,
            )
        )
        .all()
    )

    timed: list[dict] = []
    for ticket in tickets:
        ready = ticket.ready_at
        created = ticket.created_at
        if ready is None:
            continue
        # Some older rows stored naive datetimes; normalise to aware UTC so
        # subtraction and comparison are consistent regardless of how they were
        # persisted.
        if ready.tzinfo is None:
            ready = ready.replace(tzinfo=UTC)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if ready < created:
            continue
        prep_seconds = (ready - created).total_seconds()
        timed.append(
            {
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "status": ticket.status,
                "started_at": ticket.started_at,
                "ready_at": ticket.ready_at,
                "prep_seconds": prep_seconds,
            }
        )

    prep_seconds_list = [row["prep_seconds"] for row in timed]
    completed = len(timed)
    return {
        "window_days": days,
        "completed_ticket_count": completed,
        "avg_prep_seconds": round(sum(prep_seconds_list) / completed) if completed else 0,
        "fastest_prep_seconds": round(min(prep_seconds_list)) if completed else 0,
        "slowest_prep_seconds": round(max(prep_seconds_list)) if completed else 0,
        "slowest_tickets": sorted(timed, key=lambda r: r["prep_seconds"], reverse=True)[:10],
    }
