from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import Actor, require_permission_and_feature
from app.db.session import get_db
from app.modules.inventory.schemas import (
    IngredientBatchIn,
    IngredientBatchOut,
    IngredientIn,
    IngredientOut,
    IngredientUpdateIn,
    PurchaseOrderIn,
    PurchaseOrderOut,
    RecipeIngredientOut,
    RecipeIn,
    StockCountIn,
    StockCountItemIn,
    StockCountItemOut,
    StockCountOut,
    StockMovementIn,
    StockMovementOut,
    SupplierIn,
    SupplierOut,
)
from app.modules.inventory.services import (
    inventory as inventory_service,
    inventory_batches as batch_service,
    stock_counts as count_service,
)
from app.modules.inventory.models import Ingredient
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
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[IngredientOut]:
    return inventory_service.list_ingredients(
        db, actor.restaurant_id, status, supplier_id
    )


@router.post("/ingredients", response_model=IngredientOut, status_code=201)
def create_ingredient(
    payload: IngredientIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.create_ingredient(db, actor, payload)


@router.get("/ingredients/{ingredient_id}", response_model=IngredientOut)
def get_ingredient(
    ingredient_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
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
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.update_ingredient(db, actor, ingredient_id, payload)


@router.patch("/ingredients/{ingredient_id}/stock", response_model=IngredientOut)
def set_ingredient_stock(
    ingredient_id: UUID,
    payload: StockLevelIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> IngredientOut:
    return inventory_service.update_ingredient_stock(
        db, actor, ingredient_id, payload.new_stock, payload.reason
    )


# ── Suppliers ───────────────────────────────────────────────────────────────

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    active_only: bool = Query(default=True),
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[SupplierOut]:
    return inventory_service.list_suppliers(db, actor.restaurant_id, active_only)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(
    payload: SupplierIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> SupplierOut:
    return inventory_service.create_supplier(db, actor, payload)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
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
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[PurchaseOrderOut]:
    return inventory_service.list_purchase_orders(
        db, actor.restaurant_id, status, supplier_id
    )


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> PurchaseOrderOut:
    return inventory_service.create_purchase_order(db, actor, payload)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(
    po_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
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
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> PurchaseOrderOut:
    return inventory_service.receive_purchase_order(db, actor, po_id)


# ── Recipes ─────────────────────────────────────────────────────────────────

@router.get("/recipes", response_model=list[RecipeIngredientOut])
def list_recipe_ingredients(
    menu_item_id: UUID | None = Query(default=None),
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[RecipeIngredientOut]:
    return inventory_service.list_recipe_ingredients(
        db, actor.restaurant_id, menu_item_id
    )


@router.put("/recipes/{menu_item_id}", response_model=list[RecipeIngredientOut])
def set_recipe(
    menu_item_id: UUID,
    payload: RecipeIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> list[RecipeIngredientOut]:
    return inventory_service.set_recipe_ingredients(
        db, actor, menu_item_id, payload.items
    )


@router.get("/recipes/{menu_item_id}/cost")
def recipe_cost(
    menu_item_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
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
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[StockMovementOut]:
    return inventory_service.list_stock_movements(
        db, actor.restaurant_id, ingredient_id, limit
    )


@router.post("/stock-movements", response_model=StockMovementOut, status_code=201)
def create_stock_movement(
    payload: StockMovementIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> StockMovementOut:
    return inventory_service.record_stock_movement(db, actor, payload)


# ── Ingredient Batches (FEFO tracking) ───────────────────────────────────

@router.get("/batches", response_model=list[IngredientBatchOut])
def list_batches(
    ingredient_id: UUID | None = Query(default=None),
    include_expired: bool = Query(default=False),
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[IngredientBatchOut]:
    batches = batch_service.list_batches(
        db, actor.restaurant_id, ingredient_id, include_expired
    )
    result = []
    for b in batches:
        result.append(
            IngredientBatchOut(
                id=b.id,
                ingredient_id=b.ingredient_id,
                ingredient_name=b.ingredient.name if b.ingredient else None,
                batch_no=b.batch_no,
                expiry_date=b.expiry_date,
                quantity=b.quantity,
                cost_per_unit_minor=b.cost_per_unit_minor,
                is_expired=b.is_expired,
            )
        )
    return result


@router.post("/batches", response_model=IngredientBatchOut, status_code=201)
def create_batch(
    payload: IngredientBatchIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> IngredientBatchOut:
    batch = batch_service.create_batch(
        db,
        actor.restaurant_id,
        payload.ingredient_id,
        payload.batch_no,
        payload.expiry_date,
        payload.quantity,
        payload.cost_per_unit_minor,
    )
    return IngredientBatchOut(
        id=batch.id,
        ingredient_id=batch.ingredient_id,
        ingredient_name=batch.ingredient.name if batch.ingredient else None,
        batch_no=batch.batch_no,
        expiry_date=batch.expiry_date,
        quantity=batch.quantity,
        cost_per_unit_minor=batch.cost_per_unit_minor,
        is_expired=batch.is_expired,
    )


@router.get("/batches/{batch_id}", response_model=IngredientBatchOut)
def get_batch(
    batch_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> IngredientBatchOut:
    batch = batch_service.get_batch(db, batch_id, actor.restaurant_id)
    if batch is None:
        raise AppError(404, "BATCH_NOT_FOUND", "Not found", "Batch was not found.")
    return IngredientBatchOut(
        id=batch.id,
        ingredient_id=batch.ingredient_id,
        ingredient_name=batch.ingredient.name if batch.ingredient else None,
        batch_no=batch.batch_no,
        expiry_date=batch.expiry_date,
        quantity=batch.quantity,
        cost_per_unit_minor=batch.cost_per_unit_minor,
        is_expired=batch.is_expired,
    )


# ── Stock Counts ─────────────────────────────────────────────────────────

@router.get("/stock-counts", response_model=list[StockCountOut])
def list_stock_counts(
    branch_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
) -> list[StockCountOut]:
    counts = count_service.list_stock_counts(
        db, actor.restaurant_id, branch_id, status
    )
    result = []
    for c in counts:
        result.append(
            StockCountOut(
                id=c.id,
                branch_id=c.branch_id,
                count_date=c.count_date,
                status=c.status,
                notes=c.notes,
                items=[
                    StockCountItemOut(
                        id=i.id,
                        ingredient_id=i.ingredient_id,
                        ingredient_name=i.ingredient.name if i.ingredient else None,
                        expected_qty=i.expected_qty,
                        counted_qty=i.counted_qty,
                        variance_qty=i.variance_qty,
                    )
                    for i in (c.items or [])
                ],
            )
        )
    return result


@router.post("/stock-counts", response_model=StockCountOut, status_code=201)
def create_stock_count(
    payload: StockCountIn,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> StockCountOut:
    try:
        count = count_service.create_stock_count(
            db,
            actor.restaurant_id,
            actor.membership.id,
            payload.branch_id,
            payload.count_date,
            payload.notes,
            [
                {
                    "ingredient_id": item.ingredient_id,
                    "expected_qty": item.expected_qty,
                    "counted_qty": item.counted_qty,
                }
                for item in payload.items
            ],
        )
        return StockCountOut(
            id=count.id,
            branch_id=count.branch_id,
            count_date=count.count_date,
            status=count.status,
            notes=count.notes,
            items=[
                StockCountItemOut(
                    id=i.id,
                    ingredient_id=i.ingredient_id,
                    ingredient_name=i.ingredient.name if i.ingredient else None,
                    expected_qty=i.expected_qty,
                    counted_qty=i.counted_qty,
                    variance_qty=i.variance_qty,
                )
                for i in (count.items or [])
            ],
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"STOCK_COUNT_ERROR: {tb}")
        raise AppError(500, "STOCK_COUNT_ERROR", "Stock count creation failed", str(e)[:200])


@router.post("/stock-counts/{count_id}/complete", response_model=StockCountOut)
def complete_stock_count(
    count_id: UUID,
    actor: Actor = Depends(require_permission_and_feature("inventory.manage", "inventory")),
    db: Session = Depends(get_db),
) -> StockCountOut:
    count = count_service.complete_stock_count(
        db, count_id, actor.restaurant_id, actor.membership.id
    )
    return StockCountOut(
        id=count.id,
        branch_id=count.branch_id,
        count_date=count.count_date,
        status=count.status,
        notes=count.notes,
        items=[
            StockCountItemOut(
                id=i.id,
                ingredient_id=i.ingredient_id,
                ingredient_name=i.ingredient.name if i.ingredient else None,
                expected_qty=i.expected_qty,
                counted_qty=i.counted_qty,
                variance_qty=i.variance_qty,
            )
            for i in (count.items or [])
        ],
    )


# ── Reports ──────────────────────────────────────────────────────────────

@router.get("/reports/low-stock")
def report_low_stock(
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
):
    ingredients = inventory_service.list_ingredients(
        db, actor.restaurant_id, status="LOW_STOCK"
    )
    return {
        "restaurant_id": str(actor.restaurant_id),
        "low_stock_count": len(ingredients),
        "ingredients": [
            {
                "id": str(i.id),
                "name": i.name,
                "sku": i.sku,
                "current_stock": i.current_stock,
                "minimum_stock": i.minimum_stock,
                "unit": i.unit,
                "storage_location": i.storage_location,
            }
            for i in ingredients
        ],
    }


@router.get("/reports/consumption")
def report_consumption(
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func, select
    from app.modules.inventory.models import StockMovement

    rows = db.execute(
        select(
            StockMovement.ingredient_id,
            func.sum(StockMovement.quantity).label("total_deducted"),
        )
        .where(
            StockMovement.restaurant_id == actor.restaurant_id,
            StockMovement.movement_type == "DEDUCT",
        )
        .group_by(StockMovement.ingredient_id)
    ).all()

    result = []
    for ingredient_id, total_deducted in rows:
        ingredient = db.get(Ingredient, ingredient_id)
        result.append({
            "ingredient_id": str(ingredient_id),
            "ingredient_name": ingredient.name if ingredient else None,
            "total_deducted": total_deducted or 0,
            "unit": ingredient.unit if ingredient else None,
        })
    result.sort(key=lambda x: x["total_deducted"], reverse=True)
    return {
        "restaurant_id": str(actor.restaurant_id),
        "consumption": result,
    }


@router.get("/reports/waste")
def report_waste(
    days: int = 30,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
):
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import func, select
    from app.modules.inventory.models import StockMovement

    days = max(1, min(days, 365))
    since = datetime.now(UTC) - timedelta(days=days)

    rows = db.execute(
        select(
            StockMovement.ingredient_id,
            func.sum(StockMovement.quantity).label("total_wasted"),
            func.count(StockMovement.id).label("event_count"),
        )
        .where(
            StockMovement.restaurant_id == actor.restaurant_id,
            StockMovement.movement_type == "WASTE",
            StockMovement.created_at >= since,
        )
        .group_by(StockMovement.ingredient_id)
    ).all()

    events = []
    total_events = 0
    for ingredient_id, total_wasted, event_count in rows:
        ingredient = db.get(Ingredient, ingredient_id)
        total_events += event_count or 0
        events.append({
            "ingredient_id": str(ingredient_id),
            "ingredient_name": ingredient.name if ingredient else None,
            "total_wasted": total_wasted or 0,
            "event_count": event_count or 0,
            "unit": ingredient.unit if ingredient else None,
        })
    events.sort(key=lambda x: x["total_wasted"], reverse=True)
    return {
        "restaurant_id": str(actor.restaurant_id),
        "window_days": days,
        "event_count": total_events,
        "waste": events,
    }


@router.get("/reports/expiring-batches")
def report_expiring_batches(
    days: int = 7,
    actor: Actor = Depends(require_permission_and_feature("inventory.read", "inventory")),
    db: Session = Depends(get_db),
):
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.modules.inventory.models import IngredientBatch

    days = max(1, min(days, 365))
    horizon = datetime.now(UTC) + timedelta(days=days)

    batches = (
        db.scalars(
            select(IngredientBatch)
            .options(selectinload(IngredientBatch.ingredient))
            .where(
                IngredientBatch.restaurant_id == actor.restaurant_id,
                IngredientBatch.quantity > 0,
                IngredientBatch.expiry_date.is_not(None),
                IngredientBatch.expiry_date <= horizon,
            )
            .order_by(IngredientBatch.expiry_date.asc(), IngredientBatch.batch_no.asc())
        )
        .unique()
        .all()
    )

    now = datetime.now(UTC)
    return {
        "restaurant_id": str(actor.restaurant_id),
        "window_days": days,
        "batches": [
            {
                "id": str(b.id),
                "batch_no": b.batch_no,
                "ingredient_id": str(b.ingredient_id),
                "ingredient_name": b.ingredient.name if b.ingredient else None,
                "unit": b.ingredient.unit if b.ingredient else None,
                "expiry_date": b.expiry_date,
                "quantity": b.quantity,
                "cost_value_minor": b.quantity * b.cost_per_unit_minor,
                "expired": b.expiry_date < now,
            }
            for b in batches
        ],
    }
