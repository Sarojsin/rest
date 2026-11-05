"""Append-only platform audit log viewer (plan 05 §9)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import PlatformActor, require_platform_permission
from app.modules.platform.models import PlatformAuditLog
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.common import page_params, paginated, serialize_audit

router = APIRouter(tags=["platform-audit"])


def _filtered(
    *,
    action: str | None,
    tenant_id: UUID | None,
    actor_id: UUID | None,
    from_: datetime | None,
    to: datetime | None,
    q: str | None,
):
    query = select(PlatformAuditLog)
    if action:
        query = query.where(PlatformAuditLog.action == action)
    if tenant_id:
        query = query.where(PlatformAuditLog.restaurant_id == tenant_id)
    if actor_id:
        query = query.where(PlatformAuditLog.actor_admin_id == actor_id)
    if from_:
        query = query.where(PlatformAuditLog.created_at >= from_)
    if to:
        query = query.where(PlatformAuditLog.created_at <= to)
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(
            PlatformAuditLog.action.ilike(needle)
            | PlatformAuditLog.entity_id.ilike(needle)
            | PlatformAuditLog.reason.ilike(needle)
            | PlatformAuditLog.actor_email_snapshot.ilike(needle)
        )
    return query


@router.get("/audit-logs/export")
def export_audit_logs(
    request: Request,
    action: str | None = None,
    tenant_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    actor: PlatformActor = Depends(require_platform_permission("audit.view")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = db.scalars(
        _filtered(
            action=action,
            tenant_id=tenant_id,
            actor_id=None,
            from_=from_,
            to=to,
            q=None,
        )
        .order_by(PlatformAuditLog.created_at.desc())
        .limit(5000)
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "created_at",
            "action",
            "actor_email",
            "entity_type",
            "entity_id",
            "tenant_id",
            "reason",
            "request_id",
            "ip",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.created_at.isoformat() if row.created_at else "",
                row.action,
                row.actor_email_snapshot or "",
                row.entity_type,
                row.entity_id,
                row.restaurant_id or "",
                row.reason,
                row.request_id or "",
                row.ip or "",
            ]
        )
    write_platform_audit(
        db,
        action="AUDIT_EXPORTED",
        entity_type="platform_audit_log",
        entity_id="export",
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason="audit export",
        request=request,
        after={"rows": len(rows)},
    )
    db.commit()
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="platform-audit.csv"'},
    )


@router.get("/audit-logs")
def list_audit_logs(
    action: str | None = None,
    tenant_id: UUID | None = None,
    actor_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("audit.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = _filtered(
        action=action,
        tenant_id=tenant_id,
        actor_id=actor_id,
        from_=from_,
        to=to,
        q=q,
    )
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformAuditLog.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return paginated([serialize_audit(row) for row in rows], total, page, page_size)


@router.get("/audit-logs/{audit_id}")
def get_audit_log(
    audit_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("audit.view")),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(PlatformAuditLog, audit_id)
    if row is None:
        from app.shared.errors import AppError

        raise AppError(404, "AUDIT_NOT_FOUND", "Not found", "Audit entry not found.")
    return serialize_audit(row)
