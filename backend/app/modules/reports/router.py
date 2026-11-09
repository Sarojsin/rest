from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission, require_tenant_feature
from app.db.session import get_db
from app.modules.reports.schemas import AuditEventOut, SalesReportOut
from app.modules.reports.services import reports as report_service

router = APIRouter(tags=["reports"])


@router.get("/reports/sales", response_model=SalesReportOut)
def sales(
    actor: Actor = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db),
) -> SalesReportOut:
    return report_service.sales_report(db, actor.restaurant_id)


@router.get("/reports/advanced")
def advanced(
    days: int = 30,
    actor: Actor = Depends(require_permission("reports.read")),
    _: Actor = Depends(require_tenant_feature("advanced_reports")),
    db: Session = Depends(get_db),
) -> dict:
    return report_service.advanced_report(db, actor.restaurant_id, days=days)


@router.get("/reports/payments")
def payments(
    days: int = 30,
    actor: Actor = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db),
) -> dict:
    return report_service.payments_report(db, actor.restaurant_id, days=days)


@router.get("/reports/kitchen-speed")
def kitchen_speed(
    days: int = 30,
    actor: Actor = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db),
) -> dict:
    return report_service.kitchen_speed_report(db, actor.restaurant_id, days=days)


@router.get("/audit-events", response_model=list[AuditEventOut])
def audit_events(
    actor: Actor = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
) -> list[AuditEventOut]:
    return report_service.list_audit(db, actor.restaurant_id)
