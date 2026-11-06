"""pa0014_platform_subscription_change_history

Revision ID: pa0014
Revises: pa0013
Create Date: 2026-11-06 19:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0014"
down_revision = "pa0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_subscription_change_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "from_plan_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "to_plan_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "changed_by_admin_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("prorated_amount_minor", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_platform_subscription_change_history_changed_by_admin_id_platform_admins"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["from_plan_version_id"],
            ["platform_plan_versions.id"],
            name=op.f("fk_platform_subscription_change_history_from_plan_version_id_platform_plan_versions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_platform_subscription_change_history_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_plan_version_id"],
            ["platform_plan_versions.id"],
            name=op.f("fk_platform_subscription_change_history_to_plan_version_id_platform_plan_versions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_subscription_change_history")),
    )
    op.create_index(
        op.f("ix_platform_sub_change_history_restaurant_created"),
        "platform_subscription_change_history",
        ["restaurant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_platform_sub_change_history_restaurant_created"),
        table_name="platform_subscription_change_history",
    )
    op.drop_table("platform_subscription_change_history")
