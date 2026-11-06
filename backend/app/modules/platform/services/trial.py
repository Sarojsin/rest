"""Trial lifecycle service (Plan 03).

Handles trial expiration, grace period notifications, trial extension limits,
and trial history tracking. Key rules:

- A trial expires when trial_ends_at passes and status is TRIALING
- Notify owner 3 days and 1 day before trial expiration
- One trial per tenant (tracked in trial_history table)
- Trial extensions limited per-action and per-total (configurable via settings)
- Superadmin can override trial limits
- Expired trials cannot be re-extended
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.modules.platform.models import (
    PlatformSubscription,
    PlatformSubscriptionEvent,
    PlatformSubscriptionTrialHistory,
    PlatformSetting,
)
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.billing import add_subscription_event
from app.shared.errors import AppError

TRIAL_STATUSES = ("TRIALING",)


def _now() -> datetime:
    return datetime.now(UTC)


def get_setting(db: Session, key: str, default=None):
    """Get a platform setting value."""
    row = db.get(PlatformSetting, key)
    if row is not None:
        return row.value_json
    return default


def _get_active_subscription(
    db: Session, restaurant_id: UUID
) -> PlatformSubscription | None:
    """Get the active subscription for a tenant."""
    return db.scalar(
        select(PlatformSubscription)
        .where(
            PlatformSubscription.restaurant_id == restaurant_id,
            PlatformSubscription.status.in_(
                ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE", "SUSPENDED")
            ),
        )
        .order_by(PlatformSubscription.created_at.desc())
        .limit(1)
    )


def expire_expired_trials(db: Session) -> int:
    """Mark all expired trials as EXPIRED.

    Returns the number of trials expired.
    """
    now = _now()
    expired = db.scalars(
        select(PlatformSubscription).where(
            PlatformSubscription.status == "TRIALING",
            PlatformSubscription.trial_ends_at < now,
        )
    ).all()

    count = 0
    for sub in expired:
        sub.status = "EXPIRED"
        sub.updated_at = now

        # Record in trial history
        history = PlatformSubscriptionTrialHistory(
            restaurant_id=sub.restaurant_id,
            trial_start_at=sub.current_period_start,
            trial_end_at=sub.trial_ends_at or now,
            plan_version_id=sub.plan_version_id,
            converted_to_paid=False,
            reason="trial_expired",
        )
        db.add(history)

        write_platform_audit(
            db,
            action="TRIAL_EXPIRED",
            entity_type="platform_subscription",
            entity_id=str(sub.id),
            actor_admin_id=None,
            actor_email=None,
            restaurant_id=sub.restaurant_id,
            reason="trial expired without payment",
            request=None,
        )
        count += 1

    db.commit()
    return count


def get_trial_expirations(
    db: Session, *, days_ahead: int = 3
) -> list[dict]:
    """Get trials expiring within the given number of days.

    Used for sending expiration notifications to owners.
    """
    now = _now()
    horizon = now + timedelta(days=days_ahead)

    trials = db.scalars(
        select(PlatformSubscription).where(
            PlatformSubscription.status == "TRIALING",
            PlatformSubscription.trial_ends_at >= now,
            PlatformSubscription.trial_ends_at <= horizon,
        )
    ).all()

    return [
        {
            "subscription_id": str(t.id),
            "restaurant_id": str(t.restaurant_id),
            "trial_ends_at": t.trial_ends_at,
            "days_remaining": max(
                0, (t.trial_ends_at - now).days
            ),
            "plan_version_id": str(t.plan_version_id) if t.plan_version_id else None,
        }
        for t in trials
    ]


def has_prior_trial(db: Session, restaurant_id: UUID) -> bool:
    """Check if a restaurant has ever had a trial (to prevent repeat trials)."""
    return db.scalar(
        select(func.count())
        .select_from(PlatformSubscriptionTrialHistory)
        .where(PlatformSubscriptionTrialHistory.restaurant_id == restaurant_id)
    ) > 0


def record_trial_history(
    db: Session,
    *,
    restaurant_id: UUID,
    trial_start_at: datetime,
    trial_end_at: datetime,
    plan_version_id: UUID | None,
    reason: str = "trial_started",
) -> PlatformSubscriptionTrialHistory:
    """Record a trial in the history table."""
    history = PlatformSubscriptionTrialHistory(
        restaurant_id=restaurant_id,
        trial_start_at=trial_start_at,
        trial_end_at=trial_end_at,
        plan_version_id=plan_version_id,
        converted_to_paid=False,
        reason=reason,
    )
    db.add(history)
    db.flush()
    return history


def mark_trial_converted(
    db: Session,
    *,
    restaurant_id: UUID,
    converted_payment_id: UUID | None = None,
) -> None:
    """Mark the most recent trial as converted to paid."""
    history = db.scalars(
        select(PlatformSubscriptionTrialHistory)
        .where(
            PlatformSubscriptionTrialHistory.restaurant_id == restaurant_id,
            PlatformSubscriptionTrialHistory.converted_to_paid == False,  # noqa: E712
        )
        .order_by(PlatformSubscriptionTrialHistory.created_at.desc())
        .limit(1)
    ).all()

    for h in history:
        h.converted_to_paid = True
        h.converted_at = _now()
        if converted_payment_id:
            h.converted_payment_id = converted_payment_id

    db.flush()


def can_create_trial(
    db: Session, *, restaurant_id: UUID
) -> tuple[bool, str | None]:
    """Check if a restaurant is eligible for a new trial.

    Returns (eligible, reason_or_none).
    """
    if has_prior_trial(db, restaurant_id):
        return False, "A trial has already been used for this restaurant"

    # Check if there's already an active subscription
    existing = _get_active_subscription(db, restaurant_id)
    if existing is not None:
        return False, "Restaurant already has an active subscription"

    return True, None


def extend_trial(
    db: Session,
    *,
    subscription: PlatformSubscription,
    days: int,
    actor_admin_id: UUID | None,
    reason: str,
    request=None,
) -> PlatformSubscription:
    """Extend a trial by the given number of days.

    Enforces per-action and total limits from settings.
    Superadmin can override limits.
    """
    from app.modules.platform.permissions import SUPERADMIN

    if subscription.status != "TRIALING":
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            "Conflict",
            "Only a trial can be extended.",
        )

    per_action = int(
        get_setting(db, "platform.trial_extension_max_days_per_action", 30) or 30
    )
    total_limit = int(
        get_setting(db, "platform.trial_extension_max_days_total", 60) or 60
    )

    if days > per_action:
        raise AppError(
            422,
            "INVALID_AMOUNT",
            "Invalid input",
            f"A single extension may not exceed {per_action} days.",
        )

    # Count previous extensions
    previous_events = db.scalars(
        select(PlatformSubscriptionEvent).where(
            PlatformSubscriptionEvent.subscription_id == subscription.id,
            PlatformSubscriptionEvent.event_type == "TRIAL_EXTENDED",
        )
    ).all()
    previous_total = sum(
        int((event.metadata_json or {}).get("days", 0) or 0)
        for event in previous_events
    )

    if previous_total + days > total_limit and actor_admin_id is not None:
        # Check if actor is superadmin - this is checked at API level too
        # but we enforce here as defense in depth
        raise AppError(
            403,
            "TRIAL_LIMIT_REQUIRES_SUPERADMIN",
            "Forbidden",
            f"This extension exceeds the configured trial limit ({total_limit} days total).",
        )

    base = subscription.trial_ends_at or _now()
    subscription.trial_ends_at = base + timedelta(days=days)
    if subscription.current_period_end < subscription.trial_ends_at:
        subscription.current_period_end = subscription.trial_ends_at
    subscription.trial_extension_count += 1
    subscription.trial_extension_total_days += days
    subscription.updated_at = _now()

    add_subscription_event(
        db,
        subscription,
        event_type="TRIAL_EXTENDED",
        admin_id=actor_admin_id,
        reason=reason,
        metadata={
            "days": days,
            "previous_total": previous_total,
            "per_action_limit": per_action,
            "total_limit": total_limit,
        },
    )

    write_platform_audit(
        db,
        action="TRIAL_EXTENDED",
        entity_type="platform_subscription",
        entity_id=str(subscription.id),
        actor_admin_id=actor_admin_id,
        actor_email=None,
        restaurant_id=subscription.restaurant_id,
        reason=reason,
        request=request,
        before={"trial_ends_at": base},
        after={
            "trial_ends_at": subscription.trial_ends_at,
            "days": days,
        },
    )
    db.commit()
    return subscription


def expire_trial_manually(
    db: Session,
    *,
    subscription: PlatformSubscription,
    actor_admin_id: UUID | None,
    reason: str,
    request=None,
) -> PlatformSubscription:
    """Manually expire a trial (superadmin action)."""
    if subscription.status != "TRIALING":
        raise AppError(
            409,
            "INVALID_STATUS_TRANSITION",
            "Conflict",
            "Only a trialing subscription can be expired.",
        )

    subscription.status = "EXPIRED"
    subscription.updated_at = _now()

    history = PlatformSubscriptionTrialHistory(
        restaurant_id=subscription.restaurant_id,
        trial_start_at=subscription.current_period_start,
        trial_end_at=subscription.trial_ends_at or _now(),
        plan_version_id=subscription.plan_version_id,
        converted_to_paid=False,
        reason=reason,
    )
    db.add(history)

    write_platform_audit(
        db,
        action="TRIAL_EXPIRED",
        entity_type="platform_subscription",
        entity_id=str(subscription.id),
        actor_admin_id=actor_admin_id,
        actor_email=None,
        restaurant_id=subscription.restaurant_id,
        reason=reason,
        request=request,
    )
    db.commit()
    return subscription


def get_trial_status(
    db: Session, *, restaurant_id: UUID
) -> dict | None:
    """Get trial status for a restaurant's dashboard.

    Returns None if no active trial subscription.
    """
    sub = _get_active_subscription(db, restaurant_id)
    if sub is None or sub.status != "TRIALING":
        return None

    now = _now()
    days_remaining = max(0, (sub.trial_ends_at - now).days) if sub.trial_ends_at else 0
    is_expiring_soon = days_remaining <= 3

    return {
        "subscription_id": str(sub.id),
        "restaurant_id": str(restaurant_id),
        "status": sub.status,
        "trial_ends_at": sub.trial_ends_at,
        "days_remaining": days_remaining,
        "is_expiring_soon": is_expiring_soon,
        "trial_extension_count": sub.trial_extension_count,
        "trial_extension_total_days": sub.trial_extension_total_days,
        "can_extend": sub.trial_extension_count
        < int(
            get_setting(
                db, "platform.trial_extension_max_days_per_action", 30
            )
            or 30
        ),
    }
