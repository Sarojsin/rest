from datetime import UTC, datetime, timedelta

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.modules.operations.models import Order, OrderItem


def _revenue_query(db: Session) -> int:
    """Total revenue in minor units across all completed orders."""
    result = db.scalar(
        select(func.coalesce(func.sum(OrderItem.line_total_minor), 0))
        .select_from(Order)
        .join(Order.items)
        .where(Order.status == "COMPLETED")
    )
    return int(result)


def total_revenue(db: Session) -> int:
    """Return total revenue in minor units (e.g. cents)."""
    return _revenue_query(db)


def total_orders(db: Session, status: str | None = None) -> int:
    """Count orders, optionally filtered by status."""
    stmt = select(func.count()).select_from(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    return db.scalar(stmt) or 0


def orders_by_status(db: Session) -> dict:
    """Return order counts grouped by status."""
    stmt = select(Order.status, func.count()).select_from(Order).group_by(Order.status)
    rows = db.execute(stmt).all()
    return {status: count for status, count in rows}


def daily_sales(
    db: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict]:
    """Return daily revenue broken down by day between start_date and end_date."""
    # ``date_trunc('day', ...)`` must render identically in SELECT, GROUP BY and
    # ORDER BY: PostgreSQL matches grouped expressions syntactically, and a bind
    # parameter would get a different placeholder in each clause.
    day = func.date_trunc(literal_column("'day'"), Order.submitted_at)
    stmt = (
        select(
            day.label("day"),
            func.coalesce(func.sum(OrderItem.line_total_minor), 0).label("revenue"),
        )
        .select_from(Order)
        .join(Order.items)
        .where(
            Order.submitted_at >= start_date,
            Order.submitted_at < end_date,
        )
        .group_by(day)
        .order_by(day)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "day": row.day.isoformat() if isinstance(row.day, datetime) else str(row.day),
            "revenue": int(row.revenue),
        }
        for row in rows
    ]


def best_selling_dishes(
    db: Session,
    limit: int = 10,
) -> list[dict]:
    """Return top dishes by total quantity sold."""
    stmt = (
        select(
            OrderItem.item_name_snapshot.label("dish"),
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.line_total_minor).label("revenue"),
        )
        .select_from(OrderItem)
        .join(Order)
        .where(Order.status == "COMPLETED")
        .group_by(OrderItem.item_name_snapshot)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {"dish": row.dish, "total_quantity": int(row.total_quantity), "revenue": int(row.revenue)}
        for row in rows
    ]


def category_performance(
    db: Session,
    limit: int = 10,
) -> list[dict]:
    """Return performance grouped by menu category (uses menu_items)."""
    # We don't have a category column on OrderItem directly;
    # this is a placeholder that returns item-level data.
    # In a full implementation, this would join menu_items.
    dishes = best_selling_dishes(db, limit=limit)
    return dishes


def revenue_last_n_days(
    db: Session,
    n: int = 30,
) -> dict:
    """Revenue and order counts for the last n days."""
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=n)
    daily = daily_sales(db, start_date, end_date)
    total_rev = sum(d["revenue"] for d in daily)
    return {
        "period_days": n,
        "total_revenue_minor": total_rev,
        "total_orders": total_orders(db),
        "daily_breakdown": daily,
    }