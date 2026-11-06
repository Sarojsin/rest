"""Schemas for restaurant staff membership administration (PA-07)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

StaffRole = Literal["manager", "waiter", "kitchen", "cashier"]


class MembershipInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    role: StaffRole
    name: str = Field(default="", max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    branch_id: UUID | None = Field(
        default=None,
        description="Optional branch to scope this membership to. Owner invitations do not use this field.",
    )


class MembershipOut(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: str
    status: str
    created_at: datetime
    branch_ids: list[UUID] = Field(default_factory=list)


class MembershipInviteOut(MembershipOut):
    invitation_token: str
    invitation_expires_at: datetime


class SeatUsageOut(BaseModel):
    current: int
    limit: int | None
    remaining: int | None


class MembershipListOut(BaseModel):
    items: list[MembershipOut]
    seats: dict[str, SeatUsageOut] | None = None
