"""pa0015_export_jobs

Revision ID: pa0015
Revises: pa0014
Create Date: 2026-11-06 20:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "pa0015"
down_revision = "pa0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("download_url", sa.String(length=500), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"],
            ["restaurants.id"],
            name=op.f("fk_platform_export_jobs_restaurant_id_restaurants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_platform_export_jobs_created_by_admin_id_platform_admins"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_export_jobs")),
    )
    op.create_index(
        op.f("ix_platform_export_jobs_restaurant_id"),
        "platform_export_jobs",
        ["restaurant_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_platform_export_jobs_status"),
        "platform_export_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_export_jobs_status"), table_name="platform_export_jobs")
    op.drop_index(op.f("ix_platform_export_jobs_restaurant_id"), table_name="platform_export_jobs")
    op.drop_table("platform_export_jobs")
