from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.schemas.staff import MenuItemPatch, MenuItemWrite
from app.services import menu as menu_service

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
    actor: Actor = Depends(require_permission("menu.manage")),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.create_item(db, actor.restaurant_id, payload)
    return {"id": str(item.id), "name": item.name, "status": item.status}


@router.patch("/menu/items/{item_id}")
def patch_item(
    item_id: UUID,
    payload: MenuItemPatch,
    actor: Actor = Depends(require_permission("menu.manage")),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.patch_item(db, actor.restaurant_id, item_id, payload)
    return {
        "id": str(item.id),
        "name": item.name,
        "status": item.status,
        "current_price_minor": item.current_price_minor,
    }
