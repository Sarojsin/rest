"""PA-1.3: platform subscription trial history

Revision ID: pa0008
Revises: pa0007
Create Date: 2026-11-05

Adds platform_subscription_trial_history table to track trial history per tenant,
preventing repeated trial creation to avoid payment. Also adds trial-related
indexes and columns to platform_subscriptions for expiration tracking.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0008"
down_revision: Union[str, Sequence[str], None] = "pa0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # platform_subscription_trial_history: track all trials per tenant
    op.create_table(
        "platform_subscription_trial_history",
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("trial_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trial_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), nullable=True),
        sa.Column("converted_to_paid", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_payment_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_subscription_trial_history_restaurant_id_restaurants")
        ),
        sa.ForeignKeyConstraint(
            ["plan_version_id"],
            ["platform_plan_versions.id"],
            name=op.f("fk_platform_subscription_trial_history_plan_version_id_platform_plan_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["converted_payment_id"],
            ["platform_payments.id"],
            name=op.f("fk_platform_subscription_trial_history_converted_payment_id_platform_payments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_subscription_trial_history")),
    )
    op.create_index(
        "ix_platform_subscription_trial_history_restaurant",
        "platform_subscription_trial_history",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_subscription_trial_history_trial_end",
        "platform_subscription_trial_history",
        ["trial_end_at"],
        unique=False,
    )

    # Add trial extension tracking columns to platform_subscriptions
    op.add_column(
        "platform_subscriptions",
        sa.Column("trial_extension_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "platform_subscriptions",
        sa.Column("trial_extension_total_days", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("platform_subscriptions", "trial_extension_total_days")
    op.drop_column("platform_subscriptions", "trial_extension_count")
    op.drop_index("ix_platform_subscription_trial_history_trial_end", table_name="platform_subscription_trial_history")
    op.drop_index("ix_platform_subscription_trial_history_restaurant", table_name="platform_subscription_trial_history")
    op.drop_table("platform_subscription_trial_history")
