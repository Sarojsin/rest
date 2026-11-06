"""pa0016_restaurant_cancelled_at

Revision ID: pa0016
Revises: pa0015
Create Date: 2026-11-06 21:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0016"
down_revision = "pa0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurants", "cancelled_at")
