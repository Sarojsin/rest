"""Plan version and entitlement service (Plan 01).

Handles versioned plan pricing, features, and limits. Key rules:

- Existing subscribers remain on their plan version until explicitly migrated.
- Changing a plan's price or limits only affects new subscriptions created
  after the new version is published.
- Only one version can be active per plan at a time.
- Draft versions can be edited; published versions are immutable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.modules.platform.models import (
    PlatformPlan,
    PlatformPlanVersion,
    PlatformPlanFeature,
    PlatformPlanLimit,
    PlatformSubscription,
)
from app.modules.platform.services.audit import write_platform_audit
from app.shared.errors import AppError


def _now() -> datetime:
    return datetime.now(UTC)


def _validate_feature_key(key: str) -> str:
    key = key.strip().lower()
    if not key or not key[0].isalpha() or not all(c.isalnum() or c == "_" for c in key):
        raise AppError(
            422,
            "INVALID_FEATURE_KEY",
            "Invalid input",
            "Feature key must start with a letter and contain only letters, numbers, and underscores.",
        )
    return key


def _validate_limit_key(key: str) -> str:
    key = key.strip().lower()
    if not key or not key[0].isalpha() or not all(c.isalnum() or c == "_" for c in key):
        raise AppError(
            422,
            "INVALID_LIMIT_KEY",
            "Invalid input",
            "Limit key must start with a letter and contain only letters, numbers, and underscores.",
        )
    return key


def _get_plan(db: Session, plan_id: UUID) -> PlatformPlan:
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    return plan


def _get_version(db: Session, version_id: UUID) -> PlatformPlanVersion:
    version = db.get(PlatformPlanVersion, version_id)
    if version is None:
        raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Not found", "Plan version not found.")
    return version


def _next_version_number(db: Session, plan_id: UUID) -> int:
    result = db.scalar(
        select(func.coalesce(func.max(PlatformPlanVersion.version), 0) + 1).where(
            PlatformPlanVersion.plan_id == plan_id
        )
    )
    return int(result or 1)


def _serialize_version(db: Session, version: PlatformPlanVersion) -> dict:
    """Serialize a plan version with its features and limits."""
    features = db.scalars(
        select(PlatformPlanFeature).where(
            PlatformPlanFeature.plan_version_id == version.id
        )
    ).all()
    limits = db.scalars(
        select(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == version.id
        )
    ).all()
    return {
        "id": str(version.id),
        "plan_id": str(version.plan_id),
        "version": version.version,
        "price_monthly_minor": version.price_monthly_minor,
        "price_annual_minor": version.price_annual_minor,
        "currency_code": version.currency_code,
        "trial_days": version.trial_days,
        "effective_from": version.effective_from,
        "effective_to": version.effective_to,
        "is_active": version.is_active,
        "features": {f.feature_key: f.enabled for f in features},
        "limits": {l.limit_key: l.limit_value for l in limits},
        "created_at": version.created_at,
        "updated_at": version.updated_at,
    }


# ---------------------------------------------------------------------------
# Plan version CRUD
# ---------------------------------------------------------------------------


def create_plan_version(
    db: Session,
    *,
    plan_id: UUID,
    price_monthly_minor: int,
    price_annual_minor: int,
    currency_code: str,
    trial_days: int,
    effective_from: datetime | None,
    admin_id: UUID,
    reason: str,
    request=None,
) -> PlatformPlanVersion:
    """Create a new version of a plan.

    The new version starts as a draft (is_active=False). Its version number
    is one higher than the current maximum for the plan.
    """
    plan = _get_plan(db, plan_id)

    version_number = _next_version_number(db, plan_id)
    effective_from_value = effective_from or _now()

    version = PlatformPlanVersion(
        plan_id=plan_id,
        version=version_number,
        price_monthly_minor=price_monthly_minor,
        price_annual_minor=price_annual_minor,
        currency_code=currency_code.upper(),
        trial_days=trial_days,
        effective_from=effective_from_value,
        is_active=False,
    )
    db.add(version)
    db.flush()

    write_platform_audit(
        db,
        action="PLAN_VERSION_CREATED",
        entity_type="platform_plan_version",
        entity_id=str(version.id),
        actor_admin_id=admin_id,
        actor_email=None,
        restaurant_id=None,
        reason=reason,
        request=request,
        after={
            "plan_id": str(plan_id),
            "version": version_number,
            "price_monthly_minor": price_monthly_minor,
            "price_annual_minor": price_annual_minor,
            "currency_code": currency_code.upper(),
            "trial_days": trial_days,
        },
    )
    db.commit()
    db.refresh(version)
    return version


def get_plan_versions(db: Session, plan_id: UUID) -> list[dict]:
    """List all versions of a plan, ordered by version number."""
    _get_plan(db, plan_id)
    versions = db.scalars(
        select(PlatformPlanVersion)
        .where(PlatformPlanVersion.plan_id == plan_id)
        .order_by(PlatformPlanVersion.version)
    ).all()
    return [_serialize_version(db, v) for v in versions]


def get_active_plan_version(db: Session, plan_id: UUID) -> PlatformPlanVersion | None:
    """Get the active version of a plan, or None if none is published."""
    return db.scalar(
        select(PlatformPlanVersion).where(
            PlatformPlanVersion.plan_id == plan_id,
            PlatformPlanVersion.is_active == True,  # noqa: E712
        )
    )


def update_plan_version(
    db: Session,
    *,
    version_id: UUID,
    price_monthly_minor: int | None,
    price_annual_minor: int | None,
    currency_code: str | None,
    trial_days: int | None,
    effective_from: datetime | None,
    admin_id: UUID,
    reason: str,
    request=None,
) -> PlatformPlanVersion:
    """Update a draft plan version. Only non-active versions can be edited."""
    version = _get_version(db, version_id)
    if version.is_active:
        raise AppError(
            409,
            "PLAN_VERSION_ACTIVE",
            "Conflict",
            "Cannot edit a published version. Create a new version instead.",
        )

    before = {
        "price_monthly_minor": version.price_monthly_minor,
        "price_annual_minor": version.price_annual_minor,
        "currency_code": version.currency_code,
        "trial_days": version.trial_days,
        "effective_from": version.effective_from,
    }

    if price_monthly_minor is not None:
        version.price_monthly_minor = price_monthly_minor
    if price_annual_minor is not None:
        version.price_annual_minor = price_annual_minor
    if currency_code is not None:
        version.currency_code = currency_code.upper()
    if trial_days is not None:
        version.trial_days = trial_days
    if effective_from is not None:
        version.effective_from = effective_from

    write_platform_audit(
        db,
        action="PLAN_VERSION_UPDATED",
        entity_type="platform_plan_version",
        entity_id=str(version.id),
        actor_admin_id=admin_id,
        actor_email=None,
        restaurant_id=None,
        reason=reason,
        request=request,
        before=before,
        after={
            "price_monthly_minor": version.price_monthly_minor,
            "price_annual_minor": version.price_annual_minor,
            "currency_code": version.currency_code,
            "trial_days": version.trial_days,
            "effective_from": version.effective_from,
        },
    )
    db.commit()
    db.refresh(version)
    return version


def publish_plan_version(
    db: Session,
    *,
    version_id: UUID,
    admin_id: UUID,
    reason: str,
    request=None,
) -> PlatformPlanVersion:
    """Publish a draft version, making it the active version for new subscriptions.

    Deactivates the previously active version for the same plan.
    """
    version = _get_version(db, version_id)
    if version.is_active:
        raise AppError(
            409,
            "PLAN_VERSION_ALREADY_ACTIVE",
            "Conflict",
            "This version is already active.",
        )

    # Deactivate the previously active version for this plan
    db.execute(
        __import__("sqlalchemy").update(PlatformPlanVersion)
        .where(
            PlatformPlanVersion.plan_id == version.plan_id,
            PlatformPlanVersion.is_active == True,  # noqa: E712
        )
        .values(is_active=False)
    )

    version.is_active = True

    write_platform_audit(
        db,
        action="PLAN_VERSION_PUBLISHED",
        entity_type="platform_plan_version",
        entity_id=str(version.id),
        actor_admin_id=admin_id,
        actor_email=None,
        restaurant_id=None,
        reason=reason,
        request=request,
        after={
            "plan_id": str(version.plan_id),
            "version": version.version,
            "is_active": True,
        },
    )
    db.commit()
    db.refresh(version)
    return version


# ---------------------------------------------------------------------------
# Features and limits
# ---------------------------------------------------------------------------


def add_plan_feature(
    db: Session,
    *,
    version_id: UUID,
    feature_key: str,
    enabled: bool,
    admin_id: UUID,
    reason: str,
    request=None,
) -> PlatformPlanFeature:
    """Add or update a feature on a plan version. Only draft versions can be edited."""
    version = _get_version(db, version_id)
    if version.is_active:
        raise AppError(
            409,
            "PLAN_VERSION_ACTIVE",
            "Conflict",
            "Cannot edit features on a published version.",
        )

    feature_key = _validate_feature_key(feature_key)

    existing = db.scalar(
        select(PlatformPlanFeature).where(
            PlatformPlanFeature.plan_version_id == version_id,
            PlatformPlanFeature.feature_key == feature_key,
        )
    )
    if existing:
        before = {"enabled": existing.enabled}
        existing.enabled = enabled
        write_platform_audit(
            db,
            action="PLAN_FEATURE_UPDATED",
            entity_type="platform_plan_feature",
            entity_id=str(existing.id),
            actor_admin_id=admin_id,
            actor_email=None,
            restaurant_id=None,
            reason=reason,
            request=request,
            before=before,
            after={"enabled": enabled},
        )
        db.commit()
        db.refresh(existing)
        return existing

    feature = PlatformPlanFeature(
        plan_version_id=version_id,
        feature_key=feature_key,
        enabled=enabled,
    )
    db.add(feature)
    db.flush()

    write_platform_audit(
        db,
        action="PLAN_FEATURE_ADDED",
        entity_type="platform_plan_feature",
        entity_id=str(feature.id),
        actor_admin_id=admin_id,
        actor_email=None,
        restaurant_id=None,
        reason=reason,
        request=request,
        after={"feature_key": feature_key, "enabled": enabled},
    )
    db.commit()
    db.refresh(feature)
    return feature


def add_plan_limit(
    db: Session,
    *,
    version_id: UUID,
    limit_key: str,
    limit_value: int,
    admin_id: UUID,
    reason: str,
    request=None,
) -> PlatformPlanLimit:
    """Add or update a usage limit on a plan version. Only draft versions can be edited."""
    version = _get_version(db, version_id)
    if version.is_active:
        raise AppError(
            409,
            "PLAN_VERSION_ACTIVE",
            "Conflict",
            "Cannot edit limits on a published version.",
        )

    limit_key = _validate_limit_key(limit_key)

    existing = db.scalar(
        select(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == version_id,
            PlatformPlanLimit.limit_key == limit_key,
        )
    )
    if existing:
        before = {"limit_value": existing.limit_value}
        existing.limit_value = limit_value
        write_platform_audit(
            db,
            action="PLAN_LIMIT_UPDATED",
            entity_type="platform_plan_limit",
            entity_id=str(existing.id),
            actor_admin_id=admin_id,
            actor_email=None,
            restaurant_id=None,
            reason=reason,
            request=request,
            before=before,
            after={"limit_value": limit_value},
        )
        db.commit()
        db.refresh(existing)
        return existing

    limit = PlatformPlanLimit(
        plan_version_id=version_id,
        limit_key=limit_key,
        limit_value=limit_value,
    )
    db.add(limit)
    db.flush()

    write_platform_audit(
        db,
        action="PLAN_LIMIT_ADDED",
        entity_type="platform_plan_limit",
        entity_id=str(limit.id),
        actor_admin_id=admin_id,
        actor_email=None,
        restaurant_id=None,
        reason=reason,
        request=request,
        after={"limit_key": limit_key, "limit_value": limit_value},
    )
    db.commit()
    db.refresh(limit)
    return limit


def get_plan_entitlements(db: Session, plan_version_id: UUID) -> dict:
    """Get the effective features and limits for a plan version."""
    version = _get_version(db, plan_version_id)
    features = db.scalars(
        select(PlatformPlanFeature).where(
            PlatformPlanFeature.plan_version_id == plan_version_id
        )
    ).all()
    limits = db.scalars(
        select(PlatformPlanLimit).where(
            PlatformPlanLimit.plan_version_id == plan_version_id
        )
    ).all()
    return {
        "features": {f.feature_key: f.enabled for f in features},
        "limits": {l.limit_key: l.limit_value for l in limits},
    }


def get_subscription_entitlements(db: Session, restaurant_id: UUID) -> dict | None:
    """Get the effective entitlements for a tenant's active subscription."""
    subscription = db.scalar(
        select(PlatformSubscription).where(
            PlatformSubscription.restaurant_id == restaurant_id,
            PlatformSubscription.status.in_(
                ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE", "SUSPENDED")
            ),
        )
    )
    if subscription is None:
        return None
    if subscription.plan_version_id is None:
        return None
    return get_plan_entitlements(db, subscription.plan_version_id)
