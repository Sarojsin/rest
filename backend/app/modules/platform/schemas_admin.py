"""Request schemas for the PA-1 platform console (plan 05).

Responses are assembled as dictionaries by the routers because they join data
across the platform and tenant directories; request validation lives here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReasonConfirmRequest(ReasonRequest):
    confirm: str = Field(min_length=1, max_length=255)


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    owner_email: EmailStr
    owner_display_name: str = Field(default="", max_length=120)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=40)
    legal_name: str | None = Field(default=None, max_length=200)
    timezone: str = Field(default="Asia/Kathmandu", max_length=64)
    currency_code: str = Field(default="NPR", min_length=3, max_length=3)
    plan_code: str = Field(min_length=1, max_length=40)
    trial_days: int = Field(default=14, ge=0, le=365)
    source: str | None = Field(default=None, max_length=80)
    reason: str = Field(min_length=1, max_length=1000)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=40)
    legal_name: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    reason: str = Field(min_length=1, max_length=1000)


class PlanCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_monthly_minor: int = Field(ge=0)
    price_annual_minor: int = Field(default=0, ge=0)
    currency_code: str = Field(default="NPR", min_length=3, max_length=3)
    trial_days: int = Field(default=0, ge=0, le=365)
    entitlements: dict[str, Any] | None = None
    is_public: bool = True
    sort_order: int = 0
    reason: str = Field(min_length=1, max_length=1000)


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_monthly_minor: int | None = Field(default=None, ge=0)
    price_annual_minor: int | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    trial_days: int | None = Field(default=None, ge=0, le=365)
    entitlements: dict[str, Any] | None = None
    is_public: bool | None = None
    sort_order: int | None = None
    reason: str = Field(min_length=1, max_length=1000)


class SubscriptionCreateRequest(BaseModel):
    restaurant_id: str
    plan_code: str = Field(min_length=1, max_length=40)
    trial_days: int | None = Field(default=None, ge=0, le=365)
    reason: str = Field(min_length=1, max_length=1000)


class SubscriptionUpdateRequest(BaseModel):
    plan_code: str | None = Field(default=None, max_length=40)
    cancel_at_period_end: bool | None = None
    current_period_end: datetime | None = None
    grace_ends_at: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)


class ExtendTrialRequest(BaseModel):
    days: int = Field(ge=1, le=365)
    reason: str = Field(min_length=1, max_length=1000)


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = True
    reason: str = Field(min_length=1, max_length=1000)


class SubscriptionChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_plan_code: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=1000)
    confirm: str = Field(min_length=1, max_length=255)


class TenantCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)
    confirm: str = Field(min_length=1, max_length=255)
    effective_date: str | None = Field(
        default=None, max_length=32, description="Optional cancellation effective date (ISO format). If omitted, cancellation is immediate."
    )


class TenantAnonymizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)
    confirm: str = Field(min_length=1, max_length=255)


class ExportJobOut(BaseModel):
    job_id: str
    status: str
    created_at: str
    expires_at: str | None = None
    download_url: str | None = None


class InvoiceLineRequest(BaseModel):
    kind: str = Field(default="PLAN", max_length=24)
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1, le=100000)
    unit_amount_minor: int = Field(ge=0)


class InvoiceCreateRequest(BaseModel):
    restaurant_id: str
    subscription_id: str | None = None
    due_at: datetime
    currency_code: str = Field(default="NPR", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[InvoiceLineRequest] = Field(min_length=1, max_length=100)
    discount_minor: int = Field(default=0, ge=0)
    reason: str = Field(min_length=1, max_length=1000)


class PaymentRequest(BaseModel):
    method: str = Field(default="BANK_TRANSFER", max_length=32)
    reference: str = Field(min_length=1, max_length=120)
    provider_reference: str | None = Field(default=None, max_length=120)
    evidence_type: str | None = Field(default=None, max_length=24)
    evidence_ref: str | None = Field(default=None, max_length=500)
    paid_at: datetime | None = None
    exception_reason: str | None = Field(default=None, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)


class PaymentVoidRequest(ReasonConfirmRequest):
    pass


class RefundRequest(BaseModel):
    amount_minor: int = Field(ge=1)
    reason_code: str = Field(default="OTHER", max_length=32)
    reason: str = Field(min_length=1, max_length=1000)
    original_reference: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=255)
    processed_outside_platform: bool = True
    evidence_ref: str | None = Field(default=None, max_length=500)
    evidence_type: str | None = Field(default=None, max_length=24)


class RefundCompleteRequest(BaseModel):
    external_reference: str = Field(min_length=1, max_length=120)
    completed_at: datetime | None = None
    destination: str | None = Field(default=None, max_length=255)
    processed_outside_platform: bool = True
    note: str | None = Field(default=None, max_length=1000)
    reason: str = Field(default="refund completed", max_length=1000)


class PlatformUserCreateRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=1000)


class PlatformUserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    reason: str = Field(min_length=1, max_length=1000)


class SettingsUpdateRequest(BaseModel):
    changes: dict[str, Any] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class InviteAcceptRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)


# ---------------------------------------------------------------------------
# Trial lifecycle schemas (Plan 03)
# ---------------------------------------------------------------------------


class ExpireTrialRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class TrialStatusOut(BaseModel):
    subscription_id: UUID
    restaurant_id: UUID
    status: str
    trial_ends_at: datetime | None
    days_remaining: int
    is_expiring_soon: bool
    trial_extension_count: int
    trial_extension_total_days: int
    can_extend: bool


class TrialExpirationOut(BaseModel):
    expired_count: int
    expired_subscriptions: list[dict] = []


class TrialExpiringOut(BaseModel):
    expiring_count: int
    trials: list[dict] = []


# ---------------------------------------------------------------------------
# Plan version schemas (Plan 01)
# ---------------------------------------------------------------------------


class PlanVersionCreateRequest(BaseModel):
    """Create a new version of an existing plan.

    The new version starts as a draft (is_active=False). Only one version
    can be active per plan at a time. Publishing a new version automatically
    deactivates the previous active version.
    """
    price_monthly_minor: int = Field(ge=0)
    price_annual_minor: int = Field(default=0, ge=0)
    currency_code: str = Field(default="NPR", min_length=3, max_length=3)
    trial_days: int = Field(default=0, ge=0, le=365)
    effective_from: datetime | None = Field(default=None)
    reason: str = Field(min_length=1, max_length=1000)


class PlanVersionUpdateRequest(BaseModel):
    """Update a draft plan version. Only the active=False version can be edited."""
    price_monthly_minor: int | None = Field(default=None, ge=0)
    price_annual_minor: int | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    trial_days: int | None = Field(default=None, ge=0, le=365)
    effective_from: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)


class PlanVersionPublishRequest(BaseModel):
    """Publish a draft version, making it the active version for new subscriptions."""
    reason: str = Field(min_length=1, max_length=1000)


class PlanFeatureRequest(BaseModel):
    """Add or update a feature on a plan version."""
    feature_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    enabled: bool = True
    reason: str = Field(min_length=1, max_length=1000)


class PlanLimitRequest(BaseModel):
    """Add or update a usage limit on a plan version."""
    limit_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    limit_value: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)


class PlanVersionOut(BaseModel):
    """Response for a plan version with its features and limits."""
    id: UUID
    plan_id: UUID
    version: int
    price_monthly_minor: int
    price_annual_minor: int
    currency_code: str
    trial_days: int
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool
    features: dict[str, bool] = {}
    limits: dict[str, int] = {}
    created_at: datetime
    updated_at: datetime


class PlanWithVersionsOut(BaseModel):
    """A plan with all its versions."""
    id: UUID
    code: str
    name: str
    description: str | None
    status: str
    is_public: bool
    sort_order: int
    versions: list[PlanVersionOut] = []
    active_version: PlanVersionOut | None = None


# ---------------------------------------------------------------------------
# Onboarding wizard schemas (Plan 08)
# ---------------------------------------------------------------------------


class RestaurantDetailsRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    legal_name: str | None = Field(default=None, max_length=200)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    contact_email: EmailStr
    contact_phone: str = Field(min_length=1, max_length=40)
    country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    province: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    address: str = Field(min_length=1, max_length=500)
    website: str | None = Field(default=None, max_length=255)
    timezone: str = Field(default="Asia/Kathmandu", max_length=64)
    currency_code: str = Field(default="NPR", min_length=3, max_length=3)


class OwnerCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)


class BranchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9-]+$")
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = Field(default=None, max_length=255)
    opening_hours: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="Asia/Kathmandu", max_length=64)


class SubscriptionOnboardingRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)
    trial_days: int = Field(default=14, ge=0, le=365)
    billing_interval: str = Field(default="MONTHLY", max_length=20)


class OnboardingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restaurant: RestaurantDetailsRequest
    owner: OwnerCreateRequest
    subscription: SubscriptionOnboardingRequest
    branches: list[BranchCreateRequest] = Field(min_length=1, max_length=10)
    reason: str = Field(min_length=1, max_length=1000)
    confirm: str = Field(min_length=1, max_length=255)


# ---------------------------------------------------------------------------
# Support ticket schemas (Plan 10)
# ---------------------------------------------------------------------------


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    restaurant_id: str
    subject: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: str = Field(default="medium", max_length=16)


class SupportTicketUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=16)
    assigned_to_admin_id: str | None = None


class SupportTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    subject: str
    description: str | None
    status: str
    priority: str
    assigned_to_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

