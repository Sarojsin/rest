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
    ReasonConfirmRequest,
)
from app.modules.platform.services.audit import write_platform_audit
from app.modules.platform.services.common import require_confirm, require_reason, now_utc
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
