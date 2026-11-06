"""PA-1.2: platform tenant usage counters and usage events

Revision ID: pa0007
Revises: pa0006
Create Date: 2026-11-05

Adds per-tenant usage counters (cached counts for branches, staff by role,
tables, etc.) and an append-only usage event ledger for auditability.

These tables support atomic seat allocation so that two simultaneous
invitations cannot exceed a plan's seat limit. Counters are denormalized
cache; the usage_events table is the source of truth for reconciliation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0007"
down_revision: Union[str, Sequence[str], None] = "pa0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # platform_tenant_usage: cached usage counters per tenant
    op.create_table(
        "platform_tenant_usage",
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("branch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manager_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waiter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kitchen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cashier_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("table_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_tenant_usage_restaurant_id_restaurants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_tenant_usage")),
    )
    op.create_index(
        "ix_platform_tenant_usage_restaurant",
        "platform_tenant_usage",
        ["restaurant_id"],
        unique=True,
    )

    # platform_usage_events: append-only ledger of usage changes
    op.create_table(
        "platform_usage_events",
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("change", sa.Integer(), nullable=False),  # +1 or -1
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False, default=""),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_usage_events_restaurant_id_restaurants")
        ),
        sa.ForeignKeyConstraint(
            ["actor_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_platform_usage_events_actor_admin_id_platform_admins"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_usage_events")),
    )
    op.create_index(
        "ix_platform_usage_events_restaurant_created",
        "platform_usage_events",
        ["restaurant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_usage_events_resource",
        "platform_usage_events",
        ["resource_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_usage_events_resource", table_name="platform_usage_events")
    op.drop_index("ix_platform_usage_events_restaurant_created", table_name="platform_usage_events")
    op.drop_table("platform_usage_events")
    op.drop_index("ix_platform_tenant_usage_restaurant", table_name="platform_tenant_usage")
    op.drop_table("platform_tenant_usage")
