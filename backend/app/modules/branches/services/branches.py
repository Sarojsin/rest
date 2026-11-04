from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.branches.models import (
    Branch,
    BranchDashboardSummary,
    BranchManager,
    BranchSalesReport,
    BranchTable,
)
from app.modules.branches.schemas import (
    BranchDashboardSummaryIn,
    BranchDashboardSummaryOut,
    BranchIn,
    BranchManagerOut,
    BranchOut,
    BranchSalesReportIn,
    BranchSalesReportOut,
    BranchTableIn,
    BranchTableOut,
    BranchUpdateIn,
    OwnerDashboardSummaryOut,
)
from app.shared.errors import AppError


def _branch_out(branch: Branch) -> BranchOut:
    manager_name = None
    if branch.manager is not None and branch.manager.user is not None:
        manager_name = branch.manager.user.name
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
        settings_json=branch.settings_json or {},
        owner_membership_id=branch.owner_membership_id,
        restaurant_name=branch.restaurant.name if branch.restaurant else None,
        manager_name=manager_name,
    )


# ── Branch ──────────────────────────────────────────────────────────────────

def list_branches(
    db: Session,
    restaurant_id: UUID,
    active_only: bool = False,
) -> list[BranchOut]:
    stmt = select(Branch).where(Branch.restaurant_id == restaurant_id)
    if active_only:
        stmt = stmt.where(Branch.is_active.is_(True))
    branches = db.scalars(stmt.order_by(Branch.name)).all()
    return [_branch_out(b) for b in branches]


def get_branch(db: Session, branch_id: UUID, restaurant_id: UUID) -> BranchOut | None:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != restaurant_id:
        return None
    return _branch_out(branch)


def create_branch(db: Session, actor, payload: BranchIn) -> BranchOut:
    if actor.membership.role not in {"owner", "manager"}:
        raise AppError(
            403, "PERMISSION_DENIED", "Insufficient permissions",
            "Only owners and managers can create branches.",
        )

    existing = db.scalar(
        select(Branch).where(
            Branch.restaurant_id == actor.restaurant_id, Branch.name == payload.name
        )
    )
    if existing:
        raise AppError(
            409, "BRANCH_NAME_EXISTS", "Branch name in use",
            "A branch with this name already exists.",
        )

    if payload.code:
        existing_code = db.scalar(
            select(Branch).where(
                Branch.restaurant_id == actor.restaurant_id,
                Branch.code == payload.code,
            )
        )
        if existing_code:
            raise AppError(
                409, "BRANCH_CODE_EXISTS", "Branch code in use",
                "A branch with this code already exists.",
            )

    branch = Branch(
        restaurant_id=actor.restaurant_id,
        name=payload.name,
        code=payload.code,
        address=payload.address,
        phone=payload.phone,
        timezone=payload.timezone,
        currency_code=payload.currency_code,
        is_active=payload.is_active,
        opening_hours=payload.opening_hours,
        settings_json=payload.settings_json or {},
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return _branch_out(branch)


def update_branch(
    db: Session, actor, branch_id: UUID, payload: BranchUpdateIn
) -> BranchOut:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != actor.restaurant_id:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)

    if payload.name is not None:
        dup = db.scalar(
            select(Branch).where(
                Branch.restaurant_id == actor.restaurant_id,
                Branch.name == payload.name,
                Branch.id != branch_id,
            )
        )
        if dup:
            raise AppError(
                409, "BRANCH_NAME_EXISTS", "Branch name in use",
                "A branch with this name already exists.",
            )

    db.commit()
    db.refresh(branch)
    return _branch_out(branch)


# ── Branch Table ────────────────────────────────────────────────────────────

def list_branch_tables(
    db: Session, branch_id: UUID, include_archived: bool = False
) -> list[BranchTableOut]:
    stmt = select(BranchTable).where(BranchTable.branch_id == branch_id)
    if not include_archived:
        stmt = stmt.where(BranchTable.status != "ARCHIVED")
    tables = db.scalars(stmt.order_by(BranchTable.table_code)).all()
    return [BranchTableOut.model_validate(t) for t in tables]


def create_branch_table(
    db: Session, branch: Branch, payload: BranchTableIn
) -> BranchTableOut:
    existing = db.scalar(
        select(BranchTable).where(
            BranchTable.branch_id == branch.id,
            BranchTable.table_code == payload.table_code,
        )
    )
    if existing:
        raise AppError(
            409, "TABLE_CODE_EXISTS", "Table code in use",
            "A table with this code already exists in this branch.",
        )

    table = BranchTable(
        branch_id=branch.id,
        table_code=payload.table_code,
        display_name=payload.display_name,
        seating_capacity=payload.seating_capacity,
        status=payload.status or "ACTIVE",
        qr_code_active=payload.qr_code_active,
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return BranchTableOut.model_validate(table)


def get_branch_table(
    db: Session, table_id: UUID, branch_id: UUID
) -> BranchTableOut | None:
    table = db.get(BranchTable, table_id)
    if table is None or table.branch_id != branch_id:
        return None
    return BranchTableOut.model_validate(table)


# ── Branch Manager ────────────────────────────────────────────────────────

def list_branch_managers(db: Session, branch_id: UUID) -> list[BranchManagerOut]:
    managers = db.scalars(
        select(BranchManager)
        .where(BranchManager.branch_id == branch_id)
        .order_by(BranchManager.assigned_at)
    ).all()
    return [BranchManagerOut.model_validate(m) for m in managers]


def assign_branch_manager(
    db: Session, actor, branch_id: UUID, target_membership_id: UUID
) -> BranchManagerOut:
    if actor.membership.role not in {"owner", "manager"}:
        raise AppError(
            403, "PERMISSION_DENIED", "Insufficient permissions",
            "Only owners and managers can assign branch managers.",
        )

    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != actor.restaurant_id:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")

    # Membership lookup without importing the tenancy module (raw SQL keeps
    # the bounded-context import graph unchanged).
    membership_restaurant = db.execute(
        text("SELECT restaurant_id FROM restaurant_memberships WHERE id = :id"),
        {"id": target_membership_id},
    ).scalar_one_or_none()
    if membership_restaurant is None or membership_restaurant != actor.restaurant_id:
        raise AppError(
            404, "MEMBERSHIP_NOT_FOUND", "Not found", "Membership was not found."
        )

    existing = db.scalar(
        select(BranchManager).where(
            BranchManager.branch_id == branch_id,
            BranchManager.membership_id == target_membership_id,
        )
    )
    if existing:
        raise AppError(
            409, "MANAGER_ALREADY_ASSIGNED", "Manager already assigned",
            "This membership is already a branch manager.",
        )

    manager = BranchManager(
        branch_id=branch_id,
        membership_id=target_membership_id,
        role="MANAGER",
        assigned_at=datetime.now(UTC),
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return BranchManagerOut.model_validate(manager)


# ── Branch Sales Report ───────────────────────────────────────────────────

def list_sales_reports(
    db: Session, branch_id: UUID, limit: int = 30
) -> list[BranchSalesReportOut]:
    reports = db.scalars(
        select(BranchSalesReport)
        .where(BranchSalesReport.branch_id == branch_id)
        .order_by(BranchSalesReport.report_date.desc())
        .limit(limit)
    ).all()
    return [BranchSalesReportOut.model_validate(r) for r in reports]


def create_sales_report(
    db: Session, branch: Branch, payload: BranchSalesReportIn
) -> BranchSalesReportOut:
    report = BranchSalesReport(
        branch_id=branch.id,
        report_date=payload.report_date or datetime.now(UTC),
        total_sales_minor=payload.total_sales_minor,
        total_orders=payload.total_orders,
        total_orders_completed=payload.total_orders_completed,
        total_orders_pending=payload.total_orders_pending,
        total_revenue_minor=payload.total_revenue_minor or payload.total_sales_minor,
        average_ticket_minor=payload.average_ticket_minor
        or (
            payload.total_sales_minor // payload.total_orders
            if payload.total_orders
            else 0
        ),
        payment_breakdown=payload.payment_breakdown or {},
        notes=payload.notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return BranchSalesReportOut.model_validate(report)


def generate_branch_sales_report(
    db: Session, branch: Branch, start_date: datetime, end_date: datetime
) -> BranchSalesReportOut:
    """Build a report from orders over the given window.

    Orders are linked to a branch through the shared table code (the QR table
    registry and the branch table registry use the same codes). When a branch
    has no registered tables yet the query falls back to the whole restaurant,
    which is correct for single-branch tenants.
    """
    branch_table_count = db.execute(
        text("SELECT COUNT(*) FROM branch_tables WHERE branch_id = :bid"),
        {"bid": branch.id},
    ).scalar_one()

    if branch_table_count:
        rows = db.execute(
            text(
                """
                SELECT o.status, COALESCE(SUM(oi.line_total_minor), 0), o.table_id
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.restaurant_id = :rid
                  AND o.submitted_at >= :start
                  AND o.submitted_at < :end
                  AND o.table_id IN (
                      SELECT rt.id
                      FROM restaurant_tables rt
                      JOIN branch_tables bt
                        ON bt.table_code = rt.table_code
                       AND bt.branch_id = :bid
                  )
                GROUP BY o.id, o.status, o.table_id
                """
            ),
            {
                "rid": branch.restaurant_id,
                "start": start_date,
                "end": end_date,
                "bid": branch.id,
            },
        ).all()
    else:
        rows = db.execute(
            text(
                """
                SELECT o.status, COALESCE(SUM(oi.line_total_minor), 0), o.table_id
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.restaurant_id = :rid
                  AND o.submitted_at >= :start
                  AND o.submitted_at < :end
                GROUP BY o.id, o.status, o.table_id
                """
            ),
            {"rid": branch.restaurant_id, "start": start_date, "end": end_date},
        ).all()

    total_sales = 0
    total_orders = 0
    completed = 0
    pending = 0
    for status, total_minor, _table_id in rows:
        total_orders += 1
        if status == "COMPLETED":
            completed += 1
        elif status in {"PENDING_CONFIRMATION", "ACCEPTED"}:
            pending += 1
        total_sales += total_minor or 0

    report = BranchSalesReport(
        branch_id=branch.id,
        report_date=datetime.now(UTC),
        total_sales_minor=total_sales,
        total_orders=total_orders,
        total_orders_completed=completed,
        total_orders_pending=pending,
        total_revenue_minor=total_sales,
        average_ticket_minor=total_sales // total_orders if total_orders else 0,
        payment_breakdown={},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return BranchSalesReportOut.model_validate(report)


# ── Branch Dashboard Summary ──────────────────────────────────────────────

def create_dashboard_summary(
    db: Session, branch: Branch, payload: BranchDashboardSummaryIn
) -> BranchDashboardSummaryOut:
    summary = BranchDashboardSummary(
        branch_id=branch.id,
        summary_date=datetime.now(UTC),
        total_revenue_minor=payload.total_revenue_minor,
        total_orders=payload.total_orders,
        average_rating=payload.average_rating,
        low_stock_count=payload.low_stock_count,
        active_tables=payload.active_tables,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return BranchDashboardSummaryOut.model_validate(summary)


def get_branch_dashboard(
    db: Session, branch: Branch
) -> BranchDashboardSummaryOut:
    latest_report = db.scalars(
        select(BranchSalesReport)
        .where(BranchSalesReport.branch_id == branch.id)
        .order_by(BranchSalesReport.report_date.desc())
        .limit(1)
    ).first()

    active_tables = db.execute(
        text(
            "SELECT COUNT(*) FROM branch_tables "
            "WHERE branch_id = :bid AND status = 'ACTIVE'"
        ),
        {"bid": branch.id},
    ).scalar_one()

    low_stock = db.execute(
        text(
            "SELECT COUNT(*) FROM ingredients "
            "WHERE restaurant_id = :rid AND status = 'LOW_STOCK'"
        ),
        {"rid": branch.restaurant_id},
    ).scalar_one_or_none() or 0

    summary = BranchDashboardSummary(
        branch_id=branch.id,
        summary_date=datetime.now(UTC),
        total_revenue_minor=latest_report.total_sales_minor if latest_report else 0,
        total_orders=latest_report.total_orders if latest_report else 0,
        average_rating=None,
        low_stock_count=low_stock,
        active_tables=active_tables,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return BranchDashboardSummaryOut.model_validate(summary)


# ── Owner Dashboard ───────────────────────────────────────────────────────

def owner_dashboard(db: Session, restaurant_id: UUID) -> OwnerDashboardSummaryOut:
    restaurant_name = db.execute(
        text("SELECT name FROM restaurants WHERE id = :id"), {"id": restaurant_id}
    ).scalar_one_or_none() or ""

    branches = db.scalars(
        select(Branch)
        .where(Branch.restaurant_id == restaurant_id)
        .order_by(Branch.name)
    ).all()

    total_revenue = 0
    total_orders = 0
    active_branch_count = 0
    branch_summaries: list[BranchDashboardSummaryOut] = []

    for branch in branches:
        report = db.scalars(
            select(BranchSalesReport)
            .where(BranchSalesReport.branch_id == branch.id)
            .order_by(BranchSalesReport.report_date.desc())
            .limit(1)
        ).first()
        if branch.is_active:
            active_branch_count += 1
        total_revenue += report.total_sales_minor if report else 0
        total_orders += report.total_orders if report else 0

        active_tables = db.execute(
            text(
                "SELECT COUNT(*) FROM branch_tables "
                "WHERE branch_id = :bid AND status = 'ACTIVE'"
            ),
            {"bid": branch.id},
        ).scalar_one()

        branch_summaries.append(
            BranchDashboardSummaryOut(
                id=branch.id,
                branch_id=branch.id,
                summary_date=datetime.now(UTC),
                total_revenue_minor=report.total_sales_minor if report else 0,
                total_revenue_display=(
                    f"{(report.total_sales_minor if report else 0) / 100:.2f}"
                ),
                total_orders=report.total_orders if report else 0,
                average_rating=None,
                low_stock_count=0,
                active_tables=active_tables,
            )
        )

    return OwnerDashboardSummaryOut(
        restaurant_name=restaurant_name,
        total_revenue_minor=total_revenue,
        total_revenue_display=f"{total_revenue / 100:.2f}",
        total_orders=total_orders,
        branch_count=len(branches),
        active_branch_count=active_branch_count,
        branches=branch_summaries,
    )


__all__ = [
    "list_branches",
    "get_branch",
    "create_branch",
    "update_branch",
    "list_branch_tables",
    "create_branch_table",
    "get_branch_table",
    "list_branch_managers",
    "assign_branch_manager",
    "list_sales_reports",
    "create_sales_report",
    "generate_branch_sales_report",
    "create_dashboard_summary",
    "get_branch_dashboard",
    "owner_dashboard",
]
