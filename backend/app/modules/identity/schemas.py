from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class MembershipOut(BaseModel):
    id: UUID
    restaurant_id: UUID
    restaurant_name: str
    role: str
    permissions: list[str]


class MeOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    membership: MembershipOut
    memberships: list[MembershipOut] = []
    active_branch_id: UUID | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MeOut


class MFAChallengeResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str  # Short-lived token for MFA challenge completion
    user_id: UUID
    membership_id: UUID
    restaurant_id: UUID
