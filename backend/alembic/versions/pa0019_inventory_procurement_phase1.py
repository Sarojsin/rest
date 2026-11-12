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
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0019"
down_revision = "pa0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredients ─────────────────────────────────────────────────────────
    # Use IF NOT EXISTS for idempotency on existing deployments
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS ingredients "
            "(id UUID NOT NULL, restaurant_id UUID NOT NULL, sku VARCHAR(64), "
            "category VARCHAR(40), base_unit VARCHAR(32) NOT NULL DEFAULT 'pieces', "
            "unit_conversions JSONB, cost_per_unit_minor INTEGER NOT NULL DEFAULT 0, "
            "storage_location VARCHAR(80), created_at TIMESTAMPTZ NOT NULL, "
            "updated_at TIMESTAMPTZ NOT NULL, CONSTRAINT pk_ingredients PRIMARY KEY (id), "
            "CONSTRAINT uq_ingredients_restaurant_sku UNIQUE (restaurant_id, sku))"
        )
    )
    # Add columns if they don't already exist (idempotent)
    op.execute(sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS sku VARCHAR(64)"))
    op.execute(sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS category VARCHAR(40)"))
    op.execute(
        sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS base_unit VARCHAR(32) NOT NULL DEFAULT 'pieces'")
    )
    op.execute(sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS unit_conversions JSONB"))
    op.execute(
        sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS cost_per_unit_minor INTEGER NOT NULL DEFAULT 0")
    )
    op.execute(sa.text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS storage_location VARCHAR(80)"))

    # Unique sku per restaurant — use DO block for idempotent constraint
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT FROM pg_constraint WHERE conname = 'uq_ingredients_restaurant_sku') "
            "THEN ALTER TABLE ingredients ADD CONSTRAINT uq_ingredients_restaurant_sku "
            "UNIQUE (restaurant_id, sku); END IF; END $$;"
        )
    )

    # ── purchase_orders ─────────────────────────────────────────────────────
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS purchase_orders "
            "(id UUID NOT NULL, restaurant_id UUID NOT NULL, purchase_date TIMESTAMPTZ, "
            "bill_photo_urls TEXT[], supplier_is_walk_in BOOLEAN NOT NULL DEFAULT false, "
            "created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL, "
            "CONSTRAINT pk_purchase_orders PRIMARY KEY (id), "
            "CONSTRAINT fk_purchase_orders_restaurant_id FOREIGN KEY (restaurant_id) "
            "REFERENCES restaurants (id))"
        )
    )

    # ── stock_movements ─────────────────────────────────────────────────────
    op.execute(
        sa.text(
            "CREATE TABLE IF NOT EXISTS stock_movements "
            "(id UUID NOT NULL, restaurant_id UUID NOT NULL, idempotency_key VARCHAR(128), "
            "previous_balance INTEGER, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL, "
            "CONSTRAINT pk_stock_movements PRIMARY KEY (id), "
            "CONSTRAINT fk_stock_movements_restaurant_id FOREIGN KEY (restaurant_id) "
            "REFERENCES restaurants (id))"
        )
    )
    op.execute(
        sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_stock_movements_idempotency_key "
                "ON stock_movements (idempotency_key) WITH (nulls_not_distinct = true)")
    )

    # ── purchase_orders columns ─────────────────────────────────────────────
    op.execute(sa.text("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS purchase_date TIMESTAMPTZ"))
    op.execute(sa.text("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS bill_photo_urls TEXT[]"))
    op.execute(
        sa.text("ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS supplier_is_walk_in BOOLEAN NOT NULL DEFAULT false")
    )

    # ── stock_movements columns ─────────────────────────────────────────────
    op.execute(sa.text("ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128)"))
    op.execute(sa.text("ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS previous_balance INTEGER"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_stock_movements_idempotency_key"))
    op.execute(sa.text("ALTER TABLE stock_movements DROP COLUMN previous_balance"))
    op.execute(sa.text("ALTER TABLE stock_movements DROP COLUMN idempotency_key"))
    op.execute(sa.text("ALTER TABLE purchase_orders DROP COLUMN supplier_is_walk_in"))
    op.execute(sa.text("ALTER TABLE purchase_orders DROP COLUMN bill_photo_urls"))
    op.execute(sa.text("ALTER TABLE purchase_orders DROP COLUMN purchase_date"))
    # Drop the unique constraint and columns from ingredients
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT FROM pg_constraint WHERE conname = 'uq_ingredients_restaurant_sku') "
            "THEN ALTER TABLE ingredients DROP CONSTRAINT uq_ingredients_restaurant_sku; END IF; END $$;"
        )
    )
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN sku"))
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN category"))
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN base_unit"))
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN unit_conversions"))
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN cost_per_unit_minor"))
    op.execute(sa.text("ALTER TABLE ingredients DROP COLUMN storage_location"))
    # Drop the tables
    op.execute(sa.text("DROP TABLE IF EXISTS stock_movements"))
    op.execute(sa.text("DROP TABLE IF EXISTS purchase_orders"))
    op.execute(sa.text("DROP TABLE IF EXISTS ingredients"))