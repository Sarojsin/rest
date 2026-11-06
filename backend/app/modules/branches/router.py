from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    Actor,
    consume_tenant_limit,
    require_permission,
    require_permission_and_consume_limit,
    require_tenant_feature,
)
from app.db.session import get_db
from app.modules.branches.models import Branch
from app.modules.branches.schemas import (
    BranchDashboardSummaryIn,
    BranchDashboardSummaryOut,
    BranchIn,
    BranchManagerIn,
    BranchManagerOut,
    BranchOut,
    BranchSalesReportIn,
    BranchSalesReportOut,
    BranchTableIn,
    BranchTableOut,
    BranchUpdateIn,
    OwnerDashboardSummaryOut,
)
from app.modules.branches.services import branches as branch_service
from app.shared.errors import AppError

router = APIRouter(tags=["branches"])


def _branch(db: Session, actor: Actor, branch_id: UUID) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.restaurant_id != actor.restaurant_id:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")
    return branch


@router.get("", response_model=list[BranchOut])
def list_branches(
    active_only: bool = Query(default=False),
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> list[BranchOut]:
    return branch_service.list_branches(db, actor.restaurant_id, active_only)


@router.post("", response_model=BranchOut, status_code=201)
def create_branch(
    payload: BranchIn,
    actor: Actor = Depends(
        require_permission_and_consume_limit("branches.create", "branches")
    ),
    db: Session = Depends(get_db),
) -> BranchOut:
    return branch_service.create_branch(db, actor, payload)


@router.get("/dashboard/owner", response_model=OwnerDashboardSummaryOut)
def owner_dashboard(
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> OwnerDashboardSummaryOut:
    return branch_service.owner_dashboard(db, actor.restaurant_id)


@router.get("/{branch_id}", response_model=BranchOut)
def get_branch(
    branch_id: UUID,
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> BranchOut:
    result = branch_service.get_branch(db, branch_id, actor.restaurant_id)
    if result is None:
        raise AppError(404, "BRANCH_NOT_FOUND", "Not found", "Branch was not found.")
    return result


@router.patch("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: UUID,
    payload: BranchUpdateIn,
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchOut:
    return branch_service.update_branch(db, actor, branch_id, payload)


# ── Tables ──────────────────────────────────────────────────────────────────

@router.get("/{branch_id}/tables", response_model=list[BranchTableOut])
def list_tables(
    branch_id: UUID,
    include_archived: bool = Query(default=False),
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> list[BranchTableOut]:
    _branch(db, actor, branch_id)
    return branch_service.list_branch_tables(db, branch_id, include_archived)


@router.post(
    "/{branch_id}/tables",
    response_model=BranchTableOut,
    status_code=201,
    dependencies=[
        Depends(require_tenant_feature("qr_ordering")),
        Depends(consume_tenant_limit("tables")),
    ],
)
def create_table(
    branch_id: UUID,
    payload: BranchTableIn,
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchTableOut:
    return branch_service.create_branch_table(db, _branch(db, actor, branch_id), payload)


# ── Managers ────────────────────────────────────────────────────────────────

@router.get("/{branch_id}/managers", response_model=list[BranchManagerOut])
def list_managers(
    branch_id: UUID,
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> list[BranchManagerOut]:
    _branch(db, actor, branch_id)
    return branch_service.list_branch_managers(db, branch_id)


@router.post("/{branch_id}/managers", response_model=BranchManagerOut, status_code=201)
def assign_manager(
    branch_id: UUID,
    payload: BranchManagerIn,
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchManagerOut:
    return branch_service.assign_branch_manager(
        db, actor, branch_id, payload.membership_id
    )


# ── Sales reports ───────────────────────────────────────────────────────────

@router.get("/{branch_id}/reports/sales", response_model=list[BranchSalesReportOut])
def list_sales_reports(
    branch_id: UUID,
    limit: int = Query(default=30, ge=1, le=365),
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> list[BranchSalesReportOut]:
    _branch(db, actor, branch_id)
    return branch_service.list_sales_reports(db, branch_id, limit)


@router.post("/{branch_id}/reports/sales", response_model=BranchSalesReportOut, status_code=201)
def create_sales_report(
    branch_id: UUID,
    payload: BranchSalesReportIn,
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchSalesReportOut:
    return branch_service.create_sales_report(db, _branch(db, actor, branch_id), payload)


@router.post("/{branch_id}/reports/sales/generate", response_model=BranchSalesReportOut)
def generate_sales_report(
    branch_id: UUID,
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchSalesReportOut:
    now = datetime.now(UTC)
    start = start_date or now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end_date or now
    return branch_service.generate_branch_sales_report(
        db, _branch(db, actor, branch_id), start, end
    )


# ── Dashboard ───────────────────────────────────────────────────────────────

@router.get("/{branch_id}/dashboard", response_model=BranchDashboardSummaryOut)
def branch_dashboard(
    branch_id: UUID,
    actor: Actor = Depends(require_permission("branches.read")),
    db: Session = Depends(get_db),
) -> BranchDashboardSummaryOut:
    return branch_service.get_branch_dashboard(db, _branch(db, actor, branch_id))


@router.post(
    "/{branch_id}/dashboard", response_model=BranchDashboardSummaryOut, status_code=201
)
def create_dashboard_summary(
    branch_id: UUID,
    payload: BranchDashboardSummaryIn,
    actor: Actor = Depends(require_permission("branches.update")),
    db: Session = Depends(get_db),
) -> BranchDashboardSummaryOut:
    return branch_service.create_dashboard_summary(
        db, _branch(db, actor, branch_id), payload
    )
