from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RestaurantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    currency_code: str
    tax_rate_bps: int
    qr_ordering_enabled: bool
    customer_hostname: str = ""


class CustomerHostOut(BaseModel):
    """Resolved customer surface config (plan 07 M7)."""

    customer_subdomain: str
    custom_domain: str | None
    """Full hostname the customer QR surface is served on."""
    customer_hostname: str
    brand_logo_url: str
    brand_accent_hex: str


class CustomerHostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # None = field unchanged (the subdomain is locked once set; see below).
    custom_domain: str | None = Field(default=None, max_length=255)
    brand_logo_url: str | None = Field(default=None, max_length=500)
    brand_accent_hex: str | None = Field(default=None, max_length=9)
    customer_subdomain: str | None = Field(default=None)
