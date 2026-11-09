"""pa0022_inventory_procurement_phase3

Revision ID: pa0022
Revises: pa0021
Create Date: 2026-11-09 00:00:00.000000

Phase 3 of Inventory & Procurement:

* ingredient_batches table — batch-level tracking with expiry dates for FEFO
* stock_counts / stock_count_items tables — blind stock count workflow
* branch_id on ingredients and stock_movements — per-branch stock scope
* batch_id on stock_movements — link movements to batches
* TRANSFER_IN / TRANSFER_OUT movement types — inter-branch transfers

All columns/tables are additive — no existing data is modified or broken.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0022"
down_revision = "pa0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredient_batches ─────────────────────────────────────────────────
    op.create_table(
        "ingredient_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "ingredient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("batch_no", sa.String(64), nullable=False),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, default=0),
        sa.Column("cost_per_unit_minor", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name="fk_ingredient_batches_ingredient_id",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name="fk_ingredient_batches_restaurant_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingredient_batches"),
        sa.UniqueConstraint(
            "restaurant_id",
            "ingredient_id",
            "batch_no",
            name="uq_ingredient_batches_restaurant_ingredient_batch",
        ),
    )

    # ── stock_counts ───────────────────────────────────────────────────────
    op.create_table(
        "stock_counts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
        sa.Column("count_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="DRAFT",
        ),  # DRAFT, COMPLETED
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "recorded_by_membership_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_stock_counts_branch_id",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name="fk_stock_counts_restaurant_id",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_membership_id"],
            ["restaurant_memberships.id"],
            name="fk_stock_counts_recorded_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_counts"),
    )

    # ── stock_count_items ──────────────────────────────────────────────────
    op.create_table(
        "stock_count_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stock_count_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ingredient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("expected_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("counted_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("variance_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name="fk_stock_count_items_ingredient_id",
        ),
        sa.ForeignKeyConstraint(
            ["stock_count_id"],
            ["stock_counts.id"],
            name="fk_stock_count_items_stock_count_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_count_items"),
        sa.UniqueConstraint(
            "stock_count_id",
            "ingredient_id",
            name="uq_stock_count_items_count_ingredient",
        ),
    )

    # ── branch_id on ingredients ───────────────────────────────────────────
    op.add_column(
        "ingredients",
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
    )
    op.create_foreign_key(
        "fk_ingredients_branch_id",
        "ingredients",
        "branches",
        ["branch_id"],
        ["id"],
    )

    # ── branch_id on stock_movements ───────────────────────────────────────
    op.add_column(
        "stock_movements",
        sa.Column(
            "branch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
    )
    op.create_foreign_key(
        "fk_stock_movements_branch_id",
        "stock_movements",
        "branches",
        ["branch_id"],
        ["id"],
    )

    # ── batch_id on stock_movements ────────────────────────────────────────
    op.add_column(
        "stock_movements",
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
    )
    op.create_foreign_key(
        "fk_stock_movements_batch_id",
        "stock_movements",
        "ingredient_batches",
        ["batch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_stock_movements_batch_id", "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "batch_id")
    op.drop_constraint("fk_stock_movements_branch_id", "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "branch_id")
    op.drop_constraint("fk_ingredients_branch_id", "ingredients", type_="foreignkey")
    op.drop_column("ingredients", "branch_id")
    op.drop_table("stock_count_items")
    op.drop_table("stock_counts")
    op.drop_table("ingredient_batches")
