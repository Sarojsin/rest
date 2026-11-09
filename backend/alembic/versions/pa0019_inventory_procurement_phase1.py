"""pa0019_inventory_procurement_phase1

Revision ID: pa0019
Revises: pa0018
Create Date: 2026-11-09 00:00:00.000000

Phase 1 of Inventory & Procurement:

* ingredients: sku (unique per restaurant), category, base_unit, unit_conversions
  (JSON), cost_per_unit_minor, storage_location
* purchase_orders: purchase_date, bill_photo_urls (text array),
  supplier_is_walk_in
* stock_movements: idempotency_key (indexed), previous_balance

All columns are additive with sensible defaults — no existing data is
modified or broken.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0019"
down_revision = "pa0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredients ─────────────────────────────────────────────────────────
    op.add_column("ingredients", sa.Column("sku", sa.String(64), nullable=True))
    op.add_column("ingredients", sa.Column("category", sa.String(40), nullable=True))
    op.add_column(
        "ingredients",
        sa.Column("base_unit", sa.String(32), nullable=False, server_default="pieces"),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "unit_conversions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column("cost_per_unit_minor", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ingredients", sa.Column("storage_location", sa.String(80), nullable=True))

    # Unique sku per restaurant.
    op.create_unique_constraint(
        "uq_ingredients_restaurant_sku",
        "ingredients",
        ["restaurant_id", "sku"],
    )

    # ── purchase_orders ─────────────────────────────────────────────────────
    op.add_column(
        "purchase_orders",
        sa.Column(
            "purchase_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "purchase_orders",
        sa.Column(
            "bill_photo_urls",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "purchase_orders",
        sa.Column(
            "supplier_is_walk_in",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ── stock_movements ─────────────────────────────────────────────────────
    op.add_column(
        "stock_movements",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
    )
    op.add_column(
        "stock_movements",
        sa.Column("previous_balance", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_stock_movements_idempotency_key",
        "stock_movements",
        ["idempotency_key"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_movements_idempotency_key",
        table_name="stock_movements",
    )
    op.drop_column("stock_movements", "previous_balance")
    op.drop_column("stock_movements", "idempotency_key")
    op.drop_column("purchase_orders", "supplier_is_walk_in")
    op.drop_column("purchase_orders", "bill_photo_urls")
    op.drop_column("purchase_orders", "purchase_date")
    op.drop_constraint(
        "uq_ingredients_restaurant_sku",
        "ingredients",
        type_="unique",
    )
    op.drop_column("ingredients", "storage_location")
    op.drop_column("ingredients", "cost_per_unit_minor")
    op.drop_column("ingredients", "unit_conversions")
    op.drop_column("ingredients", "base_unit")
    op.drop_column("ingredients", "category")
    op.drop_column("ingredients", "sku")
