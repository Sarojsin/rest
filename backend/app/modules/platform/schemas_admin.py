"""Request schemas for the PA-1 platform console (plan 05).

Responses are assembled as dictionaries by the routers because they join data
across the platform and tenant directories; request validation lives here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


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
