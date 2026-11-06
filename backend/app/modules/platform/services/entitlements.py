"""Tenant entitlement enforcement service (Plan 02).

Provides backend enforcement of plan features and limits. Every tenant
operation that consumes a plan-limited resource must check:

1. The feature is enabled (feature gates)
2. The usage limit is not reached (seat limits)

Uses atomic database transactions with SELECT ... FOR UPDATE to prevent
race conditions when two simultaneous invitations could exceed a seat limit.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator
from uuid import UUID

from sqlalchemy import select, text, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.modules.platform.models import (
    PlatformPlan,
    PlatformPlanFeature,
    PlatformPlanLimit,
    PlatformPlanVersion,
    PlatformSubscription,
    PlatformTenantUsage,
    PlatformUsageEvent,
)
from app.modules.platform.services.audit import write_platform_audit
from app.shared.errors import AppError

# Resource type -> limit key mapping
RESOURCE_LIMIT_KEYS = {
    "branch": "branches",
    "owner": "owners",
    "manager": "managers",
    "waiter": "waiters",
    "kitchen": "kitchen",
    "cashier": "cashier",
    "table": "tables",
}

# All recognized limit keys
LIMIT_KEYS = frozenset(RESOURCE_LIMIT_KEYS.values())

# Reverse lookup: plan limit key (plural) -> usage counter resource (singular)
LIMIT_KEY_TO_RESOURCE = {v: k for k, v in RESOURCE_LIMIT_KEYS.items()}

# All recognized feature keys
FEATURE_KEYS = frozenset(
    {
        "qr_ordering",
        "menu_management",
        "inventory",
        "advanced_reports",
        "loyalty",
        "online_payment",
    }
)


def _now() -> datetime:
    return datetime.now(UTC)


def _get_active_subscription(db: Session, restaurant_id: UUID):
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


def _get_or_create_usage_row(
    db: Session, restaurant_id: UUID
) -> PlatformTenantUsage:
    """Get or create the usage row for a restaurant within a transaction."""
    row = db.scalar(
        select(PlatformTenantUsage).where(
            PlatformTenantUsage.restaurant_id == restaurant_id
        ).with_for_update()
    )
    if row is None:
        row = PlatformTenantUsage(
            restaurant_id=restaurant_id,
            branch_count=0,
            owner_count=0,
            manager_count=0,
            waiter_count=0,
            kitchen_count=0,
            cashier_count=0,
            table_count=0,
        )
        db.add(row)
        db.flush()
    return row


def _record_usage_event(
    db: Session,
    *,
    restaurant_id: UUID,
    resource_type: str,
    change: int,
    actor_admin_id: UUID | None,
    reason: str,
) -> None:
    """Append an append-only usage event."""
    event = PlatformUsageEvent(
        restaurant_id=restaurant_id,
        resource_type=resource_type,
        change=change,
        actor_admin_id=actor_admin_id,
        reason=reason,
    )
    db.add(event)
    db.flush()


def _apply_change_to_usage_row(
    row: PlatformTenantUsage, resource_type: str, change: int
) -> None:
    """Apply a +1/-1 change to the appropriate counter on the usage row.

    ``resource_type`` may be either the singular resource name (``branch``) or
    the plan limit key (``branches``); both resolve to the same counter.
    """
    singular = LIMIT_KEY_TO_RESOURCE.get(resource_type, resource_type)
    counter_attr = f"{singular}_count"
    if not hasattr(row, counter_attr):
        raise AppError(
            422,
            "UNKNOWN_RESOURCE_TYPE",
            "Invalid input",
            f"Unknown resource type: {resource_type}",
        )
    current = getattr(row, counter_attr)
    new_value = current + change
    if new_value < 0:
        raise AppError(
            422,
            "NEGATIVE_USAGE",
            "Invalid input",
            f"Cannot decrement {resource_type} below zero.",
        )
    setattr(row, counter_attr, new_value)


# ---------------------------------------------------------------------------
# Entitlement queries
# ---------------------------------------------------------------------------


def get_effective_entitlements(
    db: Session, *, restaurant_id: UUID
) -> dict | None:
    """Get the effective features and limits for a tenant's active subscription.

    Returns None if the tenant has no active subscription.
    """
    sub = _get_active_subscription(db, restaurant_id)
    if sub is None or sub.plan_version_id is None:
        return None

    features = db.scalars(
        select(PlatformPlanFeature).where(
            PlatformPlanFeature.plan_version_id == sub.plan_version_id
        )
    ).all()
    limits = db.scalars(
        select(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == sub.plan_version_id
        )
    ).all()

    return {
        "subscription_id": str(sub.id),
        "plan_version_id": str(sub.plan_version_id),
        "features": {f.feature_key: f.enabled for f in features},
        "limits": {l.limit_key: l.limit_value for l in limits},
    }


def check_feature_enabled(
    db: Session, *, restaurant_id: UUID, feature_key: str
) -> bool:
    """Check whether a feature is enabled for a tenant's active subscription.

    Returns False if no active subscription or feature not found.
    """
    entitlements = get_effective_entitlements(db, restaurant_id=restaurant_id)
    if entitlements is None:
        return False
    return entitlements["features"].get(feature_key, False)


def check_limit_available(
    db: Session, *, restaurant_id: UUID, limit_key: str, increment: int = 1
) -> bool:
    """Check whether incrementing a limit would stay within the plan limit.

    Returns True if current + increment <= limit, False otherwise.
    Returns False if no active subscription or limit not found (treated as 0).
    """
    if limit_key not in LIMIT_KEYS:
        raise AppError(
            422,
            "UNKNOWN_LIMIT_KEY",
            "Invalid input",
            f"Unknown limit key: {limit_key}",
        )

    entitlements = get_effective_entitlements(db, restaurant_id=restaurant_id)
    if entitlements is None:
        return False

    plan_limit = entitlements["limits"].get(limit_key)
    if plan_limit is None:
        # No explicit limit means unlimited
        return True

    row = _get_or_create_usage_row(db, restaurant_id)
    counter_attr = f"{LIMIT_KEY_TO_RESOURCE[limit_key]}_count"
    current = getattr(row, counter_attr)

    return current + increment <= plan_limit


def consume_limit(
    db: Session,
    *,
    restaurant_id: UUID,
    limit_key: str,
    increment: int = 1,
    actor_admin_id: UUID | None = None,
    reason: str = "",
) -> bool:
    """Atomically increment a usage counter and verify it stays within limit.

    Returns True if the increment succeeded, False if it would exceed the limit.
    Uses SELECT ... FOR UPDATE to prevent race conditions.

    Records a usage event in the append-only ledger.
    """
    if limit_key not in LIMIT_KEYS:
        raise AppError(
            422,
            "UNKNOWN_LIMIT_KEY",
            "Invalid input",
            f"Unknown limit key: {limit_key}",
        )

    entitlements = get_effective_entitlements(db, restaurant_id=restaurant_id)
    if entitlements is None:
        return False

    plan_limit = entitlements["limits"].get(limit_key)
    if plan_limit is None:
        # No explicit limit means unlimited - still record the event
        row = _get_or_create_usage_row(db, restaurant_id)
        _apply_change_to_usage_row(row, limit_key, increment)
        _record_usage_event(
            db,
            restaurant_id=restaurant_id,
            resource_type=limit_key,
            change=increment,
            actor_admin_id=actor_admin_id,
            reason=reason or "unlimited",
        )
        return True

    # Lock the usage row for atomic check-and-increment
    row = _get_or_create_usage_row(db, restaurant_id)
    counter_attr = f"{LIMIT_KEY_TO_RESOURCE[limit_key]}_count"
    current = getattr(row, counter_attr)

    if current + increment > plan_limit:
        # Record the rejected attempt as a usage event with change 0
        _record_usage_event(
            db,
            restaurant_id=restaurant_id,
            resource_type=limit_key,
            change=0,
            actor_admin_id=actor_admin_id,
            reason=reason or f"limit_exceeded:{current}/{plan_limit}",
        )
        return False

    _apply_change_to_usage_row(row, limit_key, increment)
    _record_usage_event(
        db,
        restaurant_id=restaurant_id,
        resource_type=limit_key,
        change=increment,
        actor_admin_id=actor_admin_id,
        reason=reason or "consumed",
    )
    return True


def release_limit(
    db: Session,
    *,
    restaurant_id: UUID,
    limit_key: str,
    decrement: int = 1,
    actor_admin_id: UUID | None = None,
    reason: str = "",
) -> bool:
    """Atomically decrement a usage counter (e.g., when a staff member is deleted).

    Returns True if the decrement succeeded.
    """
    if limit_key not in LIMIT_KEYS:
        raise AppError(
            422,
            "UNKNOWN_LIMIT_KEY",
            "Invalid input",
            f"Unknown limit key: {limit_key}",
        )

    row = _get_or_create_usage_row(db, restaurant_id)
    counter_attr = f"{LIMIT_KEY_TO_RESOURCE[limit_key]}_count"
    current = getattr(row, counter_attr)
    actual = min(current, decrement)
    if actual > 0:
        _apply_change_to_usage_row(row, limit_key, -actual)
    _record_usage_event(
        db,
        restaurant_id=restaurant_id,
        resource_type=limit_key,
        change=-actual,
        actor_admin_id=actor_admin_id,
        reason=reason or "released",
    )
    return True


def reconcile_usage_counters(
    db: Session, *, restaurant_id: UUID
) -> dict[str, int]:
    """Reconcile cached usage counters against actual usage events.

    Recomputes each counter from the usage_events ledger and updates the
    usage row. Returns the previous and current values for each counter.
    """
    row = _get_or_create_usage_row(db, restaurant_id)

    previous = {}
    current = {}

    for limit_key, resource in LIMIT_KEY_TO_RESOURCE.items():
        attr = f"{resource}_count"
        prev = getattr(row, attr)
        previous[attr] = prev

        # Sum all changes from usage events (events use the plural limit key).
        result = db.scalar(
            select(func.coalesce(func.sum(PlatformUsageEvent.change), 0)).where(
                PlatformUsageEvent.restaurant_id == restaurant_id,
                PlatformUsageEvent.resource_type == limit_key,
            )
        )
        new_value = max(0, int(result or 0))
        current[attr] = new_value
        setattr(row, attr, new_value)

    db.flush()
    db.commit()
    return {"previous": previous, "current": current}


def backfill_usage_counters(
    db: Session, *, restaurant_id: UUID | None = None
) -> dict[str, dict[str, int]]:
    """Recompute cached counters from the actual tenant tables.

    Idempotent: running it twice produces no extra ledger rows. Each changed
    counter appends a single adjustment event so the append-only ledger and the
    cached row stay reconcilable.

    ``restaurant_id`` limits the run to one tenant; omit it to backfill every
    restaurant. The caller owns the transaction/commit.
    """
    params = {"rid": restaurant_id} if restaurant_id is not None else {}
    where = "WHERE id = :rid" if restaurant_id is not None else ""
    ids = db.execute(
        text(f"SELECT id FROM restaurants {where}"), params
    ).scalars().all()

    counts_sql = text(
        """
        SELECT
            (SELECT count(*) FROM branches
              WHERE restaurant_id = :rid) AS branch_count,
            (SELECT count(*) FROM restaurant_memberships
              WHERE restaurant_id = :rid AND role = 'owner'
                AND status <> 'REMOVED') AS owner_count,
            (SELECT count(*) FROM restaurant_memberships
              WHERE restaurant_id = :rid AND role = 'manager'
                AND status <> 'REMOVED') AS manager_count,
            (SELECT count(*) FROM restaurant_memberships
              WHERE restaurant_id = :rid AND role = 'waiter'
                AND status <> 'REMOVED') AS waiter_count,
            (SELECT count(*) FROM restaurant_memberships
              WHERE restaurant_id = :rid AND role = 'kitchen'
                AND status <> 'REMOVED') AS kitchen_count,
            (SELECT count(*) FROM restaurant_memberships
              WHERE restaurant_id = :rid AND role = 'cashier'
                AND status <> 'REMOVED') AS cashier_count,
            (SELECT count(*) FROM restaurant_tables
              WHERE branch_id = :rid AND status <> 'ARCHIVED') AS table_count
        """
    )

    summary: dict[str, dict[str, int]] = {}
    for rid in ids:
        actual = dict(db.execute(counts_sql, {"rid": rid}).mappings().one())
        row = _get_or_create_usage_row(db, rid)
        changed: dict[str, int] = {}
        for attr, new_value in actual.items():
            old_value = getattr(row, attr)
            delta = int(new_value) - int(old_value)
            if delta == 0:
                continue
            setattr(row, attr, int(new_value))
            # attr is "branch_count" -> singular "branch" -> plural limit key "branches"
            singular = attr.removesuffix("_count")
            plural = {
                "branch": "branches",
                "owner": "owners",
                "manager": "managers",
                "waiter": "waiters",
                "kitchen": "kitchen",
                "cashier": "cashier",
                "table": "tables",
            }[singular]
            _record_usage_event(
                db,
                restaurant_id=rid,
                resource_type=plural,
                change=delta,
                actor_admin_id=None,
                reason="backfill from tenant tables",
            )
            changed[attr] = delta
        summary[str(rid)] = changed

    db.flush()
    return summary


def get_usage_status(
    db: Session, *, restaurant_id: UUID
) -> dict | None:
    """Get current usage status with limits for a tenant's dashboard.

    Returns None if no active subscription.
    """
    entitlements = get_effective_entitlements(db, restaurant_id=restaurant_id)
    if entitlements is None:
        return None

    row = _get_or_create_usage_row(db, restaurant_id)

    usage = {}
    limits = entitlements["limits"]
    # Key usage by the plural plan-limit key (branches, waiters, ...) so it lines
    # up with check_limit_available/consume_limit and the plan definitions.
    for limit_key, resource in LIMIT_KEY_TO_RESOURCE.items():
        attr = f"{resource}_count"
        current = getattr(row, attr)
        limit = limits.get(limit_key)
        usage[limit_key] = {
            "current": current,
            "limit": limit,
            "remaining": None if limit is None else max(0, limit - current),
            "at_limit": limit is not None and current >= limit,
        }

    return {
        "restaurant_id": str(restaurant_id),
        "subscription_id": entitlements["subscription_id"],
        "plan_version_id": entitlements["plan_version_id"],
        "usage": usage,
    }
