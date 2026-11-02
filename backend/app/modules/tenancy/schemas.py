from uuid import UUID

from pydantic import BaseModel


class RestaurantOut(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    currency_code: str
    tax_rate_bps: int
    qr_ordering_enabled: bool
