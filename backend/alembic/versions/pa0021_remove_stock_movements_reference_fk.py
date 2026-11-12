"""pa0021_remove_stock_movements_reference_fk

Revision ID: pa0021
Revises: pa0020
Create Date: 2026-11-09 00:00:00.000000

Remove the foreign key constraint on stock_movements.reference_id to
purchase_orders. The reference_type column already disambiguates what the
reference_id points to (PO, ORDER, ADJUST, MANUAL), so a hard FK to only
purchase_orders prevents inventory consumption from referencing orders.

This is a data-model correction: reference_id was always intended to be
polymorphic (per reference_type), not strictly purchase_orders.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "pa0021"
down_revision = "pa0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_stock_movements_reference_id_purchase_orders",
        "stock_movements",
        type_="foreignkey",
        if_exists=True,
    )


def downgrade() -> None:
    op.create_foreign_key(
        "fk_stock_movements_reference_id_purchase_orders",
        "stock_movements",
        "purchase_orders",
        ["reference_id"],
        ["id"],
    )
