"""Notification / FCM transport schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.schemas import ORMModel

Platform = Literal["android", "ios", "web"]


class DeviceTokenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=500)
    platform: Platform


class DeviceTokenOut(ORMModel):
    id: UUID
    user_id: UUID
    restaurant_id: UUID
    token: str
    platform: Platform
    updated_at: datetime


class DeviceTokenListOut(BaseModel):
    items: list[DeviceTokenOut]
    total: int


class FCMMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=500)
    data: dict[str, str] | None = None
    # When set, send only to devices of this restaurant; otherwise broadcast
    # to every registered device token.
    restaurant_id: UUID | None = None


class FCMMessageOut(BaseModel):
    sent: int
    failed: int
    message_ids: list[str]
