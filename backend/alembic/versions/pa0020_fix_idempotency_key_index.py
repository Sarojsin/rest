"""pa0020_fix_idempotency_key_index

Revision ID: pa0020
Revises: pa0019
Create Date: 2026-11-09 00:00:00.000000

Fix the idempotency_key index on stock_movements: the previous unique index
treated NULL values as duplicates, which broke movements that don't provide
an idempotency key (e.g. PO receives). Replace with a partial unique index
that only enforces uniqueness when idempotency_key IS NOT NULL.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0020"
down_revision = "pa0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_stock_movements_idempotency_key",
        table_name="stock_movements",
    )
    op.create_index(
        "ix_stock_movements_idempotency_key",
        "stock_movements",
        ["idempotency_key"],
        unique=True,
        postgresql_where="idempotency_key IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_movements_idempotency_key",
        table_name="stock_movements",
    )
    op.create_index(
        "ix_stock_movements_idempotency_key",
        "stock_movements",
        ["idempotency_key"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
