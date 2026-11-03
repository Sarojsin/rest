from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.subscriptions.models import SubscriptionPlan, Subscription, SubscriptionBillingInfo
from app.modules.subscriptions.schemas import (
    SubscriptionPlanOut,
    SubscriptionPlanIn,
    SubscriptionOut,
    SubscriptionIn,
    SubscriptionBillingInfoOut,
    SubscriptionBillingInfoIn,
)
from app.shared.errors import AppError

router = APIRouter(tags=["subscriptions"])


# ── SubscriptionPlans ─────────────────────────────────────────────────────

@router.get("/plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> list[SubscriptionPlanOut]:
    plans = db.scalars(
        select(SubscriptionPlan).where(SubscriptionPlan.restaurant_id == actor.restaurant_id, SubscriptionPlan.is_active)
    ).all()
    return [SubscriptionPlanOut.model_validate(p) for p in plans]


@router.post("/plans", response_model=SubscriptionPlanOut)
def create_subscription_plan(
    payload: SubscriptionPlanIn,
    actor: Actor = Depends(require_permission("subscriptions.manage")),
    db: Session = Depends(get_db),
) -> SubscriptionPlanOut:
    # Check for duplicate name
    existing = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.restaurant_id == actor.restaurant_id,
            SubscriptionPlan.name == payload.name,
        )
    )
    if existing:
        raise AppError(409, "PLAN_NAME_EXISTS", "Plan name in use", "A subscription plan with this name already exists.")

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
    db.flush()
    db.commit()
    return SubscriptionPlanOut.model_validate(plan)


# ── Subscriptions ─────────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> SubscriptionOut | None:
    subscription = db.scalar(
        select(Subscription).where(Subscription.membership_id == actor.membership.id)
    )
    if not subscription:
        return None
    return SubscriptionOut.model_validate(subscription)


@router.post("/subscription", response_model=SubscriptionOut)
def create_subscription(
    payload: SubscriptionIn,
    actor: Actor = Depends(require_permission("subscriptions.create")),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    # Verify plan exists
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if not plan or not plan.is_active:
        raise AppError(404, "SUBSCRIPTION_PLAN_NOT_FOUND", "Plan not found", "Subscription plan was not found or is not active.")

    # Check if already has active subscription
    existing = db.scalar(
        select(Subscription).where(
            Subscription.membership_id == actor.membership.id,
            Subscription.status.in_(["ACTIVE", "TRIAL"]),
        )
    )
    if existing:
        raise AppError(409, "SUBSCRIPTION_ALREADY_ACTIVE", "Subscription already active", "This membership already has an active subscription.")

    subscription = Subscription(
        restaurant_id=actor.restaurant_id,
        membership_id=actor.membership.id,
        plan_id=payload.plan_id,
        status=payload.status,
    )
    db.add(subscription)
    db.flush()
    db.commit()
    return SubscriptionOut.model_validate(subscription)


# ── SubscriptionBillingInfo ───────────────────────────────────────────────

@router.get("/billing", response_model=SubscriptionBillingInfoOut)
def get_billing_info(
    actor: Actor = Depends(require_permission("subscriptions.read")),
    db: Session = Depends(get_db),
) -> SubscriptionBillingInfoOut | None:
    billing = db.scalar(
        select(SubscriptionBillingInfo).where(
            SubscriptionBillingInfo.subscription_id == actor.membership.id
        )
    )
    if not billing:
        return None
    return SubscriptionBillingInfoOut.model_validate(billing)


@router.post("/billing", response_model=SubscriptionBillingInfoOut)
def create_billing_info(
    payload: SubscriptionBillingInfoIn,
    actor: Actor = Depends(require_permission("subscriptions.manage")),
    db: Session = Depends(get_db),
) -> SubscriptionBillingInfoOut:
    # Verify subscription exists
    subscription = db.get(Subscription, payload.subscription_id)
    if not subscription or subscription.restaurant_id != actor.restaurant_id:
        raise AppError(404, "SUBSCRIPTION_NOT_FOUND", "Not found", "Subscription was not found.")

    billing = SubscriptionBillingInfo(
        subscription_id=payload.subscription_id,
        amount_minor=payload.amount_minor,
        currency_code=payload.currency_code,
        billing_date=payload.billing_date,
        status=payload.status,
    )
    db.add(billing)
    db.flush()
    db.commit()
    return SubscriptionBillingInfoOut.model_validate(billing)