"""add_recovery_codes_hash_to_users

Revision ID: pa0025
Revises: pa0024
Create Date: 2026-11-12 00:00:00.000000

Add recovery_codes_hash column to users table for TOTP-based two-factor
authentication recovery codes. This column is nullable — existing users will
have NULL, and new users can have their recovery codes set after onboarding.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0025"
down_revision = "pa0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "recovery_codes_hash",
            sa.String(255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "recovery_codes_hash")