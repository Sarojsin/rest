"""PA-0.11: tenant lifecycle columns

Revision ID: pa0003tenantlifecycle
Revises: pa0002membershiptoken
Create Date: 2026-11-04

Adds the soft-delete/suspension metadata on ``restaurants`` (plan 04 §2.1) and
the contact/legal-name fields used by platform tenant management. No row is
destroyed; existing rows remain valid with all new columns NULL.

Status values become ACTIVE / SUSPENDED / CANCELLED. Trial stays on the
subscription row, never duplicated here (PA D-5).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0003tenantlifecycle"
down_revision: Union[str, Sequence[str], None] = "pa0002membershiptoken"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("suspended_reason", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("contact_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("contact_phone", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "restaurants",
        sa.Column("legal_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurants", "legal_name")
    op.drop_column("restaurants", "contact_phone")
    op.drop_column("restaurants", "contact_email")
    op.drop_column("restaurants", "suspended_reason")
    op.drop_column("restaurants", "suspended_at")
    op.drop_column("restaurants", "archived_at")
