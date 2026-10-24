from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor
from app.db.session import get_db
from app.models.identity import Restaurant, RestaurantSettings
from app.schemas.staff import RestaurantOut

router = APIRouter(tags=["restaurant"])


@router.get("/restaurant", response_model=RestaurantOut)
def get_restaurant(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)) -> RestaurantOut:
    restaurant = db.get(Restaurant, actor.restaurant_id)
    settings = db.get(RestaurantSettings, actor.restaurant_id)
    if restaurant is None:
        from app.core.errors import AppError

        raise AppError(404, "RESTAURANT_NOT_FOUND", "Not found", "Restaurant was not found.")
    return RestaurantOut(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        timezone=restaurant.timezone,
        currency_code=restaurant.currency_code,
        tax_rate_bps=settings.tax_rate_bps if settings else 1000,
        qr_ordering_enabled=bool(settings.qr_ordering_enabled) if settings else True,
    )
