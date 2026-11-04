from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.modules.inventory.models import (
    Ingredient,
    PurchaseOrder,
    PurchaseOrderItem,
    RecipeIngredient,
    StockMovement,
    Supplier,
)
from app.modules.inventory.schemas import (
    IngredientIn,
    IngredientOut,
    IngredientUpdateIn,
    PurchaseOrderIn,
    PurchaseOrderOut,
    RecipeIngredientIn,
    RecipeIngredientOut,
    StockMovementIn,
    StockMovementOut,
    SupplierIn,
    SupplierOut,
)
from app.shared.errors import AppError


def _ingredient_out(ingredient: Ingredient) -> IngredientOut:
    return IngredientOut.model_validate(ingredient)


def _apply_stock_status(ingredient: Ingredient) -> None:
    if ingredient.current_stock <= 0:
        ingredient.status = "OUT_OF_STOCK"
    elif ingredient.current_stock <= ingredient.minimum_stock:
        ingredient.status = "LOW_STOCK"
    else:
        ingredient.status = "IN_STOCK"


# ── Ingredient ──────────────────────────────────────────────────────────────

def list_ingredients(
    db: Session,
    restaurant_id: UUID,
    status: str | None = None,
    supplier_id: UUID | None = None,
) -> list[IngredientOut]:
    stmt = select(Ingredient).where(Ingredient.restaurant_id == restaurant_id)
    if status:
        stmt = stmt.where(Ingredient.status == status)
    if supplier_id:
        stmt = stmt.where(Ingredient.supplier_id == supplier_id)
    ingredients = db.scalars(stmt.order_by(Ingredient.name)).all()
    return [_ingredient_out(i) for i in ingredients]


def get_ingredient(
    db: Session, ingredient_id: UUID, restaurant_id: UUID
) -> IngredientOut | None:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.restaurant_id != restaurant_id:
        return None
    return _ingredient_out(ingredient)


def create_ingredient(db: Session, actor, payload: IngredientIn) -> IngredientOut:
    existing = db.scalar(
        select(Ingredient).where(
            Ingredient.restaurant_id == actor.restaurant_id,
            Ingredient.name == payload.name,
        )
    )
    if existing:
        raise AppError(
            409, "INGREDIENT_NAME_EXISTS", "Ingredient name in use",
            "An ingredient with this name already exists.",
        )

    if payload.supplier_id is not None:
        supplier = db.get(Supplier, payload.supplier_id)
        if supplier is None or supplier.restaurant_id != actor.restaurant_id:
            raise AppError(
                404, "SUPPLIER_NOT_FOUND", "Not found", "Supplier was not found."
            )

    ingredient = Ingredient(
        restaurant_id=actor.restaurant_id,
        name=payload.name,
        code=payload.code,
        unit=payload.unit,
        current_stock=payload.current_stock,
        minimum_stock=payload.minimum_stock,
        supplier_id=payload.supplier_id,
    )
    _apply_stock_status(ingredient)
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return _ingredient_out(ingredient)


def update_ingredient(
    db: Session, actor, ingredient_id: UUID, payload: IngredientUpdateIn
) -> IngredientOut:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.restaurant_id != actor.restaurant_id:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found.")

    data = payload.model_dump(exclude_unset=True)
    if "supplier_id" in data and data["supplier_id"] is not None:
        supplier = db.get(Supplier, data["supplier_id"])
        if supplier is None or supplier.restaurant_id != actor.restaurant_id:
            raise AppError(
                404, "SUPPLIER_NOT_FOUND", "Not found", "Supplier was not found."
            )
    for field, value in data.items():
        setattr(ingredient, field, value)
    _apply_stock_status(ingredient)
    db.commit()
    db.refresh(ingredient)
    return _ingredient_out(ingredient)


def update_ingredient_stock(
    db: Session, actor, ingredient_id: UUID, new_stock: int, reason: str
) -> IngredientOut:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.restaurant_id != actor.restaurant_id:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found.")
    if new_stock < 0:
        raise AppError(
            422, "INVALID_STOCK", "Invalid stock", "Stock cannot be negative."
        )

    old_stock = ingredient.current_stock
    ingredient.current_stock = new_stock
    _apply_stock_status(ingredient)

    movement = StockMovement(
        restaurant_id=actor.restaurant_id,
        ingredient_id=ingredient.id,
        movement_type="ADJUST",
        quantity=new_stock - old_stock,
        new_balance=new_stock,
        reason=reason,
        reference_type="MANUAL",
        recorded_by_membership_id=actor.membership.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(ingredient)
    return _ingredient_out(ingredient)


# ── Supplier ────────────────────────────────────────────────────────────────

def list_suppliers(
    db: Session, restaurant_id: UUID, active_only: bool = True
) -> list[SupplierOut]:
    stmt = select(Supplier).where(Supplier.restaurant_id == restaurant_id)
    if active_only:
        stmt = stmt.where(Supplier.is_active.is_(True))
    suppliers = db.scalars(stmt.order_by(Supplier.name)).all()
    return [SupplierOut.model_validate(s) for s in suppliers]


def get_supplier(
    db: Session, supplier_id: UUID, restaurant_id: UUID
) -> SupplierOut | None:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.restaurant_id != restaurant_id:
        return None
    return SupplierOut.model_validate(supplier)


def create_supplier(db: Session, actor, payload: SupplierIn) -> SupplierOut:
    existing = db.scalar(
        select(Supplier).where(
            Supplier.restaurant_id == actor.restaurant_id,
            Supplier.name == payload.name,
        )
    )
    if existing:
        raise AppError(
            409, "SUPPLIER_NAME_EXISTS", "Supplier name in use",
            "A supplier with this name already exists.",
        )

    supplier = Supplier(restaurant_id=actor.restaurant_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


# ── Purchase Order ──────────────────────────────────────────────────────────

def list_purchase_orders(
    db: Session,
    restaurant_id: UUID,
    status: str | None = None,
    supplier_id: UUID | None = None,
) -> list[PurchaseOrderOut]:
    stmt = select(PurchaseOrder).where(PurchaseOrder.restaurant_id == restaurant_id)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    if supplier_id:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    pos = db.scalars(stmt.order_by(PurchaseOrder.created_at.desc())).all()
    return [PurchaseOrderOut.model_validate(p) for p in pos]


def get_purchase_order(
    db: Session, po_id: UUID, restaurant_id: UUID
) -> PurchaseOrderOut | None:
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.restaurant_id != restaurant_id:
        return None
    return PurchaseOrderOut.model_validate(po)


def create_purchase_order(
    db: Session, actor, payload: PurchaseOrderIn
) -> PurchaseOrderOut:
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None or supplier.restaurant_id != actor.restaurant_id:
        raise AppError(404, "SUPPLIER_NOT_FOUND", "Not found", "Supplier was not found.")

    existing = db.scalar(
        select(PurchaseOrder).where(
            PurchaseOrder.restaurant_id == actor.restaurant_id,
            PurchaseOrder.code == payload.code,
        )
    )
    if existing:
        raise AppError(
            409, "PURCHASE_ORDER_CODE_EXISTS", "PO code in use",
            "A purchase order with this code already exists.",
        )

    total = 0
    rows: list[PurchaseOrderItem] = []
    for item in payload.items:
        ingredient = db.get(Ingredient, item.ingredient_id)
        if ingredient is None or ingredient.restaurant_id != actor.restaurant_id:
            raise AppError(
                404, "INGREDIENT_NOT_FOUND", "Not found",
                f"Ingredient {item.ingredient_id} not found.",
            )
        line_total = item.unit_price_minor * item.quantity
        total += line_total
        rows.append(
            PurchaseOrderItem(
                ingredient_id=item.ingredient_id,
                quantity=item.quantity,
                unit_price_minor=item.unit_price_minor,
                total_minor=line_total,
            )
        )

    po = PurchaseOrder(
        restaurant_id=actor.restaurant_id,
        supplier_id=payload.supplier_id,
        code=payload.code,
        status=payload.status or "DRAFT",
        expected_date=payload.expected_date,
        notes=payload.notes,
        total_minor=total,
        items=rows,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return PurchaseOrderOut.model_validate(po)


def receive_purchase_order(
    db: Session, actor, po_id: UUID
) -> PurchaseOrderOut:
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.restaurant_id != actor.restaurant_id:
        raise AppError(
            404, "PURCHASE_ORDER_NOT_FOUND", "Not found", "Purchase order was not found."
        )
    if po.status == "RECEIVED":
        raise AppError(
            409, "PO_ALREADY_RECEIVED", "PO already received",
            "This purchase order has already been received.",
        )
    if po.status == "CANCELLED":
        raise AppError(
            409, "PO_CANCELLED", "PO cancelled",
            "A cancelled purchase order cannot be received.",
        )

    for item in po.items:
        ingredient = db.get(Ingredient, item.ingredient_id)
        if ingredient is None:
            raise AppError(
                404, "INGREDIENT_NOT_FOUND", "Not found",
                f"Ingredient {item.ingredient_id} not found.",
            )
        delta = item.quantity - item.received_quantity
        ingredient.current_stock += delta
        _apply_stock_status(ingredient)
        item.received_quantity = item.quantity
        db.add(
            StockMovement(
                restaurant_id=actor.restaurant_id,
                ingredient_id=ingredient.id,
                movement_type="RECEIVE",
                quantity=delta,
                new_balance=ingredient.current_stock,
                reason=f"Received purchase order {po.code}",
                reference_id=po.id,
                reference_type="PO",
                recorded_by_membership_id=actor.membership.id,
            )
        )

    po.status = "RECEIVED"
    po.received_date = datetime.now(UTC)
    po.delivered_by_membership_id = actor.membership.id
    db.commit()
    db.refresh(po)
    return PurchaseOrderOut.model_validate(po)


# ── Recipe Ingredient ───────────────────────────────────────────────────────

def list_recipe_ingredients(
    db: Session, restaurant_id: UUID, menu_item_id: UUID | None = None
) -> list[RecipeIngredientOut]:
    stmt = select(RecipeIngredient).where(
        RecipeIngredient.restaurant_id == restaurant_id
    )
    if menu_item_id:
        stmt = stmt.where(RecipeIngredient.menu_item_id == menu_item_id)
    rows = db.scalars(stmt.order_by(RecipeIngredient.ingredient_id)).all()
    return [RecipeIngredientOut.model_validate(r) for r in rows]


def set_recipe_ingredients(
    db: Session,
    actor,
    menu_item_id: UUID,
    items: list[RecipeIngredientIn],
) -> list[RecipeIngredientOut]:
    exists = db.execute(
        text(
            "SELECT 1 FROM menu_items WHERE id = :id AND restaurant_id = :rid"
        ),
        {"id": menu_item_id, "rid": actor.restaurant_id},
    ).scalar_one_or_none()
    if exists is None:
        raise AppError(
            404, "MENU_ITEM_NOT_FOUND", "Not found", "Menu item was not found."
        )

    db.execute(
        delete(RecipeIngredient).where(
            RecipeIngredient.menu_item_id == menu_item_id,
            RecipeIngredient.restaurant_id == actor.restaurant_id,
        )
    )

    created: list[RecipeIngredient] = []
    for item in items:
        ingredient = db.get(Ingredient, item.ingredient_id)
        if ingredient is None or ingredient.restaurant_id != actor.restaurant_id:
            raise AppError(
                404, "INGREDIENT_NOT_FOUND", "Not found",
                f"Ingredient {item.ingredient_id} not found.",
            )
        row = RecipeIngredient(
            restaurant_id=actor.restaurant_id,
            menu_item_id=menu_item_id,
            ingredient_id=item.ingredient_id,
            quantity_per_serving=item.quantity_per_serving,
            quantity_per_order=item.quantity_per_order,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return [RecipeIngredientOut.model_validate(r) for r in created]


# ── Stock Movement ──────────────────────────────────────────────────────────

def list_stock_movements(
    db: Session,
    restaurant_id: UUID,
    ingredient_id: UUID | None = None,
    limit: int = 100,
) -> list[StockMovementOut]:
    stmt = select(StockMovement).where(StockMovement.restaurant_id == restaurant_id)
    if ingredient_id:
        stmt = stmt.where(StockMovement.ingredient_id == ingredient_id)
    rows = db.scalars(
        stmt.order_by(StockMovement.created_at.desc()).limit(limit)
    ).all()
    return [StockMovementOut.model_validate(r) for r in rows]


def record_stock_movement(
    db: Session, actor, payload: StockMovementIn
) -> StockMovementOut:
    ingredient = db.get(Ingredient, payload.ingredient_id)
    if ingredient is None or ingredient.restaurant_id != actor.restaurant_id:
        raise AppError(404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found.")

    movement_type = payload.movement_type
    quantity = payload.quantity

    if movement_type in {"RECEIVE", "DEDUCT", "WASTE"} and quantity <= 0:
        raise AppError(
            422, "INVALID_QUANTITY", "Invalid quantity",
            "Quantity must be greater than zero for this movement type.",
        )

    if movement_type == "RECEIVE":
        new_balance = ingredient.current_stock + quantity
    elif movement_type == "DEDUCT":
        if quantity > ingredient.current_stock:
            raise AppError(
                422, "INSUFFICIENT_STOCK", "Insufficient stock",
                f"Cannot deduct {quantity}; only {ingredient.current_stock} available.",
            )
        new_balance = ingredient.current_stock - quantity
    elif movement_type == "WASTE":
        if quantity > ingredient.current_stock:
            raise AppError(
                422, "INSUFFICIENT_STOCK", "Insufficient stock",
                f"Cannot waste {quantity}; only {ingredient.current_stock} available.",
            )
        new_balance = ingredient.current_stock - quantity
    else:  # ADJUST
        if not payload.reason:
            raise AppError(
                422, "ADJUSTMENT_REASON_REQUIRED", "Adjustment reason required",
                "An adjustment reason is required.",
            )
        new_balance = ingredient.current_stock + quantity

    if new_balance < 0:
        raise AppError(
            422, "INVALID_STOCK", "Invalid stock", "Stock cannot become negative."
        )

    ingredient.current_stock = new_balance
    _apply_stock_status(ingredient)

    movement = StockMovement(
        restaurant_id=actor.restaurant_id,
        ingredient_id=ingredient.id,
        movement_type=movement_type,
        quantity=quantity,
        new_balance=new_balance,
        reason=payload.reason,
        reference_id=payload.reference_id,
        reference_type=payload.reference_type,
        recorded_by_membership_id=actor.membership.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return StockMovementOut.model_validate(movement)


# ── Menu Item Recipe Cost ──────────────────────────────────────────────────

def calculate_recipe_cost(db: Session, menu_item_id: UUID, restaurant_id: UUID) -> dict:
    rows = db.scalars(
        select(RecipeIngredient).where(
            RecipeIngredient.menu_item_id == menu_item_id,
            RecipeIngredient.restaurant_id == restaurant_id,
        )
    ).all()

    breakdown = []
    total = 0
    for row in rows:
        ingredient = db.get(Ingredient, row.ingredient_id)
        if ingredient is None:
            continue
        cost = 0
        breakdown.append(
            {
                "ingredient_name": ingredient.name,
                "quantity": row.quantity_per_order,
                "unit_cost_minor": cost,
                "line_cost_minor": cost * row.quantity_per_order,
            }
        )
        total += cost * row.quantity_per_order

    return {"total_cost_minor": total, "breakdown": breakdown}


__all__ = [
    "list_ingredients",
    "get_ingredient",
    "create_ingredient",
    "update_ingredient",
    "update_ingredient_stock",
    "list_suppliers",
    "get_supplier",
    "create_supplier",
    "list_purchase_orders",
    "get_purchase_order",
    "create_purchase_order",
    "receive_purchase_order",
    "list_recipe_ingredients",
    "set_recipe_ingredients",
    "list_stock_movements",
    "record_stock_movement",
    "calculate_recipe_cost",
]
