"""Customer subdomain service (plan 07 M7).

Every restaurant serves its customer QR surface on a subdomain of the platform
apex (D5: chosen at launch, locked for the life of the tenant), with an
optional fully custom domain for verified tenants.

The web app must never redirect a customer across tenants: every public QR
endpoint cross-checks the request Host against the restaurant's configured
hostname and fails closed with 403 instead.
"""

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.tenancy.models import Restaurant, RestaurantSettings
from app.shared.errors import AppError

_DEV_MODE = settings.app_env != "production"

# RFC-1035 label: 3-63 chars, starts/ends alphanumeric, inner hyphens allowed.
SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$")

# Labels reserved for the platform apex and its own surfaces (plan 07).
RESERVED_SUBDOMAINS = {
    "www",
    "api",
    "app",
    "admin",
    "staff",
    "platform",
    "public",
    "mail",
    "smtp",
    "ftp",
    "static",
    "cdn",
    "assets",
    "media",
    "docs",
    "help",
    "status",
    "blog",
    "billing",
    "pay",
    "auth",
    "login",
    "sso",
    "demo",
}

# Hosts that never carry tenant routing: local development and the bare test
# client. The bare apex itself is also fine (dev single-tenant convenience).
_DEV_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "testserver"}


def validate_subdomain(raw: str) -> str:
    """Normalize a requested subdomain label; raise on invalid or reserved."""
    label = raw.strip().lower()
    if not label:
        raise AppError(
            422, "INVALID_SUBDOMAIN", "Invalid input", "Subdomain is required."
        )
    if not SUBDOMAIN_RE.match(label):
        raise AppError(
            422,
            "INVALID_SUBDOMAIN",
            "Invalid input",
            "Use 3-63 lowercase letters, digits or hyphens (no leading/trailing hyphen).",
        )
    if label in RESERVED_SUBDOMAINS:
        raise AppError(
            409, "RESERVED_SUBDOMAIN", "Taken", "This subdomain is reserved by the platform."
        )
    return label


def _slug_label(slug: str) -> str:
    """Derive a valid subdomain label from a restaurant slug (launch default)."""
    label = slug.lower()
    label = re.sub(r"[^a-z0-9-]", "", label)
    label = label.strip("-")
    return label[:63] or "tenant"


def customer_hostname(row: RestaurantSettings | None, restaurant: Restaurant) -> str:
    """Full hostname this restaurant serves customers on (custom domain wins)."""
    if row is not None and row.custom_domain:
        return row.custom_domain.lower()
    subdomain = row.customer_subdomain if row is not None else None
    if not subdomain:
        subdomain = _slug_label(restaurant.slug)
    return f"{subdomain}.{settings.customer_domain_base}"


def _allowed_for_restaurant(db: Session, restaurant_id: object) -> set[str]:
    """Every hostname that may legitimately serve this restaurant's QR codes.

    The shared customer QR domain (customer_qr_domain) is valid for every
    restaurant: the QR token identifies the restaurant/table, not the hostname.
    A restaurant's own custom domain is additionally valid when configured.
    """
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        return set()
    settings_row = db.get(RestaurantSettings, restaurant_id)
    hosts: set[str] = set()
    if settings.customer_qr_domain:
        hosts.add(settings.customer_qr_domain.lower())
    if settings_row is not None and settings_row.custom_domain:
        hosts.add(settings_row.custom_domain.lower())
    # The managed subdomain stays valid alongside a custom domain.
    hosts.add(customer_hostname(settings_row, restaurant))
    return hosts


def assert_qr_hostname(db: Session, restaurant_id: object, host: str | None) -> None:
    """Fail closed (403) when the caller's Host may not serve this tenant (plan 07).

    Never redirects: a wrong hostname is a cross-tenant attempt, so the only
    safe response is rejection.
    """
    if not host:
        raise AppError(
            403, "QR_HOST_MISMATCH", "Forbidden", "This table code is not valid here."
        )
    normalized = host.lower().split(":", 1)[0]
    if _DEV_MODE and normalized in _DEV_HOSTS:
        # Local development and the test client have no DNS.
        return
    if normalized not in _allowed_for_restaurant(db, restaurant_id):
        raise AppError(
            403,
            "QR_HOST_MISMATCH",
            "Forbidden",
            "This table code is not valid on this address.",
        )


def customer_surface_branding(db: Session, restaurant_id: UUID) -> dict[str, str]:
    """Composition-layer thumbnail of the tenant surface of one restaurant.

    Repositories-service boundary: module routers (the sanctioned composition
    touchpoints) call this to enrich payloads such as the public QR menu.
    """
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        return {"customer_hostname": "", "brand_logo_url": "", "brand_accent_hex": ""}
    settings_row = db.get(RestaurantSettings, restaurant_id)
    return {
        "customer_hostname": customer_hostname(settings_row, restaurant),
        "brand_logo_url": (settings_row.brand_logo_url if settings_row else "") or "",
        "brand_accent_hex": (settings_row.brand_accent_hex if settings_row else "") or "",
    }
