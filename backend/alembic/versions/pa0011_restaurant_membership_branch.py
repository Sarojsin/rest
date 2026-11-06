"""pa0011_restaurant_membership_branch

Revision ID: pa0011
Revises: pa0010
Create Date: 2026-11-06 16:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0011"
down_revision = "pa0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "restaurant_membership_branch",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=op.f("fk_restaurant_membership_branch_branch_id_branches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["restaurant_memberships.id"],
            name=op.f("fk_restaurant_membership_branch_membership_id_restaurant_memberships"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restaurant_membership_branch")),
        sa.UniqueConstraint(
            "membership_id",
            "branch_id",
            name=op.f("uq_restaurant_membership_branch_membership_id_branch_id"),
        ),
    )
    op.create_index(
        op.f("ix_restaurant_membership_branch_branch_id"),
        "restaurant_membership_branch",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_restaurant_membership_branch_membership_id"),
        "restaurant_membership_branch",
        ["membership_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_restaurant_membership_branch_membership_id"),
        table_name="restaurant_membership_branch",
    )
    op.drop_index(
        op.f("ix_restaurant_membership_branch_branch_id"),
        table_name="restaurant_membership_branch",
    )
    op.drop_table("restaurant_membership_branch")
