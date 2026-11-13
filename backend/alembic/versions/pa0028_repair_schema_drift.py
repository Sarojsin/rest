"""pa0028_repair_schema_drift

Revision ID: pa0028
Revises: pa0027
Create Date: 2026-11-13 00:00:00.000000

Repair the columns that exist on the SQLAlchemy models but were never created
in the deployed database.

Background: the application used to create missing tables with
``Base.metadata.create_all`` in development. ``create_all`` never adds columns
to tables that already exist, so several tables drifted: the ORM emits INSERTs
and SELECTs that reference columns the database does not have (for example
``order_items.restaurant_id``, which broke customer QR ordering with
``psycopg.errors.UndefinedColumn``).

This migration is strictly additive:

* adds the missing columns with the same types/nullability as the models;
* backfills the tenant column on child rows from their parent row;
* adds the foreign keys and unique constraints the models declare.

No table, row or existing column is dropped or rewritten.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0028"
down_revision = "pa0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── branches ───────────────────────────────────────────────────────────
    # The live table only had id/name/code/restaurant_id/timestamps.
    op.add_column("branches", sa.Column("address", sa.String(200), nullable=True))
    op.add_column("branches", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column(
        "branches",
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "branches",
        sa.Column(
            "currency_code", sa.String(3), nullable=False, server_default="USD"
        ),
    )
    op.add_column(
        "branches",
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "branches", sa.Column("opening_hours", sa.String(100), nullable=True)
    )
    op.add_column(
        "branches",
        sa.Column(
            "settings_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "branches",
        sa.Column("owner_membership_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_branches_owner_membership_id",
        "branches",
        "restaurant_memberships",
        ["owner_membership_id"],
        ["id"],
    )

    # ── ingredients ────────────────────────────────────────────────────────
    # ``name`` is NOT NULL on the model, so add it nullable, backfill existing
    # rows (a SKU or the id suffix is the best available label), then enforce
    # the constraint.
    op.add_column("ingredients", sa.Column("name", sa.String(120), nullable=True))
    op.execute(
        """
        UPDATE ingredients
        SET name = COALESCE(
            NULLIF(sku, ''),
            'Ingredient ' || left(id::text, 8)
        )
        WHERE name IS NULL
        """
    )
    op.alter_column("ingredients", "name", nullable=False)

    op.add_column("ingredients", sa.Column("code", sa.String(32), nullable=True))
    op.add_column(
        "ingredients",
        sa.Column("unit", sa.String(32), nullable=False, server_default="pieces"),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "current_stock", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "minimum_stock", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="IN_STOCK"
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ingredients_supplier_id",
        "ingredients",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_ingredients_restaurant_name", "ingredients", ["restaurant_id", "name"]
    )
    op.create_unique_constraint(
        "uq_ingredients_restaurant_code", "ingredients", ["restaurant_id", "code"]
    )

    # ── purchase_orders ────────────────────────────────────────────────────
    op.add_column(
        "purchase_orders", sa.Column("code", sa.String(32), nullable=True)
    )
    op.execute(
        """
        UPDATE purchase_orders
        SET code = 'PO-' || left(id::text, 8)
        WHERE code IS NULL
        """
    )
    op.alter_column("purchase_orders", "code", nullable=False)

    op.add_column(
        "purchase_orders",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="DRAFT"
        ),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("total_minor", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("expected_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("received_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("purchase_orders", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "purchase_orders",
        sa.Column(
            "delivered_by_membership_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_purchase_orders_supplier_id",
        "purchase_orders",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_purchase_orders_delivered_by_membership_id",
        "purchase_orders",
        "restaurant_memberships",
        ["delivered_by_membership_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_purchase_orders_restaurant_code",
        "purchase_orders",
        ["restaurant_id", "code"],
    )

    # ── stock_movements ────────────────────────────────────────────────────
    op.add_column(
        "stock_movements",
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "stock_movements", sa.Column("movement_type", sa.String(32), nullable=True)
    )
    op.add_column(
        "stock_movements", sa.Column("quantity", sa.Integer(), nullable=True)
    )
    op.add_column(
        "stock_movements", sa.Column("new_balance", sa.Integer(), nullable=True)
    )
    op.add_column(
        "stock_movements", sa.Column("reason", sa.String(200), nullable=True)
    )
    op.add_column(
        "stock_movements",
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "stock_movements", sa.Column("reference_type", sa.String(32), nullable=True)
    )
    op.add_column(
        "stock_movements",
        sa.Column(
            "recorded_by_membership_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    # The four core columns are NOT NULL on the model. The table is empty in
    # the deployed database; enforce the constraint only after it is known
    # that no pre-existing row can violate it.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM stock_movements) THEN
                RAISE EXCEPTION
                    'stock_movements already has rows; backfill ingredient_id/'
                    'movement_type/quantity/new_balance/recorded_by_membership_id '
                    'before running pa0028';
            END IF;
        END $$;
        """
    )
    op.alter_column("stock_movements", "ingredient_id", nullable=False)
    op.alter_column("stock_movements", "movement_type", nullable=False)
    op.alter_column("stock_movements", "quantity", nullable=False)
    op.alter_column("stock_movements", "new_balance", nullable=False)
    op.alter_column("stock_movements", "recorded_by_membership_id", nullable=False)
    op.create_foreign_key(
        "fk_stock_movements_ingredient_id",
        "stock_movements",
        "ingredients",
        ["ingredient_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_stock_movements_recorded_by_membership_id",
        "stock_movements",
        "restaurant_memberships",
        ["recorded_by_membership_id"],
        ["id"],
    )

    # ── order_items ────────────────────────────────────────────────────────
    # Tenant column used by tenant-scoped queries. Backfill from the parent
    # order so existing lines stay attached to their restaurant.
    op.add_column(
        "order_items",
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE order_items
        SET restaurant_id = orders.restaurant_id
        FROM orders
        WHERE order_items.order_id = orders.id
          AND order_items.restaurant_id IS NULL
        """
    )
    op.alter_column("order_items", "restaurant_id", nullable=False)
    op.create_foreign_key(
        "fk_order_items_restaurant_id",
        "order_items",
        "restaurants",
        ["restaurant_id"],
        ["id"],
    )
    op.create_index(
        "ix_order_items_restaurant_id", "order_items", ["restaurant_id"]
    )

    # ── order_ratings ──────────────────────────────────────────────────────
    op.add_column(
        "order_ratings",
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE order_ratings
        SET restaurant_id = orders.restaurant_id
        FROM orders
        WHERE order_ratings.order_id = orders.id
          AND order_ratings.restaurant_id IS NULL
        """
    )
    op.alter_column("order_ratings", "restaurant_id", nullable=False)
    op.create_foreign_key(
        "fk_order_ratings_restaurant_id",
        "order_ratings",
        "restaurants",
        ["restaurant_id"],
        ["id"],
    )
    op.create_index(
        "ix_order_ratings_restaurant_id", "order_ratings", ["restaurant_id"]
    )


def downgrade() -> None:
    # order_ratings
    op.drop_index("ix_order_ratings_restaurant_id", table_name="order_ratings")
    op.drop_constraint(
        "fk_order_ratings_restaurant_id", "order_ratings", type_="foreignkey"
    )
    op.drop_column("order_ratings", "restaurant_id")

    # order_items
    op.drop_index("ix_order_items_restaurant_id", table_name="order_items")
    op.drop_constraint(
        "fk_order_items_restaurant_id", "order_items", type_="foreignkey"
    )
    op.drop_column("order_items", "restaurant_id")

    # stock_movements
    op.drop_constraint(
        "fk_stock_movements_recorded_by_membership_id",
        "stock_movements",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_stock_movements_ingredient_id", "stock_movements", type_="foreignkey"
    )
    for column in (
        "recorded_by_membership_id",
        "reference_type",
        "reference_id",
        "reason",
        "new_balance",
        "quantity",
        "movement_type",
        "ingredient_id",
    ):
        op.drop_column("stock_movements", column)

    # purchase_orders
    op.drop_constraint(
        "uq_purchase_orders_restaurant_code", "purchase_orders", type_="unique"
    )
    op.drop_constraint(
        "fk_purchase_orders_delivered_by_membership_id",
        "purchase_orders",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_purchase_orders_supplier_id", "purchase_orders", type_="foreignkey"
    )
    for column in (
        "delivered_by_membership_id",
        "notes",
        "received_date",
        "expected_date",
        "total_minor",
        "status",
        "supplier_id",
        "code",
    ):
        op.drop_column("purchase_orders", column)

    # ingredients
    op.drop_constraint(
        "uq_ingredients_restaurant_code", "ingredients", type_="unique"
    )
    op.drop_constraint(
        "uq_ingredients_restaurant_name", "ingredients", type_="unique"
    )
    op.drop_constraint(
        "fk_ingredients_supplier_id", "ingredients", type_="foreignkey"
    )
    for column in (
        "supplier_id",
        "status",
        "minimum_stock",
        "current_stock",
        "unit",
        "code",
        "name",
    ):
        op.drop_column("ingredients", column)

    # branches
    op.drop_constraint(
        "fk_branches_owner_membership_id", "branches", type_="foreignkey"
    )
    for column in (
        "owner_membership_id",
        "settings_json",
        "opening_hours",
        "is_active",
        "currency_code",
        "timezone",
        "phone",
        "address",
    ):
        op.drop_column("branches", column)
