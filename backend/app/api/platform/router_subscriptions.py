"""Platform subscription lifecycle (plan 05 §6)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import (
    PlatformPlan,
    PlatformSubscription,
    PlatformSubscriptionEvent,
)
from app.modules.platform.permissions import SUPERADMIN
from app.modules.platform.schemas_admin import (
    CancelSubscriptionRequest,
    ExtendTrialRequest,
    ReasonRequest,
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
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
    require_reason,
    now_utc,
)
from app.modules.platform.services.settings import get_setting
from app.shared.errors import AppError

router = APIRouter(tags=["platform-subscriptions"])


def _get(db: Session, subscription_id: UUID) -> PlatformSubscription:
    row = db.get(PlatformSubscription, subscription_id)
    if row is None:
        raise AppError(404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription not found.")
    return row


def _plan_by_code(db: Session, code: str) -> PlatformPlan:
    plan = db.scalar(select(PlatformPlan).where(PlatformPlan.code == code.strip().lower()))
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    if plan.status == "ARCHIVED":
        raise AppError(409, "PLAN_ARCHIVED", "Conflict", "That plan is archived.")
    if plan.status != "ACTIVE":
        raise AppError(409, "PLAN_NOT_ACTIVE", "Conflict", "That plan is not active.")
    return plan


def _live_for_tenant(db: Session, tenant_id: UUID) -> PlatformSubscription | None:
    return db.scalar(
        select(PlatformSubscription)
        .where(
            PlatformSubscription.restaurant_id == tenant_id,
            PlatformSubscription.status.in_(platform_directory.LIVE_STATUSES),
        )
        .order_by(PlatformSubscription.created_at.desc())
        .limit(1)
    )


@router.get("/subscriptions")
def list_subscriptions(
    tenant_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    plan_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("subscription.view")),
    db: Session = Depends(get_db),
) -> dict:
    page, page_size = page_params(page, page_size)
    query = select(PlatformSubscription)
    if tenant_id:
        query = query.where(PlatformSubscription.restaurant_id == tenant_id)
    if status_filter:
        query = query.where(PlatformSubscription.status == status_filter)
    if plan_id:
        query = query.where(PlatformSubscription.plan_id == plan_id)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = db.scalars(
        query.order_by(PlatformSubscription.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    items = []
    for row in rows:
        data = serialize_subscription(db, row)
        tenant = platform_directory.get_tenant(db, row.restaurant_id)
        data["tenant_name"] = tenant["name"] if tenant else None
        data["tenant_slug"] = tenant["slug"] if tenant else None
        data["events"] = data["events"][:3]
        items.append(data)
    return paginated(items, total, page, page_size)


@router.get("/subscriptions/{subscription_id}")
def get_subscription(
    subscription_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("subscription.view")),
    db: Session = Depends(get_db),
) -> dict:
    row = _get(db, subscription_id)
    data = serialize_subscription(db, row)
    tenant = platform_directory.get_tenant(db, row.restaurant_id)
    data["tenant"] = tenant
    return data


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    try:
        tenant_id = UUID(payload.restaurant_id)
    except ValueError as exc:
        raise AppError(422, "INVALID_TENANT", "Invalid input", "Invalid tenant id.") from exc
    tenant = platform_directory.require_tenant(db, tenant_id)
    if _live_for_tenant(db, tenant_id):
        raise AppError(
            409, "LIVE_SUBSCRIPTION_EXISTS", "Conflict", "Tenant already has a live subscription."
        )
    plan = _plan_by_code(db, payload.plan_code)
    now = now_utc()
    trial_days = payload.trial_days if payload.trial_days is not None else plan.trial_days
    row = PlatformSubscription(
        restaurant_id=tenant_id,
        plan_id=plan.id,
        status="TRIALING" if trial_days > 0 else "ACTIVE",
        trial_ends_at=now + timedelta(days=trial_days) if trial_days else None,
        current_period_start=now,
        current_period_end=now + timedelta(days=trial_days or 30),
        cancel_at_period_end=False,
        price_snapshot_minor=plan.price_monthly_minor,
        currency_snapshot=plan.currency_code,
        billing_interval_snapshot="MONTHLY",
        created_by_admin_id=actor.admin_id,
    )
    db.add(row)
    db.flush()
    add_subscription_event(
        db,
        row,
        event_type="CREATED",
        admin_id=actor.admin_id,
        reason=reason,
        to_status=row.status,
        metadata={"plan_code": plan.code, "trial_days": trial_days},
    )
    write_platform_audit(
        db,
        action="SUBSCRIPTION_CREATED",
        entity_type="platform_subscription",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        after={"plan_code": plan.code, "status": row.status},
    )
    db.commit()
    data = serialize_subscription(db, row)
    data["tenant"] = tenant
    return data


@router.patch("/subscriptions/{subscription_id}")
def update_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, subscription_id)
    before = {
        "plan_id": row.plan_id,
        "cancel_at_period_end": row.cancel_at_period_end,
        "current_period_end": row.current_period_end,
        "grace_ends_at": row.grace_ends_at,
    }
    events: list[str] = []

    if payload.plan_code is not None:
        plan = _plan_by_code(db, payload.plan_code)
        if plan.id != row.plan_id:
            row.plan_id = plan.id
            row.price_snapshot_minor = plan.price_monthly_minor
            row.currency_snapshot = plan.currency_code
            row.billing_interval_snapshot = "MONTHLY"
            add_subscription_event(
                db,
                row,
                event_type="PLAN_CHANGED",
                admin_id=actor.admin_id,
                reason=reason,
                metadata={"plan_code": plan.code},
            )
            events.append("PLAN_CHANGED")

    if payload.cancel_at_period_end is not None:
        row.cancel_at_period_end = payload.cancel_at_period_end
        row.canceled_at = now_utc() if payload.cancel_at_period_end else None

    if payload.current_period_end is not None:
        interval = row.billing_interval_snapshot
        max_end = row.current_period_end + (
            timedelta(days=365) if interval == "ANNUAL" else timedelta(days=30)
        )
        if not (row.current_period_start <= payload.current_period_end <= max_end):
            raise AppError(
                409,
                "INVALID_STATUS_TRANSITION",
                "Conflict",
                "The new period end is outside the allowed one-interval window.",
            )
        row.current_period_end = payload.current_period_end

    if payload.grace_ends_at is not None:
        if actor.role != SUPERADMIN:
            raise AppError(
                403,
                "FORBIDDEN",
                "Forbidden",
                "Only a superadmin can change the grace period.",
            )
        row.grace_ends_at = payload.grace_ends_at

    row.updated_at = now_utc()
    write_platform_audit(
        db,
        action="SUBSCRIPTION_UPDATED",
        entity_type="platform_subscription",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=row.restaurant_id,
        reason=reason,
        request=request,
        before=before,
        after={
            "plan_id": row.plan_id,
            "cancel_at_period_end": row.cancel_at_period_end,
            "current_period_end": row.current_period_end,
            "grace_ends_at": row.grace_ends_at,
        },
    )
    db.commit()
    data = serialize_subscription(db, row)
    data["tenant"] = platform_directory.get_tenant(db, row.restaurant_id)
    return data


@router.post("/subscriptions/{subscription_id}/extend-trial")
def extend_trial(
    subscription_id: UUID,
    payload: ExtendTrialRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, subscription_id)
    if row.status != "TRIALING":
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "Only a trial can be extended."
        )
    per_action = int(get_setting(db, "platform.trial_extension_max_days_per_action", 30) or 30)
    total_limit = int(get_setting(db, "platform.trial_extension_max_days_total", 60) or 60)
    if payload.days > per_action:
        raise AppError(
            422,
            "INVALID_AMOUNT",
            "Invalid input",
            f"A single extension may not exceed {per_action} days.",
        )
    previous_events = db.scalars(
        select(PlatformSubscriptionEvent).where(
            PlatformSubscriptionEvent.subscription_id == row.id,
            PlatformSubscriptionEvent.event_type == "TRIAL_EXTENDED",
        )
    ).all()
    previous_total = sum(
        int((event.metadata_json or {}).get("days", 0) or 0)
        for event in previous_events
    )
    if previous_total + payload.days > total_limit and actor.role != SUPERADMIN:
        raise AppError(
            403,
            "TRIAL_LIMIT_REQUIRES_SUPERADMIN",
            "Forbidden",
            "This extension exceeds the configured trial limit; a superadmin must approve it.",
        )

    base = row.trial_ends_at or now_utc()
    row.trial_ends_at = base + timedelta(days=payload.days)
    if row.current_period_end < row.trial_ends_at:
        row.current_period_end = row.trial_ends_at
    row.updated_at = now_utc()
    add_subscription_event(
        db,
        row,
        event_type="TRIAL_EXTENDED",
        admin_id=actor.admin_id,
        reason=reason,
        metadata={
            "days": payload.days,
            "previous_total": previous_total,
            "per_action_limit": per_action,
            "total_limit": total_limit,
        },
    )
    write_platform_audit(
        db,
        action="TRIAL_EXTENDED",
        entity_type="platform_subscription",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=row.restaurant_id,
        reason=reason,
        request=request,
        before={"trial_ends_at": base},
        after={"trial_ends_at": row.trial_ends_at, "days": payload.days},
    )
    db.commit()
    return serialize_subscription(db, row)


@router.post("/subscriptions/{subscription_id}/cancel")
def cancel_subscription(
    subscription_id: UUID,
    payload: CancelSubscriptionRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, subscription_id)
    if row.status in ("CANCELLED", "EXPIRED"):
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "Subscription is already ended."
        )
    previous = row.status
    if payload.at_period_end:
        row.cancel_at_period_end = True
        row.canceled_at = now_utc()
        to_status = previous
        event = "CANCELLED"
    else:
        row.status = "CANCELLED"
        row.cancel_at_period_end = False
        row.canceled_at = now_utc()
        to_status = "CANCELLED"
        event = "CANCELLED"
    row.updated_at = now_utc()
    add_subscription_event(
        db,
        row,
        event_type=event,
        admin_id=actor.admin_id,
        reason=reason,
        from_status=previous,
        to_status=to_status,
        metadata={"at_period_end": payload.at_period_end},
    )
    write_platform_audit(
        db,
        action="SUBSCRIPTION_CANCELLED",
        entity_type="platform_subscription",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=row.restaurant_id,
        reason=reason,
        request=request,
        before={"status": previous},
        after={"status": row.status, "cancel_at_period_end": row.cancel_at_period_end},
    )
    db.commit()
    return serialize_subscription(db, row)


@router.post("/subscriptions/{subscription_id}/reactivate")
def reactivate_subscription(
    subscription_id: UUID,
    payload: ReasonRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    row = _get(db, subscription_id)
    previous = row.status
    if previous == "ACTIVE" and not row.cancel_at_period_end:
        raise AppError(
            409, "INVALID_STATUS_TRANSITION", "Conflict", "Subscription is already active."
        )
    now = now_utc()
    row.status = "ACTIVE"
    row.cancel_at_period_end = False
    row.canceled_at = None
    row.grace_ends_at = None
    row.current_period_start = now
    row.current_period_end = period_end(now, row.billing_interval_snapshot)
    row.updated_at = now
    add_subscription_event(
        db,
        row,
        event_type="REACTIVATED",
        admin_id=actor.admin_id,
        reason=reason,
        from_status=previous,
        to_status="ACTIVE",
    )
    write_platform_audit(
        db,
        action="SUBSCRIPTION_REACTIVATED",
        entity_type="platform_subscription",
        entity_id=str(row.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=row.restaurant_id,
        reason=reason,
        request=request,
        before={"status": previous},
        after={"status": "ACTIVE"},
    )
    db.commit()
    return serialize_subscription(db, row)


@router.get("/subscriptions/{subscription_id}/events")
def subscription_events(
    subscription_id: UUID,
    page: int = 1,
    page_size: int = 25,
    actor: PlatformActor = Depends(require_platform_permission("subscription.view")),
    db: Session = Depends(get_db),
) -> dict:
    _get(db, subscription_id)
    page, page_size = page_params(page, page_size)
    base = select(PlatformSubscriptionEvent).where(
        PlatformSubscriptionEvent.subscription_id == subscription_id
    )
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.scalars(
        base.order_by(PlatformSubscriptionEvent.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    return paginated(
        [
            {
                "id": row.id,
                "event_type": row.event_type,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "actor_admin_id": row.actor_admin_id,
                "reason": row.reason,
                "metadata": row.metadata_json,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        total,
        page,
        page_size,
    )
