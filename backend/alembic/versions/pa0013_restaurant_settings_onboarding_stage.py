"""pa0013_restaurant_settings_onboarding_stage

Revision ID: pa0013
Revises: pa0012
Create Date: 2026-11-06 18:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0013"
down_revision = "pa0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_settings",
        sa.Column("onboarding_stage", sa.String(length=32), nullable=False, server_default="registered"),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurant_settings", "onboarding_completed_at")
    op.drop_column("restaurant_settings", "onboarding_stage")
