"""Inventory consumption tied to the kitchen ticket lifecycle.

Deducts ingredients when a kitchen ticket enters preparation (IN_PROGRESS)
and reverses those deductions when a ticket is cancelled. All operations
are idempotent per ticket so the same transition never double-applies.

Consumption policy (Phase 2):

* Deduction fires exactly once per ticket, when the ticket first enters
  ``IN_PROGRESS`` (i.e. the first item moves to PREPARING or READY).
* Quantity deducted = ``recipe.quantity_per_order × order_item.quantity``
  per recipe line, in base-unit subunits.
* If stock would go negative, the movement is still recorded (service is
  not blocked) and the ingredient balance simply goes negative — visible
  as OUT_OF_STOCK on the ingredient list for manager review.
* Reversal fires when the ticket enters CANCELLED, restoring previously
  deducted quantities via REVERSAL movements.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.inventory.models import Ingredient, RecipeIngredient, StockMovement
from app.modules.inventory.services.inventory import _apply_stock_status
from app.modules.kitchen.models import KitchenTicket
from app.modules.operations.models import OrderItem
from app.shared.errors import AppError


def _ingredient_deduction_key(ticket_id: UUID, ingredient_id: UUID) -> str:
    return f"deduct:ticket:{ticket_id}:ing:{ingredient_id}"


def _ingredient_reversal_key(ticket_id: UUID, ingredient_id: UUID) -> str:
    return f"reversal:ticket:{ticket_id}:ing:{ingredient_id}"


def _get_order_items(
    db: Session, ticket: KitchenTicket
) -> dict[UUID, OrderItem]:
    """Map KitchenTicketItem.order_item_id → OrderItem for all items in a ticket."""
    order_item_ids = [item.order_item_id for item in ticket.items]
    if not order_item_ids:
        return {}
    rows = db.scalars(select(OrderItem).where(OrderItem.id.in_(order_item_ids))).all()
    return {row.id: row for row in rows}


def _recipe_rows_for_menu_item(
    db: Session, restaurant_id: UUID, menu_item_id: UUID
):
    return db.scalars(
        select(RecipeIngredient).where(
            RecipeIngredient.restaurant_id == restaurant_id,
            RecipeIngredient.menu_item_id == menu_item_id,
        )
    ).all()


def deduct_for_ticket(
    db: Session, ticket: KitchenTicket, membership_id: UUID
) -> dict[str, int]:
    """Deduct recipe ingredients for all items in a kitchen ticket.

    Called once when a ticket first enters IN_PROGRESS. Idempotent: if any
    ingredient already has a deduction key for this ticket, the ticket is
    considered already deducted (missing per-ingredient keys are completed
    by the per-ingredient check below).

    Returns a dict of {ingredient_id: quantity_deducted} for ingredients
    actually deducted in this call.
    """
    restaurant_id = ticket.restaurant_id
    order = ticket.order
    if order is None:
        return {}

    order_items = _get_order_items(db, ticket)
    actually_deducted: dict[str, int] = {}

    for ticket_item in ticket.items:
        order_item = order_items.get(ticket_item.order_item_id)
        if order_item is None:
            order_item = db.get(OrderItem, ticket_item.order_item_id)
        if order_item is None or order_item.menu_item_id is None:
            continue

        menu_item_id = order_item.menu_item_id
        order_qty = order_item.quantity

        for recipe_row in _recipe_rows_for_menu_item(
            db, restaurant_id, menu_item_id
        ):
            ingredient = db.get(Ingredient, recipe_row.ingredient_id)
            if ingredient is None:
                continue

            qty = recipe_row.quantity_per_order * order_qty
            if qty <= 0:
                continue

            idem_key = _ingredient_deduction_key(ticket.id, ingredient.id)

            # Skip if this ingredient was already deducted for this ticket
            existing = db.scalar(
                select(StockMovement).where(
                    StockMovement.idempotency_key == idem_key,
                    StockMovement.restaurant_id == restaurant_id,
                )
            )
            if existing is not None:
                actually_deducted[str(ingredient.id)] = existing.quantity
                continue

            new_balance = ingredient.current_stock - qty
            previous_balance = ingredient.current_stock
            ingredient.current_stock = new_balance
            _apply_stock_status(ingredient)

            db.add(
                StockMovement(
                    restaurant_id=restaurant_id,
                    ingredient_id=ingredient.id,
                    movement_type="DEDUCT",
                    quantity=qty,
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    reason=f"Kitchen prep: {order_item.item_name_snapshot}",
                    reference_type="ORDER",
                    reference_id=ticket.order_id,
                    idempotency_key=idem_key,
                    recorded_by_membership_id=membership_id,
                )
            )
            actually_deducted[str(ingredient.id)] = qty

    db.flush()
    return actually_deducted


def reverse_for_ticket(
    db: Session, ticket: KitchenTicket, membership_id: UUID
) -> dict[str, int]:
    """Reverse ingredient deductions for a cancelled kitchen ticket.

    Called when a ticket enters CANCELLED. Idempotent: if any reversal key
    already exists for this ticket+ingredient, that ingredient is skipped.

    Only reverses ingredients that were previously deducted (matched by
    deduction idempotency keys).
    """
    restaurant_id = ticket.restaurant_id
    order = ticket.order
    if order is None:
        return {}

    order_items = _get_order_items(db, ticket)
    actually_reversed: dict[str, int] = {}

    for ticket_item in ticket.items:
        order_item = order_items.get(ticket_item.order_item_id)
        if order_item is None:
            order_item = db.get(OrderItem, ticket_item.order_item_id)
        if order_item is None or order_item.menu_item_id is None:
            continue

        menu_item_id = order_item.menu_item_id
        order_qty = order_item.quantity

        for recipe_row in _recipe_rows_for_menu_item(
            db, restaurant_id, menu_item_id
        ):
            ingredient = db.get(Ingredient, recipe_row.ingredient_id)
            if ingredient is None:
                continue

            qty = recipe_row.quantity_per_order * order_qty
            if qty <= 0:
                continue

            reversal_key = _ingredient_reversal_key(ticket.id, ingredient.id)

            # Skip if already reversed
            existing = db.scalar(
                select(StockMovement).where(
                    StockMovement.idempotency_key == reversal_key,
                    StockMovement.restaurant_id == restaurant_id,
                )
            )
            if existing is not None:
                continue

            # Only reverse if this ingredient was previously deducted
            deduction_key = _ingredient_deduction_key(ticket.id, ingredient.id)
            deduction = db.scalar(
                select(StockMovement).where(
                    StockMovement.idempotency_key == deduction_key,
                    StockMovement.restaurant_id == restaurant_id,
                )
            )
            if deduction is None:
                continue

            new_balance = ingredient.current_stock + qty
            previous_balance = ingredient.current_stock
            ingredient.current_stock = new_balance
            _apply_stock_status(ingredient)

            db.add(
                StockMovement(
                    restaurant_id=restaurant_id,
                    ingredient_id=ingredient.id,
                    movement_type="REVERSAL",
                    quantity=qty,
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    reason=f"Kitchen cancel: {order_item.item_name_snapshot}",
                    reference_type="ORDER",
                    reference_id=ticket.order_id,
                    idempotency_key=reversal_key,
                    recorded_by_membership_id=membership_id,
                )
            )
            actually_reversed[str(ingredient.id)] = qty

    db.flush()
    return actually_reversed
