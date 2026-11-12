"""pa0023_fcm_device_tokens

Revision ID: pa0023
Revises: pa0022
Create Date: 2026-11-11 00:00:00.000000

Adds the device_tokens table for Firebase Cloud Messaging (FCM) push
notifications. One row per (user, token) pair; indexed by restaurant for
broadcast delivery. All columns are additive — no existing data changes.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0023"
down_revision = "pa0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_device_tokens_restaurant_id_restaurants"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_device_tokens_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_device_tokens")),
        sa.UniqueConstraint(
            "user_id", "token", name=op.f("uq_device_tokens_user_token")
        ),
        sa.UniqueConstraint(
            "restaurant_id",
            "token",
            name=op.f("uq_device_tokens_restaurant_token"),
        ),
    )
    op.create_index(
        op.f("ix_device_tokens_restaurant_id"),
        "device_tokens",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_device_tokens_user_id"),
        "device_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_device_tokens_user_id"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_restaurant_id"), table_name="device_tokens")
    op.drop_table("device_tokens")
