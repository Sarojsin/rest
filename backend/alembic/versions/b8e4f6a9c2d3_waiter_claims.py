"""phase 8: waiter claim columns on orders

Revision ID: b8e4f6a9c2d3
Revises: a7c1d2e4f5b6
Create Date: 2026-11-03

Adds the waiter-claim ownership fields per plan 08
(backend/webplan/08-waiter-request.md): claim_state + claimant/timestamps,
claim timeout, and escalation fields. Membership references are plain UUID
columns (no FK), matching the existing decision_by/created_by precedent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e4f6a9c2d3"
down_revision: Union[str, Sequence[str], None] = "a7c1d2e4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("claim_state", sa.String(length=32), nullable=False, server_default=""))
    op.add_column("orders", sa.Column("claimed_by_membership_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("claim_timeout_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("escalated_by_membership_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "escalated_at")
    op.drop_column("orders", "escalated_by_membership_id")
    op.drop_column("orders", "claim_timeout_at")
    op.drop_column("orders", "claimed_at")
    op.drop_column("orders", "claimed_by_membership_id")
    op.drop_column("orders", "claim_state")
