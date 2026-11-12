"""add_mfa_enrolled_at_to_users

Revision ID: pa0027
Revises: pa0026
Create Date: 2026-11-12 00:00:00.000000

Add mfa_enrolled_at column to users table. This column is NULLABLE — a user
who has not yet enrolled in MFA will have NULL; after enrollment it stores
the timestamp of when MFA was activated.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pa0027"
down_revision = "pa0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "mfa_enrolled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "mfa_enrolled_at")