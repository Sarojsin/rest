"""PA-1.4: Self-service registration for restaurant owners

Revision ID: pa0009
Revises: pa0008
Create Date: 2026-11-05

Adds self-service registration support for restaurant owners:
- Self-registered restaurant applications with pending status
- Public plan catalog (read-only, no auth required)
- Public subscription requests with trial or paid activation
- Owner invitation flow for self-registered tenants
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0009"
down_revision: Union[str, Sequence[str], None] = "pa0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Self-registration applications (pending approval or auto-approved)
    op.create_table(
        "self_service_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
        sa.Column("restaurant_name", sa.String(length=160), nullable=False),
        sa.Column("restaurant_slug", sa.String(length=80), nullable=False),
        sa.Column("owner_email", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("owner_phone", sa.String(length=40), nullable=True),
        sa.Column("plan_code", sa.String(length=40), nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=40), nullable=True),
        sa.Column("legal_name", sa.String(length=200), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_reason", sa.String(length=1000), nullable=True),
        sa.Column("invitation_token_hash", sa.String(length=64), nullable=True),
        sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invitation_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_self_service_registrations_restaurant_id_restaurants")
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_self_service_registrations_reviewed_by_admin_id_platform_admins"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_self_service_registrations")),
        sa.UniqueConstraint("restaurant_slug", name=op.f("uq_self_service_registrations_restaurant_slug")),
        sa.UniqueConstraint("owner_email", name=op.f("uq_self_service_registrations_owner_email")),
    )
    op.create_index(
        "ix_self_service_registrations_status",
        "self_service_registrations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_self_service_registrations_created_at",
        "self_service_registrations",
        ["created_at"],
        unique=False,
    )

    # Public plan catalog settings
    op.create_table(
        "public_platform_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_public_platform_settings")),
    )


def downgrade() -> None:
    op.drop_table("public_platform_settings")
    op.drop_index("ix_self_service_registrations_created_at", table_name="self_service_registrations")
    op.drop_index("ix_self_service_registrations_status", table_name="self_service_registrations")
    op.drop_table("self_service_registrations")
