from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Review ──────────────────────────────────────────────────────────────────

class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    restaurant_id: UUID
    membership_id: UUID | None
    rating: int  # 1-5
    title: str | None
    content: str | None
    images: str | None  # JSON string
    status: str
    created_at: datetime
    responded_at: datetime | None
    response_text: str | None


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5)
    title: str | None = None
    content: str | None = None
    images: str | None = None


class ReviewResponseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


# ── ReviewsSummary ──────────────────────────────────────────────────────────

class ReviewsSummaryOut(BaseModel):
    average_rating: float
    total_reviews: int
    rating_distribution: dict  # {rating: count}