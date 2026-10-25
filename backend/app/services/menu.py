from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.identity import Restaurant, RestaurantSettings
from app.models.menu import MenuCategory, MenuItem
from app.models.tables import RestaurantTable
from app.schemas.public import PublicMenuCategory, PublicMenuItem, PublicMenuOut
from app.schemas.staff import MenuItemPatch, MenuItemWrite


def public_menu(db: Session, restaurant_id: UUID, table: RestaurantTable) -> PublicMenuOut:
    restaurant = db.get(Restaurant, restaurant_id)
    settings = db.get(RestaurantSettings, restaurant_id)
    categories = db.scalars(
        select(MenuCategory)
        .options(selectinload(MenuCategory.items))
        .where(MenuCategory.restaurant_id == restaurant_id, MenuCategory.status == "PUBLISHED")
        .order_by(MenuCategory.display_order)
    ).unique().all()
    return PublicMenuOut(
        restaurant_name=restaurant.name if restaurant else "Restaurant",
        currency_code=restaurant.currency_code if restaurant else "USD",
        table_id=table.id,
        table_display_name=table.display_name,
        qr_ordering_enabled=bool(settings.qr_ordering_enabled) if settings else True,
        categories=[
            PublicMenuCategory(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                display_order=cat.display_order,
                items=[
                    PublicMenuItem(
                        id=item.id,
                        name=item.name,
                        description=item.description,
                        current_price_minor=item.current_price_minor,
                        currency_code=item.currency_code,
                        status=item.status,
                        display_order=item.display_order,
                        image_emoji=item.image_emoji,
                        image_path=item.image_path or "",
                        model_path=item.model_path or "",
                        ingredients_text=item.ingredients_text or "",
                    )
                    for item in sorted(cat.items, key=lambda i: i.display_order)
                    if item.status == "PUBLISHED"
                ],
            )
            for cat in categories
        ],
    )


def staff_menu(db: Session, restaurant_id: UUID) -> list[dict]:
    categories = db.scalars(
        select(MenuCategory)
        .options(selectinload(MenuCategory.items))
        .where(MenuCategory.restaurant_id == restaurant_id)
        .order_by(MenuCategory.display_order)
    ).unique().all()
    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "description": cat.description,
            "display_order": cat.display_order,
            "status": cat.status,
            "items": [
                {
                    "id": str(item.id),
                    "category_id": str(item.category_id),
                    "name": item.name,
                    "description": item.description,
                    "current_price_minor": item.current_price_minor,
                    "currency_code": item.currency_code,
                    "status": item.status,
                    "display_order": item.display_order,
                    "image_emoji": item.image_emoji,
                    "image_path": item.image_path or "",
                    "model_path": item.model_path or "",
                    "ingredients_text": item.ingredients_text or "",
                }
                for item in sorted(cat.items, key=lambda i: i.display_order)
            ],
        }
        for cat in categories
    ]


def create_item(db: Session, restaurant_id: UUID, payload: MenuItemWrite) -> MenuItem:
    category = db.scalar(
        select(MenuCategory).where(
            MenuCategory.id == payload.category_id, MenuCategory.restaurant_id == restaurant_id
        )
    )
    if category is None:
        raise AppError(404, "CATEGORY_NOT_FOUND", "Not found", "Menu category was not found.")
    item = MenuItem(
        restaurant_id=restaurant_id,
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        current_price_minor=payload.current_price_minor,
        status=payload.status,
        ingredients_text=payload.ingredients_text,
        image_emoji=payload.image_emoji,
        image_path=payload.image_path,
        model_path=payload.model_path,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def patch_item(db: Session, restaurant_id: UUID, item_id: UUID, payload: MenuItemPatch) -> MenuItem:
    item = db.scalar(
        select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id)
    )
    if item is None:
        raise AppError(404, "ITEM_NOT_FOUND", "Not found", "Menu item was not found.")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
