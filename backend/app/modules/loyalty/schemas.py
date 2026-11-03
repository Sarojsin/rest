from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── LoyaltyAccount ──────────────────────────────────────────────────────────

class LoyaltyAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_id: UUID
    points_balance: int
    total_earned: int
    total_redeemed: int
    lifetime_spend_minor: int
    tier: str
    last_earned_at: datetime | None
    last_redeemed_at: datetime | None


class LoyaltyAccountIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID
    points_balance: int = 0
    tier: str = "STANDARD"


# ── LoyaltyTransaction ──────────────────────────────────────────────────────

class LoyaltyTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_id: UUID
    type: str  # EARN, REDEEM
    points: int
    reason: str
    reference_id: UUID | None
    created_at: datetime


class LoyaltyTransactionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID
    type: str  # EARN, REDEEM
    points: int
    reason: str
    reference_id: UUID | None


# ── Coupon ──────────────────────────────────────────────────────────────────

class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    discount_type: str  # PERCENT, FIXED
    discount_value: int
    minimum_spend_minor: int
    maximum_redeem_count: int | None
    current_redeem_count: int
    is_active: bool
    valid_from: datetime
    valid_until: datetime | None
    usage_limit_per_customer: int | None


class CouponIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    discount_type: str = "PERCENT"
    discount_value: int = Field(gt=0)
    minimum_spend_minor: int = Field(ge=0, default=0)
    maximum_redeem_count: int | None = None
    valid_from: datetime
    valid_until: datetime | None = None
    usage_limit_per_customer: int | None = None


# ── CouponRedemption ──────────────────────────────────────────────────────

class CouponRedemptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coupon_id: UUID
    membership_id: UUID
    order_id: UUID
    discount_amount_minor: int
    redeemed_at: datetime


class CouponRedemptionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coupon_id: UUID
    membership_id: UUID
    order_id: UUID
    discount_amount_minor: int