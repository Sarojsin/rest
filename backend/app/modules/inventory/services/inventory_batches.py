"""Ingredient batch management with FEFO (first-expired-first-out) picking.

Batches track inventory at the granular level — each batch has a batch number,
optional expiry date, quantity (in base-unit subunits), and cost per unit.
When inventory is deducted (e.g. for kitchen consumption), batches are
consumed in expiry order so the soonest-to-expire stock is used first.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import Ingredient, IngredientBatch, StockMovement
from app.shared.errors import AppError


def list_batches(
    db: Session,
    restaurant_id: UUID,
    ingredient_id: UUID | None = None,
    include_expired: bool = False,
) -> list[IngredientBatch]:
    stmt = select(IngredientBatch).where(
        IngredientBatch.restaurant_id == restaurant_id
    )
    if ingredient_id:
        stmt = stmt.where(IngredientBatch.ingredient_id == ingredient_id)
    if not include_expired:
        now = datetime.now(UTC)
        stmt = stmt.where(
            (IngredientBatch.expiry_date.is_(None))
            | (IngredientBatch.expiry_date > now)
        )
    stmt = stmt.order_by(IngredientBatch.expiry_date.is_(None), IngredientBatch.expiry_date)
    return db.scalars(stmt).all()


def get_batch(
    db: Session, batch_id: UUID, restaurant_id: UUID
) -> IngredientBatch | None:
    batch = db.get(IngredientBatch, batch_id)
    if batch is None or batch.restaurant_id != restaurant_id:
        return None
    return batch


def create_batch(
    db: Session,
    restaurant_id: UUID,
    ingredient_id: UUID,
    batch_no: str,
    expiry_date: datetime | None,
    quantity: int,
    cost_per_unit_minor: int,
) -> IngredientBatch:
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.restaurant_id != restaurant_id:
        raise AppError(
            404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found."
        )

    existing = db.scalar(
        select(IngredientBatch).where(
            IngredientBatch.restaurant_id == restaurant_id,
            IngredientBatch.ingredient_id == ingredient_id,
            IngredientBatch.batch_no == batch_no,
        )
    )
    if existing:
        raise AppError(
            409, "BATCH_NO_EXISTS", "Batch number in use",
            "A batch with this number already exists for this ingredient.",
        )

    batch = IngredientBatch(
        restaurant_id=restaurant_id,
        ingredient_id=ingredient_id,
        batch_no=batch_no,
        expiry_date=expiry_date,
        quantity=quantity,
        cost_per_unit_minor=cost_per_unit_minor,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch(
    db: Session,
    batch_id: UUID,
    restaurant_id: UUID,
    expiry_date: datetime | None = None,
    quantity: int | None = None,
    cost_per_unit_minor: int | None = None,
) -> IngredientBatch:
    batch = get_batch(db, batch_id, restaurant_id)
    if batch is None:
        raise AppError(
            404, "BATCH_NOT_FOUND", "Not found", "Batch was not found."
        )

    if expiry_date is not None:
        batch.expiry_date = expiry_date
    if quantity is not None:
        batch.quantity = quantity
    if cost_per_unit_minor is not None:
        batch.cost_per_unit_minor = cost_per_unit_minor

    db.commit()
    db.refresh(batch)
    return batch


def fefo_deduct(
    db: Session,
    restaurant_id: UUID,
    ingredient_id: UUID,
    quantity_needed: int,
    reason: str,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    recorded_by_membership_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> list[dict]:
    """Deduct quantity from batches in FEFO (earliest-expiry-first) order.

    Returns a list of {batch_id, batch_no, quantity_deducted} dicts.
    Raises INSUFFICIENT_STOCK if total available across batches is insufficient.
    """
    # Idempotency check
    if idempotency_key:
        from sqlalchemy import select as _select
        existing = db.scalar(
            _select(StockMovement).where(
                StockMovement.idempotency_key == idempotency_key,
                StockMovement.restaurant_id == restaurant_id,
            )
        )
        if existing is not None:
            return [{"batch_id": None, "batch_no": None, "quantity_deducted": 0}]

    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None or ingredient.restaurant_id != restaurant_id:
        raise AppError(
            404, "INGREDIENT_NOT_FOUND", "Not found", "Ingredient was not found."
        )

    # Get batches ordered by expiry (FEFO), null expiry last
    now = datetime.now(UTC)
    batches = db.scalars(
        select(IngredientBatch).where(
            IngredientBatch.ingredient_id == ingredient_id,
            IngredientBatch.restaurant_id == restaurant_id,
            IngredientBatch.quantity > 0,
        ).order_by(
            IngredientBatch.expiry_date.is_(None).desc(),  # null expiry last
            IngredientBatch.expiry_date.asc(),
        )
    ).all()

    total_available = sum(b.quantity for b in batches)
    if total_available < quantity_needed:
        raise AppError(
            422, "INSUFFICIENT_STOCK", "Insufficient stock",
            f"Only {total_available} available across batches; {quantity_needed} needed.",
        )

    remaining = quantity_needed
    deductions: list[dict] = []

    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity, remaining)
        batch.quantity -= take
        remaining -= take

        new_balance = ingredient.current_stock - take
        previous_balance = ingredient.current_stock
        ingredient.current_stock = new_balance

        movement = StockMovement(
            restaurant_id=restaurant_id,
            ingredient_id=ingredient_id,
            movement_type="DEDUCT",
            quantity=take,
            previous_balance=previous_balance,
            new_balance=new_balance,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_id=batch.id,
            idempotency_key=idempotency_key,
            recorded_by_membership_id=recorded_by_membership_id,
        )
        db.add(movement)
        deductions.append({
            "batch_id": str(batch.id),
            "batch_no": batch.batch_no,
            "quantity_deducted": take,
        })

    db.flush()
    return deductions
