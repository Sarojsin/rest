from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission
from app.db.session import get_db
from app.modules.inventory.schemas import (
    IngredientIn,
    IngredientOut,
    IngredientUpdateIn,
    PurchaseOrderIn,
    PurchaseOrderOut,
    RecipeIngredientOut,
    RecipeIn,
    StockMovementIn,
    StockMovementOut,
    SupplierIn,
    SupplierOut,
)
from app.modules.inventory.services import inventory as inventory_service
from app.shared.errors import AppError

router = APIRouter(tags=["inventory"])


class StockLevelIn(BaseModel):
    new_stock: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=200)


# ── Ingredients ─────────────────────────────────────────────────────────────

@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(
    status: str | None = Query(default=None),
    supplier_id: UUID | None = Query(default=None),
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> list[IngredientOut]:
    return inventory_service.list_ingredients(
        db, actor.restaurant_id, status, supplier_id
    )


@router.post("/ingredients", response_model=IngredientOut, status_code=201)
def create_ingredient(
    payload: IngredientIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.create_ingredient(db, actor, payload)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientOut)
def get_ingredient(
    ingredient_id: UUID,
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    result = inventory_service.get_ingredient(db, ingredient_id, actor.restaurant_id)
    if result is None:
        raise AppError(
            404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found."
        )
    return result


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(
    ingredient_id: UUID,
    payload: IngredientUpdateIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.update_ingredient(db, actor, ingredient_id, payload)


@router.patch("/ingredients/{ingredient_id}/stock", response_model=IngredientOut)
def set_ingredient_stock(
    ingredient_id: UUID,
    payload: StockLevelIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.update_ingredient_stock(
        db, actor, ingredient_id, payload.new_stock, payload.reason
    )


# ── Suppliers ───────────────────────────────────────────────────────────────

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    active_only: bool = Query(default=True),
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> list[SupplierOut]:
    return inventory_service.list_suppliers(db, actor.restaurant_id, active_only)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(
    payload: SupplierIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> SupplierOut:
    return inventory_service.create_supplier(db, actor, payload)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: UUID,
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> SupplierOut:
    result = inventory_service.get_supplier(db, supplier_id, actor.restaurant_id)
    if result is None:
        raise AppError(404, "SUPPLIER_NOT_FOUND", "Not found", "Supplier was not found.")
    return result


# ── Purchase orders ─────────────────────────────────────────────────────────

@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    status: str | None = Query(default=None),
    supplier_id: UUID | None = Query(default=None),
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> list[PurchaseOrderOut]:
    return inventory_service.list_purchase_orders(
        db, actor.restaurant_id, status, supplier_id
    )


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> PurchaseOrderOut:
    return inventory_service.create_purchase_order(db, actor, payload)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    po_id: UUID,
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> PurchaseOrderOut:
    result = inventory_service.get_purchase_order(db, po_id, actor.restaurant_id)
    if result is None:
        raise AppError(
            404, "PURCHASE_ORDER_NOT_FOUND", "Not found", "Purchase order was not found."
        )
    return result


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(
    po_id: UUID,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> PurchaseOrderOut:
    return inventory_service.receive_purchase_order(db, actor, po_id)


# ── Recipes ─────────────────────────────────────────────────────────────────

@router.get("/recipes", response_model=list[RecipeIngredientOut])
def list_recipe_ingredients(
    menu_item_id: UUID | None = Query(default=None),
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> list[RecipeIngredientOut]:
    return inventory_service.list_recipe_ingredients(
        db, actor.restaurant_id, menu_item_id
    )


@router.put("/recipes/{menu_item_id}", response_model=list[RecipeIngredientOut])
def set_recipe(
    menu_item_id: UUID,
    payload: RecipeIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> list[RecipeIngredientOut]:
    return inventory_service.set_recipe_ingredients(
        db, actor, menu_item_id, payload.items
    )


@router.get("/recipes/{menu_item_id}/cost")
def recipe_cost(
    menu_item_id: UUID,
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> dict:
    return inventory_service.calculate_recipe_cost(
        db, menu_item_id, actor.restaurant_id
    )


# ── Stock movements ─────────────────────────────────────────────────────────

@router.get("/stock-movements", response_model=list[StockMovementOut])
def list_stock_movements(
    ingredient_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    actor: Actor = Depends(require_permission("inventory.read")),
    db: Session = Depends(get_db),
) -> list[StockMovementOut]:
    return inventory_service.list_stock_movements(
        db, actor.restaurant_id, ingredient_id, limit
    )


@router.post("/stock-movements", response_model=StockMovementOut, status_code=201)
def create_stock_movement(
    payload: StockMovementIn,
    actor: Actor = Depends(require_permission("inventory.manage")),
    db: Session = Depends(get_db),
) -> StockMovementOut:
    return inventory_service.record_stock_movement(db, actor, payload)
