"""add_mfa_enabled_to_users

Revision ID: pa0026
Revises: pa0025
Create Date: 2026-11-12 00:00:00.000000

Add mfa_enabled column to users table. This column is NOT NULL with a
server_default of False — all existing and new users will have mfa_enabled=False
by default, matching the platform_directory.py INSERT fix that was applied
earlier in the session.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0026"
down_revision = "pa0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "mfa_enabled")