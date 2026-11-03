from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint("restaurant_id", "membership_id", "rating", name="uq_reviews_restaurant_rating"),
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # JSON string of image paths/URLs
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )  # PENDING, APPROVED, REJECTED
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="reviews")


class ReviewResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_responses"

    review_id: Mapped[UUID] = mapped_column(
        ForeignKey("reviews.id"), nullable=False
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurant_memberships.id"), nullable=True
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(nullable=False)