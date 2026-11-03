import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.branches.models import (
    Branch,
    BranchDashboardSummary,
    BranchManager,
    BranchSalesReport,
    BranchTable,
)
from app.shared.errors import AppError

# ── Branch ──────────────────────────────────────────────────────────────────

def list_branches(
    db: Session,
    restaurant_id: UUID,
    active_only: bool = True,
) -> list[BranchOut]:
    stmt = select(Branch).where(Branch.restaurant_id == restaurant_id)
    if active_only:
        stmt = stmt.where(Branch.is_active)
    branches = db.scalars(stmt.order_by(Branch.name)).all()
    return [
        BranchOut(
            id=b.id,
            name=b.name,
            code=b.code,
            address=b.address,
            phone=b.phone,
            timezone=b.timezone,
            currency_code=b.currency_code,
            is_active=b.is_active,
            opening_hours=b.opening_hours,
            settings_json=json.loads(b.settings_json) if b.settings_json else {},
            owner_membership_id=b.owner_membership_id,
            restaurant_name=b.restaurant.name if b.restaurant else None,
            manager_name=b.manager.user.name if b.manager and b.manager.user else None,
        )
        for b in branches
    ]


def get_branch(
    db: Session, branch_id: UUID, restaurant_id: UUID
) -> BranchOut | None:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != restaurant_id:
        return None
    return BranchOut(
        id=branch.id,
        name=branch.name,
        code=branch.code,
        address=branch.address,
        phone=branch.phone,
        timezone=branch.timezone,
        currency_code=branch.currency_code,
        is_active=branch.is_active,
        opening_hours=branch.opening_hours,
        settings_json=json.loads(branch.settings_json) if branch.settings_json else {},
        owner_membership_id=branch.owner_membership_id,
        restaurant_name=branch.restaurant.name if branch.restaurant else None,
        manager_name=branch.manager.user.name if branch.manager and branch.manager.user else None,
    )


def create_branch(
    db: Session,
    membership,
    payload: BranchIn,
) -> BranchOut:
    # Verify owner has permission
    if membership.role not in {"OWNER", "SUPER_ADMIN"}:
        raise AppError(403, "PERMISSION_DENIED", "Insufficient permissions", "Only owners can create branches.")

    # Check for duplicate name
    existing = db.scalar(
        select(Branch).where(Branch.restaurant_id == membership.restaurant_id, Branch.name == payload.name)
    )
    if existing:
        raise AppError(409, "BRANCH_NAME_EXISTS", "Branch name in use", "A branch with this name already exists.")

    branch = Branch(
        restaurant_id=membership.restaurant_id,
        name=payload.name,
        code=payload.code,
        address=payload.address,
        phone=payload.phone,
        timezone=payload.timezone,
        currency_code=payload.currency_code,
        is_active=payload.is_active,
        opening_hours=payload.opening_hours,
        settings_json=json.dumps(payload.settings_json) if payload.settings_json else "{}",
    )
    db.add(branch)
    db.flush()
    db.commit()
    return get_branch(db, branch.id, membership.restaurant_id)


# ── Branch Table ────────────────────────────────────────────────────────────

def list_branch_tables(
    db: Session,
    branch_id: UUID,
    include_archived: bool = False,
) -> list[BranchTableOut]:
    stmt = select(BranchTable).where(BranchTable.branch_id == branch_id)
    if not include_archived:
        stmt = stmt.where(BranchTable.status != "ARCHIVED")
    tables = db.scalars(stmt.order_by(BranchTable.table_code)).all()
    return [
        BranchTableOut(
            id=t.id,
            table_code=t.table_code,
            display_name=t.display_name,
            seating_capacity=t.seating_capacity,
            status=t.status,
            qr_code_active=t.qr_code_active,
        )
        for t in tables
    ]


def create_branch_table(
    db: Session,
    branch: Branch,
    payload: BranchTableIn,
) -> BranchTableOut:
    table = BranchTable(
        branch_id=branch.id,
        table_code=payload.table_code,
        display_name=payload.display_name,
        seating_capacity=payload.seating_capacity,
        status=payload.status or "ACTIVE",
        qr_code_active=payload.qr_code_active,
    )
    db.add(table)
    db.flush()
    db.commit()
    return get_branch_table(db, table.id, branch.id)


def get_branch_table(
    db: Session, table_id: UUID, branch_id: UUID
) -> BranchTableOut | None:
    table = db.get(BranchTable, table_id)
    if table is None or table.branch_id != branch_id:
        return None
    return BranchTableOut(
        id=table.id,
        table_code=table.table_code,
        display_name=table.display_name,
        seating_capacity=table.seating_capacity,
        status=table.status,
        qr_code_active=table.qr_code_active,
    )


# ── Branch Manager ────────────────────────────────────────────────────────

def list_branch_managers(
    db: Session,
    branch_id: UUID,
) -> list[BranchManagerOut]:
    stmt = select(BranchManager).where(BranchManager.branch_id == branch_id)
    managers = db.scalars(stmt.order_by(BranchManager.assigned_at)).all()
    return [
        BranchManagerOut(
            role=m.role,
            is_active=m.is_active,
            assigned_at=m.assigned_at,
        )
        for m in managers
    ]


def assign_branch_manager(
    db: Session,
    membership,
    branch_id: UUID,
    target_membership_id: UUID,
) -> BranchManagerOut:
    # Verify current user has permission
    if membership.role not in {"OWNER", "SUPER_ADMIN"}:
        raise AppError(403, "PERMISSION_DENIED", "Insufficient permissions", "Only owners can assign branch managers.")

    # Check branch exists
    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != membership.restaurant_id:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

    # Check target membership belongs to same restaurant
    target_membership = db.get(RestaurantMembership, target_membership_id)
    if target_membership is None or target_membership.restaurant_id != membership.restaurant_id:
        raise AppError(404, "MEMBERSHIP_NOT_FOUND", "Not found", "Membership was not found.")

    # Check if already assigned
    existing = db.scalar(
        select(BranchManager).where(
            BranchManager.branch_id == branch_id,
            BranchManager.membership_id == target_membership_id,
        )
    )
    if existing:
        raise AppError(409, "MANAGER_ALREADY_ASSIGNED", "Manager already assigned", "This membership is already a branch manager.")

    manager = BranchManager(
        branch_id=branch_id,
        membership_id=target_membership_id,
        role="MANAGER",
        assigned_at=datetime.now(UTC),
    )
    db.add(manager)
    db.flush()
    db.commit()
    return BranchManagerOut(
        role=manager.role,
        is_active=manager.is_active,
        assigned_at=manager.assigned_at,
    )


# ── Branch Sales Report ───────────────────────────────────────────────────

def generate_branch_sales_report(
    db: Session,
    branch_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> BranchSalesReportOut:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

    # Get orders for this branch in date range using raw SQL to avoid importing operations.models
    stmt = select(Order).where(
        Order.branch_id == branch_id,
        Order.created_at >= start_date,
        Order.created_at < end_date,
    )
    orders = db.scalars(stmt).all()

    total_sales = 0
    total_orders = 0
    total_orders_completed = 0
    total_orders_pending = 0
    payment_breakdown = {}

    for order in orders:
        total_orders += 1
        if order.status == "COMPLETED":
            total_orders_completed += 1
        elif order.status in {"PENDING_CONFIRMATION", "ACCEPTED"}:
            total_orders_pending += 1
        total_sales += order.total_minor or 0

        # Payment breakdown
        for payment in order.payments:
            if payment.status == "SUCCEEDED":
                method = payment.method
                payment_breakdown[method] = payment_breakdown.get(method, 0) + (payment.amount_minor or 0)

    avg_ticket = total_sales // total_orders if total_orders > 0 else 0

    report = BranchSalesReport(
        branch_id=branch_id,
        report_date=datetime.now(UTC),
        total_sales_minor=total_sales,
        total_sales_display=f"{total_sales / 100:.2f}",
        total_orders=total_orders,
        total_orders_completed=total_orders_completed,
        total_orders_pending=total_orders_pending,
        total_revenue_minor=total_sales,
        total_revenue_display=f"{total_sales / 100:.2f}",
        average_ticket_minor=avg_ticket,
        payment_breakdown=payment_breakdown,
    )

    db.add(report)
    db.flush()
    db.commit()
    return BranchSalesReportOut(
        id=report.id,
        report_date=report.report_date,
        total_sales_minor=report.total_sales_minor,
        total_sales_display=report.total_sales_display,
        total_orders=report.total_orders,
        total_orders_completed=report.total_orders_completed,
        total_orders_pending=report.total_orders_pending,
        total_revenue_minor=report.total_revenue_minor,
        total_revenue_display=report.total_revenue_display,
        average_ticket_minor=report.average_ticket_minor,
        payment_breakdown=report.payment_breakdown,
    )


# ── Branch Dashboard Summary ──────────────────────────────────────────────

def generate_branch_dashboard_summary(
    db: Session,
    branch_id: UUID,
) -> BranchDashboardSummaryOut:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

    # Get recent sales report
    report = db.scalars(
        select(BranchSalesReport).where(BranchSalesReport.branch_id == branch_id)
        .order_by(BranchSalesReport.report_date.desc())
        .limit(1)
    ).one_or_none()

    # Count active tables
    active_tables = db.scalar(
        select(BranchTable).where(
            BranchTable.branch_id == branch_id,
            BranchTable.status == "ACTIVE",
        )
    )

    # Count low stock ingredients - placeholder, would use inventory module
    low_stock_count = 0

    summary = BranchDashboardSummary(
        branch_id=branch_id,
        summary_date=datetime.now(UTC),
        total_revenue_minor=(report.total_sales_minor if report else 0),
        total_orders=(report.total_orders if report else 0),
        average_rating=None,  # placeholder
        low_stock_count=low_stock_count,
        active_tables=active_tables,
    )

    db.add(summary)
    db.flush()
    db.commit()
    return BranchDashboardSummaryOut(
        id=summary.id,
        summary_date=summary.summary_date,
        total_revenue_minor=summary.total_revenue_minor,
        total_revenue_display=f"{summary.total_revenue_minor / 100:.2f}",
        total_orders=summary.total_orders,
        average_rating=summary.average_rating,
        low_stock_count=summary.low_stock_count,
        active_tables=summary.active_tables,
    )


# ── Owner Dashboard ───────────────────────────────────────────────────────

def generate_owner_dashboard(
    db: Session,
    restaurant_id: UUID,
) -> OwnerDashboardSummaryOut:
    # Get all branches for this restaurant using raw query
    branches = db.scalars(
        select(Branch).where(Branch.restaurant_id == restaurant_id, Branch.is_active)
    ).all()

    total_revenue = 0
    total_orders = 0
    active_branch_count = 0
    branches_summary = []

    for branch in branches:
        # Get latest sales report via raw query
        report = db.scalar(
            select(BranchSalesReport).where(BranchSalesReport.branch_id == branch.id)
            .order_by(BranchSalesReport.report_date.desc())
            .limit(1)
        )

        if report:
            total_revenue += report.total_sales_minor
            total_orders += report.total_orders
            active_branch_count += 1

        branches_summary.append(
            {
                "id": branch.id,
                "summary_date": datetime.now(UTC),
                "total_revenue_minor": report.total_sales_minor if report else 0,
                "total_revenue_display": f"{report.total_sales_minor / 100:.2f}" if report else "0.00",
                "total_orders": report.total_orders if report else 0,
                "average_rating": None,
                "low_stock_count": 0,
                "active_tables": db.scalar(
                    select(BranchTable).where(
                        BranchTable.branch_id == branch.id,
                        BranchTable.status == "ACTIVE",
                    )
                ),
            }
        )

    return OwnerDashboardSummaryOut(
        restaurant_name="",  # would need restaurant lookup
        total_revenue_minor=total_revenue,
        total_revenue_display=f"{total_revenue / 100:.2f}",
        total_orders=total_orders,
        branch_count=len(branches),
        active_branch_count=active_branch_count,
        branches=branches_summary,
    )