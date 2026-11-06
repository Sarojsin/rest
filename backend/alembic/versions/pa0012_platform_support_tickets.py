"""pa0012_platform_support_tickets

Revision ID: pa0012
Revises: pa0011
Create Date: 2026-11-06 17:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0012"
down_revision = "pa0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column(
            "assigned_to_admin_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_to_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_platform_support_tickets_assigned_to_admin_id_platform_admins"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_platform_support_tickets_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_support_tickets")),
    )
    op.create_index(
        op.f("ix_platform_support_tickets_restaurant_id"),
        "platform_support_tickets",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_platform_support_tickets_status"),
        "platform_support_tickets",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_platform_support_tickets_status"),
        table_name="platform_support_tickets",
    )
    op.drop_index(
        op.f("ix_platform_support_tickets_restaurant_id"),
        table_name="platform_support_tickets",
    )
    op.drop_table("platform_support_tickets")
