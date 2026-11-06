"""PA-1.1: platform plan versions, features, and limits

Revision ID: pa0006
Revises: pa0005
Create Date: 2026-11-05

Adds versioned plan pricing, features, and limits. Existing platform_plans
data is preserved as version 1 for backward compatibility. Subscriptions
snapshot a specific plan version at creation time so changing a plan's price
or limits never silently alters existing subscribers' terms.

Plan versioning rule: existing subscribers remain on their plan version
until explicitly migrated. Changing a plan's price or limits only affects
new subscriptions created after the new version is published.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0006"
down_revision: Union[str, Sequence[str], None] = "pa0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # platform_plan_versions: versioned pricing and trial config per plan
    op.create_table(
        "platform_plan_versions",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("price_monthly_minor", sa.Integer(), nullable=False),
        sa.Column("price_annual_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["platform_plans.id"], name=op.f("fk_plan_versions_plan_id_platform_plans")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_plan_versions")),
        sa.UniqueConstraint(
            "plan_id", "version", name=op.f("uq_platform_plan_versions_plan_id_version")
        ),
    )
    op.create_index(
        "ix_platform_plan_versions_plan_active",
        "platform_plan_versions",
        ["plan_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_platform_plan_versions_effective",
        "platform_plan_versions",
        ["effective_from", "effective_to"],
        unique=False,
    )

    # platform_plan_features: features belonging to a plan version
    op.create_table(
        "platform_plan_features",
        sa.Column("plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_version_id"],
            ["platform_plan_versions.id"],
            name=op.f("fk_plan_features_plan_version_id_platform_plan_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_plan_features")),
        sa.UniqueConstraint(
            "plan_version_id", "feature_key", name=op.f("uq_plan_features_plan_version_feature")
        ),
    )
    op.create_index(
        "ix_plan_features_version",
        "platform_plan_features",
        ["plan_version_id"],
        unique=False,
    )

    # platform_plan_limits: usage limits belonging to a plan version
    op.create_table(
        "platform_plan_limits",
        sa.Column("plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("limit_key", sa.String(length=64), nullable=False),
        sa.Column("limit_value", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_version_id"],
            ["platform_plan_versions.id"],
            name=op.f("fk_plan_limits_plan_version_id_platform_plan_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_plan_limits")),
        sa.UniqueConstraint(
            "plan_version_id", "limit_key", name=op.f("uq_plan_limits_plan_version_limit")
        ),
    )
    op.create_index(
        "ix_plan_limits_version",
        "platform_plan_limits",
        ["plan_version_id"],
        unique=False,
    )

    # Add plan_version_id to platform_subscriptions (snapshot at subscription time)
    op.add_column(
        "platform_subscriptions",
        sa.Column("plan_version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_platform_subscriptions_plan_version_id_plan_versions",
        "platform_subscriptions",
        "platform_plan_versions",
        ["plan_version_id"],
        ["id"],
    )
    op.create_index(
        "ix_platform_subscriptions_plan_version",
        "platform_subscriptions",
        ["plan_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_subscriptions_plan_version", table_name="platform_subscriptions")
    op.drop_constraint(
        "fk_platform_subscriptions_plan_version_id_plan_versions",
        "platform_subscriptions",
        type_="foreignkey",
    )
    op.drop_column("platform_subscriptions", "plan_version_id")
    op.drop_index("ix_plan_limits_version", table_name="platform_plan_limits")
    op.drop_table("platform_plan_limits")
    op.drop_index("ix_plan_features_version", table_name="platform_plan_features")
    op.drop_table("platform_plan_features")
    op.drop_index("ix_platform_plan_versions_effective", table_name="platform_plan_versions")
    op.drop_index("ix_platform_plan_versions_plan_active", table_name="platform_plan_versions")
    op.drop_table("platform_plan_versions")
