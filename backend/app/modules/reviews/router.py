from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.reviews.models import Review, ReviewResponse
from app.modules.reviews.schemas import (
    ReviewIn,
    ReviewOut,
    ReviewResponseIn,
    ReviewsSummaryOut,
)
from app.shared.errors import AppError

router = APIRouter(tags=["reviews"])


# ── Summary (declared before /{review_id} to avoid path capture) ────────────

@router.get("/summary", response_model=ReviewsSummaryOut)
def get_reviews_summary(
    actor: Actor = Depends(require_permission("reviews.read")),
    db: Session = Depends(get_db),
) -> ReviewsSummaryOut:
    reviews = db.scalars(
        select(Review).where(Review.restaurant_id == actor.restaurant_id)
    ).all()

    total = len(reviews)
    if total == 0:
        return ReviewsSummaryOut(
            average_rating=0.0, total_reviews=0, rating_distribution={}
        )

    distribution: dict[int, int] = {}
    for review in reviews:
        distribution[review.rating] = distribution.get(review.rating, 0) + 1

    return ReviewsSummaryOut(
        average_rating=round(sum(r.rating for r in reviews) / total, 2),
        total_reviews=total,
        rating_distribution=distribution,
    )


# ── Reviews ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ReviewOut])
def list_reviews(
    status: str | None = None,
    actor: Actor = Depends(require_permission("reviews.read")),
    db: Session = Depends(get_db),
) -> list[ReviewOut]:
    stmt = select(Review).where(Review.restaurant_id == actor.restaurant_id)
    if status:
        stmt = stmt.where(Review.status == status)
    reviews = db.scalars(stmt.order_by(Review.created_at.desc())).all()
    return [ReviewOut.model_validate(r) for r in reviews]


@router.post("", response_model=ReviewOut, status_code=201)
def create_review(
    payload: ReviewIn,
    actor: Actor = Depends(require_permission("reviews.create")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    review = Review(
        restaurant_id=actor.restaurant_id,
        membership_id=actor.membership.id,
        rating=payload.rating,
        title=payload.title,
        content=payload.content,
        images=payload.images,
        status="APPROVED",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: UUID,
    actor: Actor = Depends(require_permission("reviews.read")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    review = db.get(Review, review_id)
    if review is None or review.restaurant_id != actor.restaurant_id:
        raise AppError(404, "REVIEW_NOT_FOUND", "Not found", "Review was not found.")
    return ReviewOut.model_validate(review)


@router.post("/{review_id}/respond", response_model=ReviewOut)
def respond_to_review(
    review_id: UUID,
    payload: ReviewResponseIn,
    actor: Actor = Depends(require_permission("reviews.respond")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    review = db.get(Review, review_id)
    if review is None or review.restaurant_id != actor.restaurant_id:
        raise AppError(404, "REVIEW_NOT_FOUND", "Not found", "Review was not found.")

    now = datetime.now(UTC)
    review.response_text = payload.response_text
    review.responded_at = now
    db.add(
        ReviewResponse(
            restaurant_id=actor.restaurant_id,
            review_id=review.id,
            membership_id=actor.membership.id,
            response_text=payload.response_text,
            responded_at=now,
        )
    )
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@router.patch("/{review_id}/status", response_model=ReviewOut)
def set_review_status(
    review_id: UUID,
    status: str,
    actor: Actor = Depends(require_permission("reviews.respond")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    if status not in {"PENDING", "APPROVED", "REJECTED"}:
        raise AppError(
            422, "INVALID_STATUS", "Invalid status",
            "Status must be PENDING, APPROVED, or REJECTED.",
        )
    review = db.get(Review, review_id)
    if review is None or review.restaurant_id != actor.restaurant_id:
        raise AppError(404, "REVIEW_NOT_FOUND", "Not found", "Review was not found.")
    review.status = status
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)
