"""Platform plan catalogue (plan 05 §5)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.platform.deps import (
    PlatformActor,
    require_platform_permission,
    require_platform_step_up,
)
from app.modules.platform.models import PlatformPlan, PlatformSubscription
from app.modules.platform.schemas_admin import (
    PlanCreateRequest,
    PlanUpdateRequest,
    PlanVersionCreateRequest,
    PlanVersionUpdateRequest,
    PlanVersionPublishRequest,
    PlanFeatureRequest,
    PlanLimitRequest,
    ReasonConfirmRequest,
)
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.common import require_confirm, require_reason, now_utc
from app.modules.platform.services.plan_versions import (
    create_plan_version,
    get_plan_versions,
    get_active_plan_version,
    update_plan_version,
    publish_plan_version,
    add_plan_feature,
    add_plan_limit,
    get_plan_entitlements,
    get_subscription_entitlements,
    _serialize_version,
)
from app.shared.errors import AppError

router = APIRouter(tags=["platform-plans"])

_LIVE = ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE", "SUSPENDED")


def _validate_entitlements(value: dict | None) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise AppError(422, "INVALID_ENTITLEMENTS", "Invalid input", "Entitlements must be an object.")
    for key, entry in value.items():
        if not isinstance(entry, dict):
            raise AppError(
                422,
                "INVALID_ENTITLEMENTS",
                "Invalid input",
                f"Entitlement {key!r} must be an object.",
            )
        if "limit" in entry and (not isinstance(entry["limit"], int) or entry["limit"] < 0):
            raise AppError(
                422,
                "INVALID_ENTITLEMENTS",
                "Invalid input",
                f"Entitlement {key!r} limit must be a non-negative integer.",
            )
        if "enabled" in entry and not isinstance(entry["enabled"], bool):
            raise AppError(
                422,
                "INVALID_ENTITLEMENTS",
                "Invalid input",
                f"Entitlement {key!r} enabled must be true or false.",
            )


def _live_count(db: Session, plan_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(PlatformSubscription)
            .where(
                PlatformSubscription.plan_id == plan_id,
                PlatformSubscription.status.in_(_LIVE),
            )
        )
        or 0
    )


def _serialize(db: Session, plan: PlatformPlan) -> dict:
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "price_monthly_minor": plan.price_monthly_minor,
        "price_annual_minor": plan.price_annual_minor,
        "currency_code": plan.currency_code,
        "trial_days": plan.trial_days,
        "entitlements": plan.entitlements,
        "status": plan.status,
        "is_public": plan.is_public,
        "sort_order": plan.sort_order,
        "archived_at": plan.archived_at,
        "active_subscriptions": _live_count(db, plan.id),
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@router.get("/plans")
def list_plans(
    include_archived: bool = False,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    query = select(PlatformPlan)
    if not include_archived:
        query = query.where(PlatformPlan.status != "ARCHIVED")
    plans = db.scalars(query.order_by(PlatformPlan.sort_order, PlatformPlan.name)).all()
    return {"items": [_serialize(db, plan) for plan in plans]}


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    code = payload.code.strip().lower()
    if db.scalar(select(PlatformPlan).where(PlatformPlan.code == code)):
        raise AppError(409, "PLAN_CODE_EXISTS", "Conflict", "That plan code already exists.")
    _validate_entitlements(payload.entitlements)
    plan = PlatformPlan(
        code=code,
        name=payload.name.strip(),
        description=payload.description,
        price_monthly_minor=payload.price_monthly_minor,
        price_annual_minor=payload.price_annual_minor,
        currency_code=payload.currency_code.upper(),
        trial_days=payload.trial_days,
        entitlements=payload.entitlements,
        status="ACTIVE",
        is_public=payload.is_public,
        sort_order=payload.sort_order,
        created_by_admin_id=actor.admin_id,
    )
    db.add(plan)
    db.flush()
    write_platform_audit(
        db,
        action="PLAN_CREATED",
        entity_type="platform_plan",
        entity_id=str(plan.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        after={"code": plan.code, "name": plan.name},
    )
    db.commit()
    return _serialize(db, plan)


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    return _serialize(db, plan)


@router.patch("/plans/{plan_id}")
def update_plan(
    plan_id: UUID,
    payload: PlanUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    changes = payload.model_dump(exclude_unset=True, exclude={"reason"})
    if "entitlements" in changes:
        _validate_entitlements(changes["entitlements"])
    before = {key: getattr(plan, key) for key in changes}
    for key, value in changes.items():
        setattr(plan, key, value)
    plan.updated_at = now_utc()
    write_platform_audit(
        db,
        action="PLAN_UPDATED",
        entity_type="platform_plan",
        entity_id=str(plan.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        before=before,
        after={key: getattr(plan, key) for key in changes},
    )
    db.commit()
    return _serialize(db, plan)


@router.post("/plans/{plan_id}/archive")
def archive_plan(
    plan_id: UUID,
    payload: ReasonConfirmRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    reason = require_reason(payload.reason)
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise AppError(404, "PLAN_NOT_FOUND", "Not found", "Plan not found.")
    require_confirm(payload.confirm, plan.code)
    live = _live_count(db, plan.id)
    if live:
        raise AppError(
            409,
            "PLAN_IN_USE",
            "Conflict",
            f"{live} live subscription(s) still use this plan.",
            extra={"active_subscriptions": live},
        )
    plan.status = "ARCHIVED"
    plan.archived_at = now_utc()
    plan.updated_at = now_utc()
    write_platform_audit(
        db,
        action="PLAN_ARCHIVED",
        entity_type="platform_plan",
        entity_id=str(plan.id),
        actor_admin_id=actor.admin_id,
        actor_email=actor.email,
        reason=reason,
        request=request,
        before={"status": "ACTIVE"},
        after={"status": "ARCHIVED"},
    )
    db.commit()
    return _serialize(db, plan)


# ---------------------------------------------------------------------------
# Plan version endpoints (Plan 01)
# ---------------------------------------------------------------------------


@router.get("/plans/{plan_id}/versions")
def list_plan_versions(
    plan_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List all versions of a plan."""
    versions = get_plan_versions(db, plan_id)
    active = get_active_plan_version(db, plan_id)
    return {
        "items": versions,
        "active_version": _serialize_version(db, active) if active else None,
    }


@router.post("/plans/{plan_id}/versions", status_code=status.HTTP_201_CREATED)
def create_plan_version_endpoint(
    plan_id: UUID,
    payload: PlanVersionCreateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new draft version of a plan."""
    version = create_plan_version(
        db,
        plan_id=plan_id,
        price_monthly_minor=payload.price_monthly_minor,
        price_annual_minor=payload.price_annual_minor,
        currency_code=payload.currency_code,
        trial_days=payload.trial_days,
        effective_from=payload.effective_from,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return _serialize_version(db, version)


@router.get("/plans/versions/{version_id}")
def get_plan_version(
    version_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Get a specific plan version with its features and limits."""
    version = get_active_plan_version(db, version_id)  # placeholder, will be replaced
    from app.modules.platform.models import PlatformPlanVersion

    v = db.get(PlatformPlanVersion, version_id)
    if v is None:
        raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Not found", "Plan version not found.")
    return _serialize_version(db, v)


@router.patch("/plans/versions/{version_id}")
def update_plan_version_endpoint(
    version_id: UUID,
    payload: PlanVersionUpdateRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Update a draft plan version."""
    version = update_plan_version(
        db,
        version_id=version_id,
        price_monthly_minor=payload.price_monthly_minor,
        price_annual_minor=payload.price_annual_minor,
        currency_code=payload.currency_code,
        trial_days=payload.trial_days,
        effective_from=payload.effective_from,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return _serialize_version(db, version)


@router.post("/plans/versions/{version_id}/publish")
def publish_plan_version_endpoint(
    version_id: UUID,
    payload: PlanVersionPublishRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Publish a draft version, making it active for new subscriptions."""
    version = publish_plan_version(
        db,
        version_id=version_id,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return _serialize_version(db, version)


@router.get("/plans/versions/{version_id}/features")
def list_plan_features(
    version_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List features for a plan version."""
    from app.modules.platform.models import PlatformPlanVersion

    v = db.get(PlatformPlanVersion, version_id)
    if v is None:
        raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Not found", "Plan version not found.")
    entitlements = get_plan_entitlements(db, version_id)
    return {"version_id": version_id, "features": entitlements["features"]}


@router.post("/plans/versions/{version_id}/features", status_code=status.HTTP_201_CREATED)
def add_plan_feature_endpoint(
    version_id: UUID,
    payload: PlanFeatureRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Add or update a feature on a plan version (draft only)."""
    feature = add_plan_feature(
        db,
        version_id=version_id,
        feature_key=payload.feature_key,
        enabled=payload.enabled,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return {"feature_key": feature.feature_key, "enabled": feature.enabled}


@router.get("/plans/versions/{version_id}/limits")
def list_plan_limits(
    version_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    """List limits for a plan version."""
    from app.modules.platform.models import PlatformPlanVersion

    v = db.get(PlatformPlanVersion, version_id)
    if v is None:
        raise AppError(404, "PLAN_VERSION_NOT_FOUND", "Not found", "Plan version not found.")
    entitlements = get_plan_entitlements(db, version_id)
    return {"version_id": version_id, "limits": entitlements["limits"]}


@router.post(
    "/plans/versions/{version_id}/limits", status_code=status.HTTP_201_CREATED
)
def add_plan_limit_endpoint(
    version_id: UUID,
    payload: PlanLimitRequest,
    request: Request,
    actor: PlatformActor = Depends(require_platform_permission("plan.manage")),
    _: PlatformActor = Depends(require_platform_step_up),
    db: Session = Depends(get_db),
) -> dict:
    """Add or update a usage limit on a plan version (draft only)."""
    limit = add_plan_limit(
        db,
        version_id=version_id,
        limit_key=payload.limit_key,
        limit_value=payload.limit_value,
        admin_id=actor.admin_id,
        reason=payload.reason,
        request=request,
    )
    return {"limit_key": limit.limit_key, "limit_value": limit.limit_value}


@router.get("/plans/{plan_id}/entitlements")
def get_plan_entitlements_endpoint(
    plan_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("plan.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Get the active version's entitlements for a plan."""
    active = get_active_plan_version(db, plan_id)
    if active is None:
        return {"plan_id": plan_id, "active_version": None, "features": {}, "limits": {}}
    entitlements = get_plan_entitlements(db, active.id)
    return {
        "plan_id": plan_id,
        "active_version": {
            "id": str(active.id),
            "version": active.version,
        },
        "features": entitlements["features"],
        "limits": entitlements["limits"],
    }


@router.get("/subscriptions/{subscription_id}/entitlements")
def get_subscription_entitlements_endpoint(
    subscription_id: UUID,
    actor: PlatformActor = Depends(require_platform_permission("subscription.view")),
    db: Session = Depends(get_db),
) -> dict:
    """Get the effective entitlements for a subscription's tenant."""
    from app.modules.platform.models import PlatformSubscription

    sub = db.get(PlatformSubscription, subscription_id)
    if sub is None:
        raise AppError(
            404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription not found."
        )
    entitlements = get_subscription_entitlements(db, sub.restaurant_id)
    if entitlements is None:
        return {
            "subscription_id": subscription_id,
            "restaurant_id": sub.restaurant_id,
            "entitlements": None,
        }
    return {
        "subscription_id": subscription_id,
        "restaurant_id": sub.restaurant_id,
        "entitlements": entitlements,
    }

