"""PA-0.3: platform identity, session, invite, and audit tables

Revision ID: pa0001platformidentity
Revises: c9d8e7f6a5b4
Create Date: 2026-11-04

Creates the four platform-realm tables required before any platform route
exists (plan 04 §1.1–1.3). Billing, subscription, and invoice tables arrive in
PA-1 with their own revision.

These tables are separate from the tenant identity tables (PA-ADR-001). No
seed data is inserted here; bootstrap is application-level and idempotent.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0001platformidentity"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_admins",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mfa_recovery_codes_hash", sa.Text(), nullable=True),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("last_auth_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_admins")),
        sa.UniqueConstraint("email", name=op.f("uq_platform_admins_email")),
    )
    op.create_index(
        "ix_platform_admins_status_role",
        "platform_admins",
        ["status", "role"],
        unique=False,
    )

    op.create_table(
        "platform_refresh_tokens",
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("session_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_refresh_tokens")),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["platform_admins.id"],
            name=op.f("fk_platform_refresh_tokens_admin_id_platform_admins"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "token_hash", name=op.f("uq_platform_refresh_tokens_token_hash")
        ),
    )
    op.create_index(
        "ix_platform_refresh_admin",
        "platform_refresh_tokens",
        ["admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_refresh_family",
        "platform_refresh_tokens",
        ["family_id"],
        unique=False,
    )

    op.create_table(
        "platform_one_time_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
        sa.Column("platform_admin_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_one_time_tokens")),
        sa.ForeignKeyConstraint(
            ["platform_admin_id"],
            ["platform_admins.id"],
            name=op.f(
                "fk_platform_one_time_tokens_platform_admin_id_platform_admins"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "token_hash", name=op.f("uq_platform_one_time_tokens_token_hash")
        ),
    )
    op.create_index(
        "ix_platform_one_time_tokens_email_purpose",
        "platform_one_time_tokens",
        ["email", "purpose"],
        unique=False,
    )

    op.create_table(
        "platform_audit_logs",
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email_snapshot", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_audit_logs")),
    )
    op.create_index(
        "ix_platform_audit_created",
        "platform_audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_audit_action",
        "platform_audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_platform_audit_tenant",
        "platform_audit_logs",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_platform_audit_actor",
        "platform_audit_logs",
        ["actor_admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_audit_actor", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_tenant", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_action", table_name="platform_audit_logs")
    op.drop_index("ix_platform_audit_created", table_name="platform_audit_logs")
    op.drop_table("platform_audit_logs")

    op.drop_index(
        "ix_platform_one_time_tokens_email_purpose",
        table_name="platform_one_time_tokens",
    )
    op.drop_table("platform_one_time_tokens")

    op.drop_index("ix_platform_refresh_family", table_name="platform_refresh_tokens")
    op.drop_index("ix_platform_refresh_admin", table_name="platform_refresh_tokens")
    op.drop_table("platform_refresh_tokens")

    op.drop_index("ix_platform_admins_status_role", table_name="platform_admins")
    op.drop_table("platform_admins")
