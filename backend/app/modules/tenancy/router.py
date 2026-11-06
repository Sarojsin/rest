from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, text
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


# ---------------------------------------------------------------------------
# Onboarding status (Plan 11)
# ---------------------------------------------------------------------------

STAGE_ORDER = [
    "registered",
    "owner_invited",
    "owner_activated",
    "profile_complete",
    "branches",
    "tables_configured",
    "menu_configured",
    "staff_invited",
    "payments_configured",
    "operational",
]

STAGE_LABELS = {
    "registered": "Registered",
    "owner_invited": "Owner Invited",
    "owner_activated": "Owner Activated",
    "profile_complete": "Profile Complete",
    "branches": "Branches",
    "tables_configured": "Tables Configured",
    "menu_configured": "Menu Configured",
    "staff_invited": "Staff Invited",
    "payments_configured": "Payments Configured",
    "operational": "Operational",
}

STAGE_STEPS = [
    {"key": "registered", "label": "Accept invitation"},
    {"key": "owner_invited", "label": "Owner account setup"},
    {"key": "owner_activated", "label": "Owner account activated"},
    {"key": "profile_complete", "label": "Complete restaurant profile"},
    {"key": "branches", "label": "Configure branches"},
    {"key": "tables_configured", "label": "Configure tables & QR codes"},
    {"key": "menu_configured", "label": "Configure menu"},
    {"key": "staff_invited", "label": "Invite employees"},
    {"key": "payments_configured", "label": "Configure payments"},
    {"key": "operational", "label": "Start operations"},
]


def _compute_stage(db: Session, restaurant_id: UUID) -> str:
    """Compute the onboarding stage from existing data.

    Stage advances only when the required data is present. This is computed
    (not manual) so the checklist always reflects reality.

    Uses raw SQL instead of cross-module ORM imports to respect the module
    boundary (the only sanctioned edge is platform -> tenancy via
    services.platform_directory).
    """
    # Check operational: at least one order exists
    has_order = db.scalar(
        text(
            "SELECT 1 FROM orders WHERE restaurant_id = :rid LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    if has_order:
        return "operational"

    # Check payments: at least one payment method configured
    has_payment = db.scalar(
        text(
            "SELECT 1 FROM payment_methods WHERE restaurant_id = :rid LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    if has_payment:
        return "payments_configured"

    # Check staff: at least one non-owner membership
    has_staff = db.scalar(
        text(
            "SELECT 1 FROM restaurant_memberships "
            "WHERE restaurant_id = :rid AND role <> 'owner' "
            "AND status <> 'REMOVED' LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    if has_staff:
        return "staff_invited"

    # Check menu: at least one category AND one item
    has_category = db.scalar(
        text(
            "SELECT 1 FROM menu_categories WHERE restaurant_id = :rid LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    has_item = db.scalar(
        text(
            "SELECT 1 FROM menu_items WHERE restaurant_id = :rid LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    if has_category and has_item:
        return "menu_configured"

    # Check tables: at least one table
    has_table = db.scalar(
        text(
            "SELECT 1 FROM restaurant_tables WHERE branch_id = :rid LIMIT 1"
        ),
        {"rid": restaurant_id},
    )
    if has_table:
        return "tables_configured"

    # Check branches: at least one branch
    has_branch = db.scalar(
        text("SELECT 1 FROM branches WHERE restaurant_id = :rid LIMIT 1"),
        {"rid": restaurant_id},
    )
    if has_branch:
        return "branches"

    # Check profile: settings have branding (logo or accent color)
    settings = db.get(RestaurantSettings, restaurant_id)
    if settings and (
        settings.brand_logo_url
        or settings.brand_accent_hex
    ):
        return "profile_complete"

    return "registered"


@router.get("/onboarding/status", response_model=dict)
def onboarding_status(
    actor: Actor = Depends(require_permission("staff.manage")),
    db: Session = Depends(get_db),
) -> dict:
    """Get the current onboarding stage and progress for the tenant.

    The stage is computed from existing data (computed, not manual), so it
    always reflects what has actually been configured.
    """
    restaurant_id = actor.restaurant_id
    settings = db.get(RestaurantSettings, restaurant_id)
    stored_stage = settings.onboarding_stage if settings else "registered"
    computed_stage = _compute_stage(db, restaurant_id)

    # Determine completed steps: all steps before the computed stage
    computed_index = STAGE_ORDER.index(computed_stage)
    completed_steps = STAGE_ORDER[:computed_index]
    remaining_steps = STAGE_ORDER[computed_index:]

    percent = int((len(completed_steps) / len(STAGE_ORDER)) * 100)

    return {
        "restaurant_id": str(restaurant_id),
        "stored_stage": stored_stage,
        "computed_stage": computed_stage,
        "stage_label": STAGE_LABELS.get(computed_stage, computed_stage),
        "current_step_index": computed_index,
        "total_steps": len(STAGE_ORDER),
        "percent_complete": percent,
        "completed_steps": completed_steps,
        "remaining_steps": remaining_steps,
        "steps": [
            {
                "key": s["key"],
                "label": s["label"],
                "completed": s["key"] in completed_steps,
            }
            for s in STAGE_STEPS
        ],
    }
