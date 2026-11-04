"""Pydantic models for the platform auth surface (PA-0.5)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginChallengeOut(BaseModel):
    mfa_required: bool = True
    enrollment_required: bool
    ticket: str
    expires_in: int


class MfaEnrollStartRequest(BaseModel):
    ticket: str


class MfaEnrollStartOut(BaseModel):
    secret: str
    provisioning_uri: str
    issuer: str


class MfaCodeRequest(BaseModel):
    ticket: str
    code: str = Field(min_length=1, max_length=32)


class StepUpRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=1, max_length=32)


class StepUpOut(BaseModel):
    expires_in: int
    step_up_expires_in: int


class PlatformAdminOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    mfa_enabled: bool


class PlatformMeOut(PlatformAdminOut):
    permissions: list[str]


class AuthSuccessOut(BaseModel):
    admin: PlatformAdminOut
    expires_in: int
    # Returned exactly once at enrollment. Never stored in plaintext.
    recovery_codes: list[str] | None = None


class PlatformSessionOut(BaseModel):
    family_id: UUID
    created_at: datetime
    expires_at: datetime
    ip: str | None = None
    user_agent: str | None = None
    current: bool = False


class PlatformSessionsOut(BaseModel):
    sessions: list[PlatformSessionOut]
