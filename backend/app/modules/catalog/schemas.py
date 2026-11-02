from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    current_price_minor: int = Field(ge=0)
    category_id: UUID
    status: str = "PUBLISHED"
    ingredients_text: str = Field(default="", max_length=500)
    image_emoji: str = Field(default="", max_length=8)
    image_path: str = Field(
        default="",
        max_length=255,
        pattern=r"^$|^/menu/food/[A-Za-z0-9._-]+\.(webp|jpg|jpeg|png|avif)$",
    )
    model_path: str = Field(
        default="",
        max_length=255,
        pattern=r"^$|^/menu/models/[A-Za-z0-9._-]+\.glb$",
    )


class MenuItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    current_price_minor: int | None = Field(default=None, ge=0)
    status: str | None = None
    ingredients_text: str | None = Field(default=None, max_length=500)
    image_emoji: str | None = None
    image_path: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^$|^/menu/food/[A-Za-z0-9._-]+\.(webp|jpg|jpeg|png|avif)$",
    )
    model_path: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^$|^/menu/models/[A-Za-z0-9._-]+\.glb$",
    )


class PublicMenuItem(BaseModel):
    id: UUID
    name: str
    description: str
    current_price_minor: int
    currency_code: str
    status: str
    display_order: int
    image_emoji: str
    image_path: str = Field(default="", max_length=255)
    model_path: str = Field(default="", max_length=255)
    ingredients_text: str = Field(default="", max_length=500)


class PublicMenuCategory(BaseModel):
    id: UUID
    name: str
    description: str
    display_order: int
    items: list[PublicMenuItem]


class PublicMenuOut(BaseModel):
    restaurant_name: str
    currency_code: str
    table_id: UUID
    table_display_name: str
    qr_ordering_enabled: bool
    categories: list[PublicMenuCategory]
