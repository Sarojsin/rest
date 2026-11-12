"""add_totp_secret_to_users

Revision ID: pa0024
Revises: pa0023
Create Date: 2026-11-12 00:00:00.000000

Add totp_secret column to users table for TOTP-based two-factor authentication.
This column is nullable — existing users will have NULL, and new users
can have their TOTP secret set after onboarding.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0024"
down_revision = "pa0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "totp_secret",
            sa.String(255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_secret")