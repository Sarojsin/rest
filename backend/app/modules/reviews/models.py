from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string of image paths/URLs
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )  # PENDING, APPROVED, REJECTED
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="reviews")  # noqa: F821


class ReviewResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_responses"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False, index=True
    )
    review_id: Mapped[UUID] = mapped_column(ForeignKey("reviews.id"), nullable=False)
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
