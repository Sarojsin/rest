from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor, get_tenant_id, set_tenant_context
from app.db.session import get_db
from app.modules.tenancy.models import Restaurant, RestaurantSettings
from app.modules.tenancy.schemas import RestaurantOut

router = APIRouter(tags=["restaurant"])


@router.get("/restaurant", response_model=RestaurantOut)
def get_restaurant(
    actor: Actor = Depends(get_actor), db: Session = Depends(get_db)
) -> RestaurantOut:
    restaurant = db.get(Restaurant, actor.restaurant_id)
    settings = db.get(RestaurantSettings, actor.restaurant_id)
    if restaurant is None:
        from app.shared.errors import AppError

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


@router.get("/tenant", response_model=dict)
def get_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    set_tenant_context(request)
    tid = get_tenant_id()
    if tid is None:
        return {"tenant_id": None, "detail": "No x-tenant-id header provided"}
    # Fetch the restaurant associated with this tenant_id
    from app.modules.tenancy.models import Restaurant as R
    restaurant = db.get(R, UUID(tid))
    if restaurant is None:
        return {
        "tenant_id": tid,
        "name": "Unknown",
        "detail": "Restaurant not found for this tenant_id",
    }
    settings = db.get(RestaurantSettings, restaurant.id)
    return {
        "tenant_id": tid,
        "name": restaurant.name,
        "slug": restaurant.slug,
        "currency_code": restaurant.currency_code,
        "qr_ordering_enabled": bool(settings.qr_ordering_enabled) if settings else True,
    }