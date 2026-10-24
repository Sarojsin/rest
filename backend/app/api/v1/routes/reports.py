from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.staff import AuditEventOut, SalesReportOut
from app.services import reports as report_service

router = APIRouter(tags=["reports"])


@router.get("/reports/sales", response_model=SalesReportOut)
def sales(
    actor: Actor = Depends(require_permission("reports.read")),
    db: Session = Depends(get_db),
) -> SalesReportOut:
    return report_service.sales_report(db, actor.restaurant_id)


@router.get("/audit-events", response_model=list[AuditEventOut])
def audit_events(
    actor: Actor = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
) -> list[AuditEventOut]:
    return report_service.list_audit(db, actor.restaurant_id)
