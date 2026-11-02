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


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut
