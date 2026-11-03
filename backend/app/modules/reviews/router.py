from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.reviews.models import Review, ReviewResponse
from app.modules.reviews.schemas import ReviewOut, ReviewIn, ReviewResponseIn, ReviewsSummaryOut
from app.shared.errors import AppError

router = APIRouter(tags=["reviews"])


# ── Reviews ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ReviewOut])
def list_reviews(
    actor: Actor = Depends(require_permission("reviews.read")),
    db: Session = Depends(get_db),
) -> list[ReviewOut]:
    reviews = db.scalars(
        select(Review).where(Review.restaurant_id == actor.restaurant_id)
    ).all()
    return [ReviewOut.model_validate(r) for r in reviews]


@router.post("/", response_model=ReviewOut)
def create_review(
    payload: ReviewIn,
    actor: Actor = Depends(require_permission("reviews.create")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    # Verify restaurant exists
    from app.modules.tenancy.models import Restaurant
    restaurant = db.get(Restaurant, actor.restaurant_id)
    if not restaurant:
        raise AppError(404, "RESTAURANT_NOT_FOUND", "Not found", "Restaurant was not found.")

    review = Review(
        restaurant_id=actor.restaurant_id,
        membership_id=actor.membership.id if actor.membership else None,
        rating=payload.rating,
        title=payload.title,
        content=payload.content,
        images=payload.images,
    )
    db.add(review)
    db.flush()
    db.commit()
    return ReviewOut.model_validate(review)


@router.post("/{review_id}/respond", response_model=ReviewOut)
def respond_to_review(
    review_id: UUID,
    payload: ReviewResponseIn,
    actor: Actor = Depends(require_permission("reviews.respond")),
    db: Session = Depends(get_db),
) -> ReviewOut:
    review = db.get(Review, review_id)
    if not review or review.restaurant_id != actor.restaurant_id:
        raise AppError(404, "REVIEW_NOT_FOUND", "Not found", "Review was not found.")

    review.response_text = payload.response_text
    review.responded_at = datetime.now()
    review.status = "APPROVED"
    db.add(review)
    db.flush()
    db.commit()
    return ReviewOut.model_validate(review)


# ── ReviewsSummary ────────────────────────────────────────────────────────

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
            average_rating=0.0,
            total_reviews=0,
            rating_distribution={},
        )

    # Calculate average
    avg_rating = sum(r.rating for r in reviews) / total

    # Calculate distribution
    distribution: dict = {}
    for r in reviews:
        r_int = int(r.rating)
        distribution[r_int] = distribution.get(r_int, 0) + 1

    return ReviewsSummaryOut(
        average_rating=round(avg_rating, 2),
        total_reviews=total,
        rating_distribution=distribution,
    )