"""PA-01.5: Automatic billing

Revision ID: pa0010
Revises: pa0009
Create Date: 2026-11-05

Adds the pieces needed for automatic billing that are not already present in
the base platform billing schema (pa0005):

- ``platform_payment_webhook_logs``: delivery/retry ledger for outbound payment
  gateway webhooks.
- ``platform_plan_versions.grace_period_days``: per-version grace window used
  after an invoice's due date before a subscription becomes SUSPENDED.

Invoice auto-generation, renewal transitions, and inbound webhook processing
are implemented in ``app/modules/platform/services/billing.py``. The invoice,
invoice-line, payment, and payment-event tables already exist from pa0005, as
does ``platform_subscriptions.grace_ends_at``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0010"
down_revision: Union[str, Sequence[str], None] = "pa0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Outbound webhook delivery ledger (retry / audit trail).
    op.create_table(
        "platform_payment_webhook_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="sent"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_payment_webhook_logs")),
    )
    op.create_index(
        "ix_platform_payment_webhook_logs_event_type",
        "platform_payment_webhook_logs",
        ["event_type"],
        unique=False,
    )

    # Per-version grace window.
    op.add_column(
        "platform_plan_versions",
        sa.Column(
            "grace_period_days",
            sa.Integer(),
            nullable=False,
            server_default="7",
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_plan_versions", "grace_period_days")
    op.drop_index(
        "ix_platform_payment_webhook_logs_event_type",
        table_name="platform_payment_webhook_logs",
    )
    op.drop_table("platform_payment_webhook_logs")