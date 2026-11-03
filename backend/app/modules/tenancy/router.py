from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor, get_tenant_id, require_permission, set_tenant_context
from app.db.session import get_db
from app.modules.tenancy.models import Restaurant, RestaurantSettings
from app.modules.tenancy.schemas import (
    CustomerHostOut,
    CustomerHostUpdate,
    RestaurantOut,
)
from app.modules.tenancy.services.hostname import (
    customer_hostname,
    validate_subdomain,
)
from app.shared.errors import AppError

router = APIRouter(tags=["restaurant"])


def _settings_or_default(db: Session, restaurant: Restaurant) -> RestaurantSettings:
    settings_row = db.get(RestaurantSettings, restaurant.id)
    if settings_row is None:
        # Structural safety net: bootstrap always creates settings, but a
        # settings-less restaurant must still render sane defaults.
        settings_row = RestaurantSettings(restaurant_id=restaurant.id)
        db.add(settings_row)
        db.flush()
    return settings_row


def _customer_host_out(restaurant: Restaurant, settings_row: RestaurantSettings) -> CustomerHostOut:
    return CustomerHostOut(
        customer_subdomain=settings_row.customer_subdomain or "",
        custom_domain=settings_row.custom_domain,
        customer_hostname=customer_hostname(settings_row, restaurant),
        brand_logo_url=settings_row.brand_logo_url or "",
        brand_accent_hex=settings_row.brand_accent_hex or "",
    )


@router.get("/restaurant", response_model=RestaurantOut)
def get_restaurant(
    actor: Actor = Depends(get_actor), db: Session = Depends(get_db)
) -> RestaurantOut:
    restaurant = db.get(Restaurant, actor.restaurant_id)
    settings = db.get(RestaurantSettings, actor.restaurant_id)
    if restaurant is None:
        raise AppError(404, "RESTAURANT_NOT_FOUND", "Not found", "Restaurant was not found.")
    return RestaurantOut(
        id=restaurant.id,
        name=restaurant.name,
        slug=restaurant.slug,
        timezone=restaurant.timezone,
        currency_code=restaurant.currency_code,
        tax_rate_bps=settings.tax_rate_bps if settings else 1000,
        qr_ordering_enabled=bool(settings.qr_ordering_enabled) if settings else True,
        customer_hostname=customer_hostname(settings, restaurant) if settings else "",
    )


@router.get("/restaurant/customer-host", response_model=CustomerHostOut)
def get_customer_host(
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> CustomerHostOut:
    restaurant = db.get(Restaurant, actor.restaurant_id)
    if restaurant is None:
        raise AppError(404, "RESTAURANT_NOT_FOUND", "Not found", "Restaurant was not found.")
    settings_row = _settings_or_default(db, restaurant)
    return _customer_host_out(restaurant, settings_row)


@router.put("/restaurant/customer-host", response_model=CustomerHostOut)
def update_customer_host(
    payload: CustomerHostUpdate,
    actor: Actor = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> CustomerHostOut:
    restaurant = db.get(Restaurant, actor.restaurant_id)
    if restaurant is None:
        raise AppError(404, "RESTAURANT_NOT_FOUND", "Not found", "Restaurant was not found.")
    settings_row = _settings_or_default(db, restaurant)

    # D5: the subdomain is chosen once at launch and then locked.
    if payload.customer_subdomain is not None:
        if settings_row.customer_subdomain:
            raise AppError(
                409,
                "SUBDOMAIN_LOCKED",
                "Conflict",
                "The customer subdomain is permanent and cannot be changed.",
            )
        label = validate_subdomain(payload.customer_subdomain)
        taken = db.scalar(
            select(RestaurantSettings.customer_subdomain).where(
                RestaurantSettings.customer_subdomain == label,
                RestaurantSettings.restaurant_id != restaurant.id,
            )
        )
        if taken is not None:
            raise AppError(
                409,
                "SUBDOMAIN_TAKEN",
                "Taken",
                "Another restaurant already uses this subdomain.",
            )
        settings_row.customer_subdomain = label

    if "custom_domain" in payload.model_fields_set:
        normalized = (payload.custom_domain or "").strip().lower()
        settings_row.custom_domain = normalized or None
    if "brand_logo_url" in payload.model_fields_set:
        settings_row.brand_logo_url = (payload.brand_logo_url or "").strip()
    if "brand_accent_hex" in payload.model_fields_set:
        settings_row.brand_accent_hex = (payload.brand_accent_hex or "").strip()

    db.commit()
    db.refresh(settings_row)
    return _customer_host_out(restaurant, settings_row)


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
