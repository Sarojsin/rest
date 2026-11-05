"""Tenant management for the platform console (plan 05 §4)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_token, new_token
from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import (
    PlatformAuditLog,
    PlatformOneTimeToken,
    PlatformPlan,
    PlatformSubscription,
)
from app.modules.platform.schemas_admin import (
    ReasonConfirmRequest,
    TenantCreateRequest,
    TenantUpdateRequest,
)
from app.modules.tenancy.services import platform_directory
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.billing import (
    add_subscription_event,
    period_end,
    serialize_subscription,
)
from app.modules.platform.services.common import (
    page_params,
    paginated,
    require_confirm,
    require_reason,
    serialize_audit,
    now_utc,
)
from app.shared.errors import AppError

router = APIRouter(tags=["platform-tenants"])


def _subscription_for(db: Session, tenant_id: UUID) -> PlatformSubscription | None:
    return db.scalar(
        select(PlatformSubscription)
        .where(
            PlatformSubscription.restaurant_id == tenant_id,
            PlatformSubscription.status.in_(platform_directory.LIVE_STATUSES),
        )
        .order_by(PlatformSubscription.created_at.desc())
        .limit(1)
    )


@router.get("/tenants")
def list_tenants(
    status_filter: str | None = Query(default=None, alias="status"),
    plan: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    items, total = platform_directory.list_tenants(
        db, status=status_filter, plan_code=plan, q=q, page=page, page_size=page_size
    )
    return paginated(items, total, page, page_size)


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    plan = db.scalar(select(PlatformPlan).where(PlatformPlan.code == payload.plan_code))
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    if plan.status != "ACTIVE":
        raise AppError(409, "PLAN_NOT_ACTIVE", "Conflict", "That plan is not active.")

    tenant = platform_directory.create_tenant(
        db,
        name=payload.name,
        slug=payload.slug,
        owner_email=str(payload.owner_email),
        owner_display_name=payload.owner_display_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        legal_name=payload.legal_name,
        timezone=payload.timezone,
        currency_code=payload.currency_code,
    )

    now = now_utc()
    trial_days = payload.trial_days
    sub_status = "TRIALING" if trial_days > 0 else "ACTIVE"
    subscription = PlatformSubscription(
        restaurant_id=tenant["id"],
        plan_id=plan.id,
        status=sub_status,
        trial_ends_at=now + timedelta(days=trial_days) if trial_days else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=trial_days or 30),
        cancel_at_period_end=False,
        price_snapshot_minor=plan.price_monthly_minor,
        currency_snapshot=plan.currency_code,
        billing_interval_snapshot="MONTHLY",
        created_by_admin_id=actor.admin_id,
    )
    db.add(subscription)
    db.flush()
    add_subscription_event(
        db,
        subscription,
        event_type="CREATED",
        admin_id=actor.admin_id,
        reason=reason,
        to_status=sub_status,
        metadata={"plan_code": plan.code, "trial_days": trial_days, "source": payload.source},
    )

    raw_token = new_token(32)
    db.add(
        PlatformOneTimeToken(
            token_hash=hash_token(raw_token),
            purpose="OWNER_INVITE",
            email=str(payload.owner_email).lower(),
            restaurant_id=tenant["id"],
            expires_at=now + timedelta(hours=72),
            created_by_admin_id=actor.admin_id,
        )
    )
    write_platform_audit(
        db,
        action="TENANT_CREATED",
        entity_type="restaurant",
        entity_id=str(tenant["id"]),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant["id"],
        reason=reason,
        request=request,
        after={
            "name": tenant["name"],
            "slug": tenant["slug"],
            "plan_code": plan.code,
            "owner_email": str(payload.owner_email),
        },
    )
    db.commit()

    tenant_origin = settings.platform_tenant_origin or ""
    accept_url = (
        f"{tenant_origin.rstrip('/')}/invite/{raw_token}"
        if tenant_origin
        else f"/invite/{raw_token}"
    )
    return {
        "tenant": tenant,
        "subscription": serialize_subscription(db, subscription),
        "invitation": {
            "token": raw_token,
            "expires_at": now + timedelta(hours=72),
            "accept_url": accept_url,
        },
        "audit_id": None,
    }


@router.get("/tenants/{tenant_id}")
def get_tenant(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    tenant = platform_directory.require_tenant(db, tenant_id)
    subscription = _subscription_for(db, tenant_id)
    recent = db.scalars(
        select(PlatformAuditLog)
        .where(PlatformAuditLog.restaurant_id == tenant_id)
        .order_by(PlatformAuditLog.created_at.desc())
        .limit(20)
    ).all()
    return {
        "tenant": tenant,
        "subscription": serialize_subscription(db, subscription) if subscription else None,
        "usage": platform_directory.tenant_usage(db, tenant_id),
        "recent_audit": [serialize_audit(row) for row in recent],
    }


@router.patch("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.create")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    before = platform_directory.require_tenant(db, tenant_id)
    fields = payload.model_dump(exclude_unset=True, exclude={"reason"})
    platform_directory.update_tenant_fields(db, tenant_id, fields)
    after = platform_directory.require_tenant(db, tenant_id)
    write_platform_audit(
        db,
        action="TENANT_UPDATED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={key: before.get(key) for key in fields},
        after={key: after.get(key) for key in fields},
    )
    db.commit()
    return {"tenant": after}


@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.suspend")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    if tenant["status"] == "SUSPENDED":
        raise AppError(409, "TENANT_ALREADY_SUSPENDED", "Conflict", "Tenant is already suspended.")
    platform_directory.set_tenant_status(
        db,
        tenant_id,
        status="SUSPENDED",
        reason=reason,
        suspended_at=now_utc(),
    )
    entry = write_platform_audit(
        db,
        action="TENANT_SUSPENDED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={"status": tenant["status"]},
        after={"status": "SUSPENDED"},
    )
    db.commit()
    return {"tenant": platform_directory.require_tenant(db, tenant_id), "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.reactivate")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    if tenant["status"] != "SUSPENDED":
        raise AppError(409, "TENANT_NOT_SUSPENDED", "Conflict", "Tenant is not suspended.")
    platform_directory.set_tenant_status(db, tenant_id, status="ACTIVE")
    entry = write_platform_audit(
        db,
        action="TENANT_REACTIVATED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={"status": tenant["status"]},
        after={"status": "ACTIVE"},
    )
    db.commit()
    return {"tenant": platform_directory.require_tenant(db, tenant_id), "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/force-logout")
def force_logout(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("tenant.force_logout")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    count = platform_directory.force_logout_tenant(db, tenant_id)
    entry = write_platform_audit(
        db,
        action="TENANT_FORCE_LOGOUT",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"revoked_memberships": count},
    )
    db.commit()
    return {"revoked_memberships": count, "audit_id": entry.id}


@router.post("/tenants/{tenant_id}/archive")
def archive_tenant(
    tenant_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    cancel_subscription: bool = False,
    actor: PlatformActor = Depends(require_platform_permission("tenant.delete")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    subscription = _subscription_for(db, tenant_id)
    if subscription is not None and not cancel_subscription:
        raise AppError(
            409,
            "TENANT_HAS_LIVE_SUBSCRIPTION",
            "Conflict",
            "Cancel the live subscription before archiving.",
        )
    now = now_utc()
    if subscription is not None:
        previous = subscription.status
        subscription.status = "CANCELLED"
        subscription.canceled_at = now
        add_subscription_event(
            db,
            subscription,
            event_type="CANCELLED",
            admin_id=actor.admin_id,
            reason=reason,
            from_status=previous,
            to_status="CANCELLED",
        )
    db.execute(
        text(
            "UPDATE restaurants SET archived_at = :now, status = 'CANCELLED', "
            "updated_at = :now WHERE id = :id"
        ),
        {"now": now, "id": tenant_id},
    )
    revoked = platform_directory.force_logout_tenant(db, tenant_id)
    entry = write_platform_audit(
        db,
        action="TENANT_ARCHIVED",
        entity_type="restaurant",
        entity_id=str(tenant_id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"archived_at": now, "revoked_memberships": revoked},
    )
    db.commit()
    return {
        "tenant": platform_directory.require_tenant(db, tenant_id),
        "revoked_memberships": revoked,
        "audit_id": entry.id,
    }


@router.get("/tenants/{tenant_id}/usage")
def tenant_usage(
    tenant_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("tenant.view")),
    db: Session = Depends(get_db),
) -> dict:
    platform_directory.require_tenant(db, tenant_id)
    return platform_directory.tenant_usage(db, tenant_id)


@router.get("/tenants/{tenant_id}/audit")
def tenant_audit(
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("audit.view")),
    db: Session = Depends(get_db),
) -> dict:
    platform_directory.require_tenant(db, tenant_id)
    page, page_size = page_params(page, page_size)
    base = select(PlatformAuditLog).where(PlatformAuditLog.restaurant_id == tenant_id)
    total = int(
        db.scalar(select(func.count()).select_from(base.subquery())) or 0
    )
    rows = db.scalars(
        base.order_by(PlatformAuditLog.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return paginated([serialize_audit(row) for row in rows], total, page, page_size)
