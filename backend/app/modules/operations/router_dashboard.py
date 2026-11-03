"""Operations module dashboard router — sales analytics and reports."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.operations.schemas import (
    DashboardBestDishesOut,
    DashboardDailySalesOut,
    DashboardOrdersOut,
    DashboardPeriodSummaryOut,
    DashboardRevenueOut,
)
from app.modules.operations.services.dashboard import (
    best_selling_dishes,
    daily_sales,
    orders_by_status,
    revenue_last_n_days,
    total_orders,
    total_revenue,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/revenue", response_model=DashboardRevenueOut)
def get_total_revenue(db: Session = Depends(get_db)) -> DashboardRevenueOut:
    """Get total revenue across all completed orders."""
    rev = total_revenue(db)
    # Format as dollars assuming minor units = cents; adjust if different currency
    display = f"{rev / 100:.2f}" if rev else "0.00"
    return DashboardRevenueOut(total_revenue_minor=rev, total_revenue_display=display)


@router.get("/orders", response_model=DashboardOrdersOut)
def get_order_summary(
    status: str | None = Query(default=None, description="Filter by order status"),
    db: Session = Depends(get_db),
) -> DashboardOrdersOut:
    """Get order count summary, optionally filtered by status."""
    count = total_orders(db, status=status)
    status_breakdown = orders_by_status(db) if not status else {status: count}
    return DashboardOrdersOut(total_orders=count, orders_by_status=status_breakdown)


@router.get("/sales/daily", response_model=list[DashboardDailySalesOut])
def get_daily_sales(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[DashboardDailySalesOut]:
    """Get daily revenue for the last N days."""
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)
    data = daily_sales(db, start_date, end_date)
    return [
        DashboardDailySalesOut(day=d["day"], revenue_minor=d["revenue"]) for d in data
    ]


@router.get("/best-dishes", response_model=list[DashboardBestDishesOut])
def get_best_selling_dishes(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[DashboardBestDishesOut]:
    """Get top-selling dishes by quantity."""
    rows = best_selling_dishes(db, limit=limit)
    return [
        DashboardBestDishesOut(
            dish=r["dish"],
            total_quantity=r["total_quantity"],
            revenue_minor=r["revenue"],
        )
        for r in rows
    ]


@router.get("/period-summary", response_model=DashboardPeriodSummaryOut)
def get_period_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> DashboardPeriodSummaryOut:
    """Get summary for a given period (last N days)."""
    summary = revenue_last_n_days(db, n=days)
    daily = [
        DashboardDailySalesOut(day=d["day"], revenue_minor=d["revenue"])
        for d in summary["daily_breakdown"]
    ]
    return DashboardPeriodSummaryOut(
        period_days=summary["period_days"],
        total_revenue_minor=summary["total_revenue_minor"],
        total_orders=summary["total_orders"],
        daily_breakdown=daily,
    )