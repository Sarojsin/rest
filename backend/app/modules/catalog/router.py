from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission, require_permission_and_feature
from app.db.session import get_db
from app.modules.catalog.schemas import MenuItemPatch, MenuItemWrite, MenuCategoryWrite, MenuCategoryPatch
from app.modules.catalog.services import menu as menu_service

router = APIRouter(tags=["menu"])


@router.get("/menu")
def get_menu(
    actor: Actor = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return menu_service.staff_menu(db, actor.restaurant_id)


@router.post("/menu/items")
def create_item(
    payload: MenuItemWrite,
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.create_item(db, actor.restaurant_id, payload)
    return {"id": str(item.id), "name": item.name, "status": item.status}


@router.patch("/menu/items/{item_id}")
def patch_item(
    item_id: UUID,
    payload: MenuItemPatch,
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.patch_item(db, actor.restaurant_id, item_id, payload)
    return {
        "id": str(item.id),
        "name": item.name,
        "status": item.status,
        "current_price_minor": item.current_price_minor,
        "ingredients_text": item.ingredients_text or "",
    }


@router.post("/menu/items/{item_id}/image")
def upload_menu_image(
    item_id: UUID,
    image: UploadFile = File(...),
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a guest photo for a menu item."""
    item = menu_service.save_menu_image(db, actor.restaurant_id, item_id, image)
    return {
        "id": str(item.id),
        "image_path": item.image_path,
    }


@router.get("/menu/categories")
def list_categories(
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    """List all menu categories for a restaurant."""
    categories = db.scalars(
        select(MenuCategory).where(MenuCategory.restaurant_id == actor.restaurant_id)
    ).unique().all()
    return {
        "categories": [
            {
                "id": str(cat.id),
                "name": cat.name,
                "description": cat.description,
                "display_order": cat.display_order,
                "status": cat.status,
            }
            for cat in categories
        ]
    }


@router.post("/menu/categories")
def create_category(
    payload: MenuCategoryWrite,
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new menu category."""
    category = menu_service.create_category(db, actor.restaurant_id, payload.model_dump())
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "display_order": category.display_order,
        "status": category.status,
    }


@router.patch("/menu/categories/{category_id}")
def update_category(
    category_id: UUID,
    payload: MenuCategoryPatch,
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    """Update a menu category."""
    category = menu_service.update_category(db, actor.restaurant_id, category_id, payload.model_dump())
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "display_order": category.display_order,
        "status": category.status,
    }


@router.delete("/menu/categories/{category_id}")
def delete_category(
    category_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("menu.manage", "menu_management")),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a menu category (only if empty)."""
    menu_service.delete_category(db, actor.restaurant_id, category_id)
    return {"detail": "Category deleted"}