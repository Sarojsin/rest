from uuid import UUID

from fastapi import UploadFile
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.modules.catalog.models import MenuCategory, MenuItem
from app.modules.catalog.schemas import (
    MenuItemPatch,
    MenuItemWrite,
    PublicMenuCategory,
    PublicMenuItem,
    PublicMenuOut,
)
from app.modules.operations.models import RestaurantTable
from app.modules.tenancy.models import Restaurant, RestaurantSettings
from app.shared.errors import AppError


def _ensure_cloudinary() -> None:
    if not settings.cloudinary_configured:
        raise AppError(
            500,
            "CLOUDINARY_NOT_CONFIGURED",
            "Image storage not configured",
            "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.",
        )
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def _validate_menu_image(upload: UploadFile) -> str:
    """Return the validated file extension or raise a stable domain error."""
    extension = Path(upload.filename or "").suffix.lstrip(".").lower()
    canonical = {"jpeg": "jpg"}.get(extension, extension)
    if canonical not in {"png", "jpg", "webp"}:
        raise AppError(
            422,
            "UNSUPPORTED_IMAGE_TYPE",
            "Unsupported image type",
            "Menu images must be PNG, JPEG, or WebP.",
        )
    header = upload.file.read(16)
    upload.file.seek(0)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        actual = "png"
    elif header.startswith(b"\xff\xd8\xff"):
        actual = "jpg"
    elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        actual = "webp"
    else:
        actual = None
    if actual is None or actual != canonical:
        raise AppError(
            422,
            "IMAGE_SIGNATURE_MISMATCH",
            "Invalid image",
            "The file content does not match its image type.",
        )
    return canonical


def save_menu_image(
    db: Session,
    restaurant_id: UUID,
    item_id: UUID,
    upload: UploadFile,
) -> MenuItem:
    """Upload a guest photo to Cloudinary and attach its URL to a menu item."""
    item = db.scalar(
        select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id)
    )
    if item is None:
        raise AppError(404, "ITEM_NOT_FOUND", "Not found", "Menu item was not found.")
    _ensure_cloudinary()
    extension = _validate_menu_image(upload)
    data = upload.file.read(5_242_881)  # 5 MB cap
    if len(data) == 0:
        raise AppError(422, "EMPTY_IMAGE", "Empty file", "The uploaded image is empty.")
    if len(data) > 5_242_880:
        raise AppError(
            413,
            "IMAGE_TOO_LARGE",
            "Image too large",
            "Menu images must be 5 MB or smaller.",
        )
    upload.file.seek(0)
    result = cloudinary.uploader.upload(
        upload.file,
        folder="restaurant/menu",
        resource_type="image",
        use_filename=False,
        unique_filename=True,
    )
    item.image_path = result.get("secure_url")
    db.commit()
    db.refresh(item)
    return item


def public_menu(db: Session, restaurant_id: UUID, table: RestaurantTable) -> PublicMenuOut:
    restaurant = db.get(Restaurant, restaurant_id)
    settings = db.get(RestaurantSettings, restaurant_id)
    categories = (
        db.scalars(
            select(MenuCategory)
            .options(selectinload(MenuCategory.items))
            .where(MenuCategory.restaurant_id == restaurant_id, MenuCategory.status == "PUBLISHED")
            .order_by(MenuCategory.display_order)
        )
        .unique()
        .all()
    )
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
    categories = (
        db.scalars(
            select(MenuCategory)
            .options(selectinload(MenuCategory.items))
            .where(MenuCategory.restaurant_id == restaurant_id)
            .order_by(MenuCategory.display_order)
        )
        .unique()
        .all()
    )
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


def create_category(db: Session, restaurant_id: UUID, payload: dict) -> MenuCategory:
    """Create a new menu category."""
    name = payload.get("name", "").strip()
    if not name:
        raise AppError(400, "INVALID_NAME", "Invalid input", "Category name is required.")
    description = payload.get("description", "")
    display_order = payload.get("display_order", 0)
    status = payload.get("status", "PUBLISHED")
    
    # Check if a category with this name already exists for this restaurant
    existing = db.scalar(
        select(MenuCategory).where(
            MenuCategory.restaurant_id == restaurant_id,
            MenuCategory.name == name,
        )
    )
    if existing:
        raise AppError(409, "CATEGORY_EXISTS", "Conflict", f"Category '{name}' already exists.")
    
    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=name,
        description=description,
        display_order=display_order,
        status=status,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, restaurant_id: UUID, category_id: UUID, payload: dict) -> MenuCategory:
    """Update a menu category."""
    category = db.get(MenuCategory, category_id)
    if category is None or category.restaurant_id != restaurant_id:
        raise AppError(404, "CATEGORY_NOT_FOUND", "Not found", "Menu category was not found.")
    
    name = payload.get("name", "").strip()
    if not name:
        raise AppError(400, "INVALID_NAME", "Invalid input", "Category name is required.")
    
    description = payload.get("description", category.description)
    display_order = payload.get("display_order", category.display_order)
    status = payload.get("status", category.status)
    
    # Check if new name conflicts with another category
    if name != category.name:
        existing = db.scalar(
            select(MenuCategory).where(
                MenuCategory.restaurant_id == restaurant_id,
                MenuCategory.name == name,
                MenuCategory.id != category_id,
            )
        )
        if existing:
            raise AppError(409, "CATEGORY_EXISTS", "Conflict", f"Category '{name}' already exists.")
    
    category.name = name
    category.description = description
    category.display_order = display_order
    category.status = status
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, restaurant_id: UUID, category_id: UUID) -> None:
    """Delete a menu category (only if it has no items)."""
    category = db.get(MenuCategory, category_id)
    if category is None or category.restaurant_id != restaurant_id:
        raise AppError(404, "CATEGORY_NOT_FOUND", "Not found", "Menu category was not found.")
    
    # Check if category has items
    item_count = db.scalar(
        select(MenuItem).where(MenuItem.category_id == category_id)
    )
    if item_count is not None and item_count > 0:
        raise AppError(400, "CATEGORY_HAS_ITEMS", "Conflict", "Cannot delete category with existing items. Reassign or delete items first.")
    
    db.delete(category)
    db.commit()


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
