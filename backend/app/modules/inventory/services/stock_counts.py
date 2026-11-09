"""Stock count (blind count) workflow.

A stock count captures expected vs counted quantities per ingredient.
When completed, variance adjustments are recorded as ADJUST movements,
so every stock change leaves an audit trail.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.inventory.models import Ingredient, StockCount, StockCountItem, StockMovement
from app.modules.inventory.services.inventory import _apply_stock_status
from app.shared.errors import AppError


def list_stock_counts(
    db: Session,
    restaurant_id: UUID,
    branch_id: UUID | None = None,
    status: str | None = None,
) -> list[StockCount]:
    stmt = select(StockCount).where(StockCount.restaurant_id == restaurant_id)
    if branch_id:
        stmt = stmt.where(StockCount.branch_id == branch_id)
    if status:
        stmt = stmt.where(StockCount.status == status)
    stmt = stmt.order_by(StockCount.count_date.desc())
    return db.scalars(stmt).all()


def get_stock_count(
    db: Session, count_id: UUID, restaurant_id: UUID
) -> StockCount | None:
    count = db.scalars(
        select(StockCount)
        .options(selectinload(StockCount.items))
        .where(
            StockCount.id == count_id,
            StockCount.restaurant_id == restaurant_id,
        )
    ).first()
    return count


def create_stock_count(
    db: Session,
    restaurant_id: UUID,
    actor_membership_id: UUID,
    branch_id: UUID | None = None,
    count_date: datetime | None = None,
    notes: str | None = None,
    items: list[dict] | None = None,
) -> StockCount:
    if count_date is None:
        count_date = datetime.now(UTC)

    count = StockCount(
        restaurant_id=restaurant_id,
        branch_id=branch_id,
        count_date=count_date,
        status="DRAFT",
        notes=notes,
        recorded_by_membership_id=actor_membership_id,
    )
    db.add(count)
    db.flush()

    if items:
        for item in items:
            ingredient = db.get(Ingredient, item["ingredient_id"])
            if ingredient is None or ingredient.restaurant_id != restaurant_id:
                raise AppError(
                    404, "INGREDIENT_NOT_FOUND", "Not found",
                    f"Ingredient {item['ingredient_id']} not found.",
                )
            count_item = StockCountItem(
                stock_count_id=count.id,
                ingredient_id=ingredient.id,
                expected_qty=item.get("expected_qty", ingredient.current_stock),
                counted_qty=item["counted_qty"],
                variance_qty=item["counted_qty"] - item.get("expected_qty", ingredient.current_stock),
            )
            db.add(count_item)

    db.commit()
    # Eagerly load items so the response can serialize them
    db.refresh(count, attribute_names=["items"])
    return count


def complete_stock_count(
    db: Session,
    count_id: UUID,
    restaurant_id: UUID,
    actor_membership_id: UUID,
) -> StockCount:
    """Complete a stock count, recording ADJUST movements for all variances.

    Each variance (counted_qty - expected_qty) becomes an ADJUST movement
    on the ingredient, updating current_stock. This ensures the ledger is
    always the source of truth.
    """
    count = get_stock_count(db, count_id, restaurant_id)
    if count is None:
        raise AppError(
            404, "STOCK_COUNT_NOT_FOUND", "Not found", "Stock count was not found."
        )
    if count.status == "COMPLETED":
        raise AppError(
            409, "STOCK_COUNT_COMPLETED", "Stock count already completed",
            "This stock count has already been completed.",
        )

    now = datetime.now(UTC)

    for item in count.items:
        ingredient = db.get(Ingredient, item.ingredient_id)
        if ingredient is None:
            continue

        variance = item.counted_qty - item.expected_qty
        if variance == 0:
            continue

        previous_balance = ingredient.current_stock
        ingredient.current_stock = item.counted_qty
        _apply_stock_status(ingredient)

        movement = StockMovement(
            restaurant_id=restaurant_id,
            ingredient_id=ingredient.id,
            movement_type="ADJUST",
            quantity=variance,
            previous_balance=previous_balance,
            new_balance=item.counted_qty,
            reason=f"Stock count variance: {count.count_date.date()}",
            reference_type="COUNT",
            reference_id=count.id,
            branch_id=count.branch_id,
            idempotency_key=f"count:{count.id}:ing:{ingredient.id}",
            recorded_by_membership_id=actor_membership_id,
        )
        db.add(movement)

    count.status = "COMPLETED"
    db.commit()
    db.refresh(count)
    return count
