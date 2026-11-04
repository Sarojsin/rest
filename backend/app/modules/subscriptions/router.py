from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.subscriptions.models import (
    Subscription,
    SubscriptionBillingInfo,
    SubscriptionPlan,
)
from app.modules.subscriptions.schemas import (
    SubscriptionBillingInfoIn,
    SubscriptionBillingInfoOut,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionPlanIn,
    SubscriptionPlanOut,
)
from app.shared.errors import AppError

router = APIRouter(tags=["subscriptions"])

_INTERVAL_DAYS = {"MONTHLY": 30, "QUARTERLY": 90, "ANNUAL": 365}


# ── SubscriptionPlans ─────────────────────────────────────────────────────

@router.get("/plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(
    include_inactive: bool = False,
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> list[SubscriptionPlanOut]:
    stmt = select(SubscriptionPlan).where(
        SubscriptionPlan.restaurant_id == actor.restaurant_id
    )
    if not include_inactive:
        stmt = stmt.where(SubscriptionPlan.is_active.is_(True))
    plans = db.scalars(stmt.order_by(SubscriptionPlan.price_minor)).all()
    return [SubscriptionPlanOut.model_validate(p) for p in plans]


@router.post("/plans", response_model=SubscriptionPlanOut, status_code=201)
def create_subscription_plan(
    payload: SubscriptionPlanIn,
    actor: Actor = Depends(require_permission("subscriptions.manage")),
    db: Session = Depends(get_db),
) -> SubscriptionPlanOut:
    existing = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.restaurant_id == actor.restaurant_id,
            SubscriptionPlan.name == payload.name,
        )
    )
    if existing:
        raise AppError(
            409, "PLAN_NAME_EXISTS", "Plan name in use",
            "A subscription plan with this name already exists.",
        )

    plan = SubscriptionPlan(
        restaurant_id=actor.restaurant_id,
        name=payload.name,
        description=payload.description,
        price_minor=payload.price_minor,
        billing_interval=payload.billing_interval,
        trial_days=payload.trial_days,
        features=payload.features,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return SubscriptionPlanOut.model_validate(plan)


# ── Subscriptions ─────────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionOut | None)
def get_subscription(
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> SubscriptionOut | None:
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.restaurant_id == actor.restaurant_id,
            Subscription.membership_id == actor.membership.id,
        )
    )
    if subscription is None:
        return None
    return SubscriptionOut.model_validate(subscription)


@router.post("/subscription", response_model=SubscriptionOut, status_code=201)
def create_subscription(
    payload: SubscriptionIn,
    actor: Actor = Depends(require_permission("subscriptions.create")),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if plan is None or plan.restaurant_id != actor.restaurant_id or not plan.is_active:
        raise AppError(
            404, "SUBSCRIPTION_PLAN_NOT_FOUND", "Plan not found",
            "Subscription plan was not found or is not active.",
        )

    existing = db.scalar(
        select(Subscription).where(
            Subscription.restaurant_id == actor.restaurant_id,
            Subscription.membership_id == actor.membership.id,
        )
    )
    if existing is not None and existing.status in {"ACTIVE", "TRIAL"}:
        raise AppError(
            409, "SUBSCRIPTION_ALREADY_ACTIVE", "Subscription already active",
            "This membership already has an active subscription.",
        )
    if existing is not None:
        raise AppError(
            409, "SUBSCRIPTION_EXISTS", "Subscription exists",
            "A subscription already exists for this membership.",
        )

    now = datetime.now(UTC)
    if payload.status == "TRIAL" and plan.trial_days:
        end = now + timedelta(days=plan.trial_days)
    else:
        end = now + timedelta(
            days=_INTERVAL_DAYS.get(plan.billing_interval, 30)
        )

    subscription = Subscription(
        restaurant_id=actor.restaurant_id,
        membership_id=actor.membership.id,
        plan_id=plan.id,
        status=payload.status,
        started_at=now,
        billing_cycle_end=end,
        cancel_at_period_end=payload.cancel_at_period_end,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return SubscriptionOut.model_validate(subscription)


@router.patch("/subscription", response_model=SubscriptionOut)
def update_subscription(
    cancel_at_period_end: bool | None = None,
    status: str | None = None,
    actor: Actor = Depends(require_permission("subscriptions.manage")),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.restaurant_id == actor.restaurant_id,
            Subscription.membership_id == actor.membership.id,
        )
    )
    if subscription is None:
        raise AppError(
            404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription was not found."
        )
    if cancel_at_period_end is not None:
        subscription.cancel_at_period_end = cancel_at_period_end
    if status is not None:
        if status not in {"TRIAL", "ACTIVE", "PAST_DUE", "CANCELLED"}:
            raise AppError(
                422, "INVALID_STATUS", "Invalid status",
                "Status must be TRIAL, ACTIVE, PAST_DUE, or CANCELLED.",
            )
        subscription.status = status
        if status == "CANCELLED":
            subscription.canceled_at = datetime.now(UTC)
    db.commit()
    db.refresh(subscription)
    return SubscriptionOut.model_validate(subscription)


# ── SubscriptionBillingInfo ───────────────────────────────────────────────

@router.get("/billing", response_model=list[SubscriptionBillingInfoOut])
def list_billing_info(
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> list[SubscriptionBillingInfoOut]:
    rows = db.scalars(
        select(SubscriptionBillingInfo)
        .where(SubscriptionBillingInfo.restaurant_id == actor.restaurant_id)
        .order_by(SubscriptionBillingInfo.billing_date.desc())
    ).all()
    return [SubscriptionBillingInfoOut.model_validate(r) for r in rows]


@router.post("/billing", response_model=SubscriptionBillingInfoOut, status_code=201)
def create_billing_info(
    payload: SubscriptionBillingInfoIn,
    actor: Actor = Depends(require_permission("subscriptions.manage")),
    db: Session = Depends(get_db),
) -> SubscriptionBillingInfoOut:
    subscription = db.get(Subscription, payload.subscription_id)
    if subscription is None or subscription.restaurant_id != actor.restaurant_id:
        raise AppError(
            404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription was not found."
        )

    billing = SubscriptionBillingInfo(
        restaurant_id=actor.restaurant_id,
        subscription_id=subscription.id,
        amount_minor=payload.amount_minor,
        currency_code=payload.currency_code,
        billing_date=payload.billing_date,
        status=payload.status,
    )
    db.add(billing)
    db.commit()
    db.refresh(billing)
    return SubscriptionBillingInfoOut.model_validate(billing)
