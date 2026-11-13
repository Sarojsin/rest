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
    PlatformPlanLimit,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformSubscriptionChangeHistory,
    PlatformSubscriptionEvent,
    PlatformTenantUsage,
)
from app.modules.platform.permissions import SUPERADMIN
from app.modules.platform.schemas_admin import (
    CancelSubscriptionRequest,
    ExpireTrialRequest,
    ExtendTrialRequest,
    ReasonRequest,
    SubscriptionChangeRequest,
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
    require_confirm,
    require_reason,
    now_utc,
)
from app.modules.platform.services.settings import get_setting
from app.modules.platform.services.entitlements import get_effective_entitlements
from app.modules.platform.services.plan_versions import get_active_plan_version
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


@router.post("/tenants/{tenant_id}/subscription/change")
def change_subscription_plan(
    tenant_id: UUID,
    payload: SubscriptionChangeRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("subscription.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Change a tenant's subscription plan (upgrade or downgrade).

    Downgrades are guarded by usage-vs-limit checks: if current usage
    exceeds the new plan's limits, the request is rejected with a list
    of violations. No resources are silently deleted.
    """
    # Validate tenant exists and get slug for confirm check
    tenant = platform_directory.require_tenant(db, tenant_id)
    require_confirm(payload.confirm, tenant["slug"])
    reason = require_reason(payload.reason)

    # Get current subscription
    current_sub = _live_for_tenant(db, tenant_id)
    if current_sub is None:
        raise AppError(
            404,
            "NO_ACTIVE_SUBSCRIPTION",
            "Not found",
            "Tenant has no active subscription.",
        )

    # Get new plan
    new_plan = _plan_by_code(db, payload.new_plan_code)
    if new_plan.id == current_sub.plan_id:
        raise AppError(
            409,
            "SAME_PLAN",
            "Conflict",
            "Already subscribed to this plan.",
        )

    # Get active plan version for new plan
    new_version = get_active_plan_version(db, new_plan.id)
    if new_version is None:
        raise AppError(
            409,
            "PLAN_VERSION_NOT_ACTIVE",
            "Conflict",
            "No active plan version found for the new plan.",
        )

    # Get old plan code before changing
    old_plan = db.get(PlatformPlan, current_sub.plan_id)
    old_plan_code = old_plan.code if old_plan else None

    # Determine if upgrade or downgrade
    is_downgrade = new_version.price_monthly_minor < current_sub.price_snapshot_minor

    # For downgrade, check usage vs new plan limits
    if is_downgrade:
        new_limits = db.scalars(
            select(PlatformPlanLimit).where(
                PlatformPlanLimit.plan_version_id == new_version.id
            )
        ).all()
        limit_map = {l.limit_key: l.limit_value for l in new_limits}

        # Get current usage from the cached counter table
        usage_row = db.scalar(
            select(PlatformTenantUsage).where(
                PlatformTenantUsage.restaurant_id == tenant_id
            )
        )

        counter_map = {
            "branches": "branch_count",
            "owners": "owner_count",
            "managers": "manager_count",
            "waiters": "waiter_count",
            "kitchen": "kitchen_count",
            "cashier": "cashier_count",
            "tables": "table_count",
        }

        violations = []
        if usage_row is not None:
            for limit_key, limit_value in limit_map.items():
                counter_attr = counter_map.get(limit_key)
                if counter_attr is None:
                    continue
                current = getattr(usage_row, counter_attr, 0) or 0
                if current > limit_value:
                    violations.append(
                        {
                            "resource": limit_key,
                            "current": current,
                            "limit": limit_value,
                            "excess": current - limit_value,
                        }
                    )

        if violations:
            raise AppError(
                409,
                "DOWNGRADE_LIMIT_EXCEEDED",
                "Conflict",
                "Current usage exceeds new plan limits.",
                extra={"violations": violations},
            )

    # Calculate prorated amount for remaining days in current period
    now = now_utc()
    days_remaining = max(0, (current_sub.current_period_end - now).days)
    old_daily_rate = current_sub.price_snapshot_minor / 30.0
    new_daily_rate = new_version.price_monthly_minor / 30.0
    prorated_amount = int(round((new_daily_rate - old_daily_rate) * days_remaining))

    # Record change history
    change_record = PlatformSubscriptionChangeHistory(
        restaurant_id=tenant_id,
        from_plan_version_id=current_sub.plan_version_id,
        to_plan_version_id=new_version.id,
        changed_by_admin_id=actor.admin_id,
        reason=reason,
        prorated_amount_minor=prorated_amount,
    )
    db.add(change_record)

    # Update subscription
    from_status = current_sub.status
    current_sub.plan_id = new_plan.id
    current_sub.plan_version_id = new_version.id
    current_sub.price_snapshot_minor = new_version.price_monthly_minor
    current_sub.currency_snapshot = new_version.currency_code
    current_sub.billing_interval_snapshot = "MONTHLY"
    current_sub.updated_at = now

    # Add subscription event
    event_type = "PLAN_UPGRADED" if not is_downgrade else "PLAN_DOWNGRADED"
    add_subscription_event(
        db,
        current_sub,
        event_type=event_type,
        admin_id=actor.admin_id,
        reason=reason,
        from_status=from_status,
        to_status=current_sub.status,
        metadata={
            "from_plan_code": old_plan_code,
            "to_plan_code": new_plan.code,
            "prorated_amount_minor": prorated_amount,
        },
    )

    write_platform_audit(
        db,
        action="SUBSCRIPTION_PLAN_CHANGED",
        entity_type="platform_subscription",
        entity_id=str(current_sub.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        restaurant_id=tenant_id,
        reason=reason,
        request=request,
        before={"plan_code": old_plan_code},
        after={
            "plan_code": new_plan.code,
            "prorated_amount_minor": prorated_amount,
        },
    )

    db.commit()

    return {
        "subscription": serialize_subscription(db, current_sub),
        "change": {
            "from_plan_version_id": (
                str(current_sub.plan_version_id) if current_sub.plan_version_id else None
            ),
            "to_plan_version_id": str(new_version.id),
            "prorated_amount_minor": prorated_amount,
            "is_downgrade": is_downgrade,
        },
        "audit_id": None,
    }


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


# ---------------------------------------------------------------------------
# Trial lifecycle endpoints (Plan 03)
# ---------------------------------------------------------------------------


@router.post("/subscriptions/{subscription_id}/expire-trial")
def expire_trial(
    subscription_id: UUID,
    payload: ExpireTrialRequest,
    request: Request,
    actor: PlatformActor = Depends(
        require_platform_permission("subscription.manage")
    ),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Manually expire a trial subscription (superadmin/ops action)."""
    from app.modules.platform.services.trial import expire_trial_manually

    row = _get(db, subscription_id)
    if row.status != "TRIALING":
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            "Conflict",
            "Only a trialing subscription can be expired.",
        )

    expire_trial_manually(
        db,
        subscription=row,
        actor_admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return {"ok": True, "subscription_id": str(subscription_id), "status": "EXPIRED"}


@router.get("/subscriptions/{subscription_id}/trial-status")
def get_trial_status(
    subscription_id: UUID,
    actor: PlatformActor = Depends(
        require_platform_permission("subscription.view")
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Get trial status for a subscription."""
    from app.modules.platform.services.trial import get_trial_status

    row = _get(db, subscription_id)
    if row.status != "TRIALING":
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            "Conflict",
            "Only a trialing subscription has trial status.",
        )

    status = get_trial_status(db, restaurant_id=row.restaurant_id)
    if status is None:
        raise AppError(
            404,
            "TRIAL_NOT_FOUND",
            "Not found",
            "No active trial found for this subscription.",
        )
    return status


@router.post("/trials/expire-expired")
def expire_expired_trials(
    request: Request,
    actor: PlatformActor = Depends(
        require_platform_permission("subscription.manage")
    ),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Expire all trials that have passed their trial_ends_at.

    Typically called by a cron job.
    """
    from app.modules.platform.services.trial import expire_expired_trials

    count = expire_expired_trials(db)
    return TrialExpirationOut(expired_count=count, expired_subscriptions=[]).model_dump()


@router.get("/trials/expiring")
def get_expiring_trials(
    days_ahead: int = Query(default=3, ge=1, le=30),
    actor: PlatformActor = Depends(
        require_platform_permission("subscription.view")
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Get trials expiring within the given number of days.

    Used for sending expiration notifications to owners.
    """
    from app.modules.platform.services.trial import get_trial_expirations

    trials = get_trial_expirations(db, days_ahead=days_ahead)
    return TrialExpiringOut(expiring_count=len(trials), trials=trials).model_dump()


@router.post("/subscriptions/{subscription_id}/extend-trial")
def extend_trial_endpoint(
    subscription_id: UUID,
    payload: ExtendTrialRequest,
    request: Request,
    actor: PlatformActor = Depends(
        require_platform_permission("subscription.manage")
    ),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Extend a trial subscription with limit enforcement."""
    from app.modules.platform.services.trial import extend_trial

    row = _get(db, subscription_id)
    if row.status != "TRIALING":
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            "Conflict",
            "Only a trial can be extended.",
        )

    extend_trial(
        db,
        subscription=row,
        days=payload.days,
        actor_admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return serialize_subscription(db, row)

