"""phase 9: legacy drop — restaurant_id → branch_id cleanup

Revision ID: c9d8e7f6a5b4
Revises: b8e4f6a9c2d3
Create Date: 2026-11-03

Removes legacy restaurant_id columns from order_items and order_ratings
(now referenced via order.restaurant_id under the branch model), and
renames any remaining restaurant_id to branch_id where the table still
references the restaurant concept.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "b8e4f6a9c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 9 Step 1: Drop restaurant_id from order_items and order_ratings.
    # These tables no longer need a direct restaurant reference; the owning
    # order provides the restaurant context under the branch model.
    op.drop_column("order_items", "restaurant_id")
    op.drop_column("order_ratings", "restaurant_id")

    # Phase 9 Step 2: Rename any remaining restaurant_id to branch_id
    # where the table still references the restaurant concept.
    # restaurant_tables already has branch_id; restaurant_id is redundant.
    # We drop it since branch_id already serves the same purpose.
    op.drop_column("restaurant_tables", "restaurant_id")


def downgrade() -> None:
    # Reverse: restore restaurant_id on restaurant_tables
    op.add_column("restaurant_tables", sa.Column("restaurant_id", sa.Uuid(), nullable=True))

    # Restore restaurant_id on order_items and order_ratings
    op.add_column("order_items", sa.Column("restaurant_id", sa.Uuid(), nullable=True))
    op.add_column("order_ratings", sa.Column("restaurant_id", sa.Uuid(), nullable=True))