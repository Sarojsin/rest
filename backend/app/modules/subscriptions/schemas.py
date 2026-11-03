from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── SubscriptionPlan ────────────────────────────────────────────────────────

class SubscriptionPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    name: str
    description: str | None
    price_minor: int
    billing_interval: str  # MONTHLY, QUARTERLY, ANNUAL
    trial_days: int
    features: str  # JSON string
    is_active: bool


class SubscriptionPlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    price_minor: int = Field(gt=0)
    billing_interval: str = "MONTHLY"
    trial_days: int = 0
    features: str = ""  # JSON string


# ── Subscription ────────────────────────────────────────────────────────────

class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_id: UUID
    plan_id: UUID
    status: str  # TRIAL, ACTIVE, PAST_DUE, CANCELLED
    started_at: datetime
    billing_cycle_end: datetime
    cancel_at_period_end: bool
    canceled_at: datetime | None


class SubscriptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    status: str = "TRIAL"
    cancel_at_period_end: bool = False


# ── SubscriptionBillingInfo ────────────────────────────────────────────────

class SubscriptionBillingInfoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    amount_minor: int
    currency_code: str
    billing_date: datetime
    status: str  # SCHEDULED, PAID, FAILED


class SubscriptionBillingInfoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_id: UUID
    amount_minor: int
    currency_code: str = "USD"
    billing_date: datetime
    status: str = "SCHEDULED"