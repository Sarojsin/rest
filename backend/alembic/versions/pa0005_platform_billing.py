"""PA-1: platform plans, subscriptions, invoices, payments, and settings

Revision ID: pa0005
Revises: pa0004
Create Date: 2026-11-05

Adds the platform billing/tenant-management tables from plan 04 §1.4–1.12.
No seed data is inserted here; bootstrap and the development seed are
application-level and idempotent.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pa0005"
down_revision: Union[str, Sequence[str], None] = "pa0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_plans",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_monthly_minor", sa.Integer(), nullable=False),
        sa.Column("price_annual_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=False),
        sa.Column("entitlements", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_plans")),
        sa.UniqueConstraint("code", name=op.f("uq_platform_plans_code")),
    )
    op.create_index(
        "ix_platform_plans_status_sort",
        "platform_plans",
        ["status", "sort_order"],
        unique=False,
    )

    op.create_table(
        "platform_subscriptions",
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_snapshot_minor", sa.Integer(), nullable=False),
        sa.Column("currency_snapshot", sa.String(length=3), nullable=False),
        sa.Column("billing_interval_snapshot", sa.String(length=16), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["platform_plans.id"], name=op.f("fk_platform_subscriptions_plan_id_platform_plans")
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_subscriptions_restaurant_id_restaurants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_subscriptions")),
    )
    op.create_index(
        "uq_platform_subscriptions_live_tenant",
        "platform_subscriptions",
        ["restaurant_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE','SUSPENDED')"
        ),
    )
    op.create_index(
        "ix_platform_subscriptions_status",
        "platform_subscriptions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_platform_subscriptions_plan",
        "platform_subscriptions",
        ["plan_id"],
        unique=False,
    )

    op.create_table(
        "platform_subscription_events",
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["platform_subscriptions.id"],
            name=op.f("fk_platform_subscription_events_subscription_id_platform_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_subscription_events")),
    )
    op.create_index(
        "ix_platform_sub_events_subscription_created",
        "platform_subscription_events",
        ["subscription_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "platform_invoice_sequences",
        sa.Column("fiscal_year", sa.String(length=8), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fiscal_year", name=op.f("pk_platform_invoice_sequences")),
    )

    op.create_table(
        "platform_invoices",
        sa.Column("invoice_number", sa.String(length=40), nullable=False),
        sa.Column("fiscal_year", sa.String(length=8), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("discount_minor", sa.Integer(), nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.Column("refunded_amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("invoice_type", sa.String(length=32), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column("issuer_address", sa.String(length=500), nullable=True),
        sa.Column("issuer_pan", sa.String(length=32), nullable=True),
        sa.Column("issuer_vat_registered", sa.Boolean(), nullable=False),
        sa.Column("issuer_vat_number", sa.String(length=32), nullable=True),
        sa.Column("buyer_name", sa.String(length=255), nullable=True),
        sa.Column("buyer_pan", sa.String(length=32), nullable=True),
        sa.Column("buyer_address", sa.String(length=500), nullable=True),
        sa.Column("tax_treatment", sa.String(length=24), nullable=False),
        sa.Column("tax_amount_minor", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_invoices_restaurant_id_restaurants")
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["platform_subscriptions.id"],
            name=op.f("fk_platform_invoices_subscription_id_platform_subscriptions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_invoices")),
        sa.UniqueConstraint("invoice_number", name=op.f("uq_platform_invoices_invoice_number")),
    )
    op.create_index(
        "ix_platform_invoices_fy_sequence",
        "platform_invoices",
        ["fiscal_year", "sequence_number"],
        unique=True,
    )
    op.create_index(
        "ix_platform_invoices_tenant_status",
        "platform_invoices",
        ["restaurant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_platform_invoices_due", "platform_invoices", ["due_at"], unique=False
    )

    op.create_table(
        "platform_invoice_lines",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_amount_minor", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["platform_invoices.id"],
            name=op.f("fk_platform_invoice_lines_invoice_id_platform_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_invoice_lines")),
    )

    op.create_table(
        "platform_payments",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=False),
        sa.Column("normalized_reference", sa.String(length=120), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("evidence_type", sa.String(length=24), nullable=True),
        sa.Column("evidence_ref", sa.String(length=500), nullable=True),
        sa.Column("evidence_content_type", sa.String(length=100), nullable=True),
        sa.Column("evidence_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("evidence_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exception_reason", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(length=1000), nullable=True),
        sa.Column("refund_of_payment_id", sa.Uuid(), nullable=True),
        sa.Column("refund_original_reference", sa.String(length=120), nullable=True),
        sa.Column("refund_destination", sa.String(length=255), nullable=True),
        sa.Column("refund_requested_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("refund_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_reason_code", sa.String(length=32), nullable=True),
        sa.Column("refund_reason_note", sa.String(length=1000), nullable=True),
        sa.Column("refund_approved_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("refund_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_completed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("refund_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_external_reference", sa.String(length=120), nullable=True),
        sa.Column("refund_processed_outside_platform", sa.Boolean(), nullable=False),
        sa.Column("refund_rejected_reason", sa.String(length=1000), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["platform_invoices.id"], name=op.f("fk_platform_payments_invoice_id_platform_invoices")
        ),
        sa.ForeignKeyConstraint(
            ["refund_of_payment_id"],
            ["platform_payments.id"],
            name=op.f("fk_platform_payments_refund_of_payment_id_platform_payments"),
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_id"], ["restaurants.id"], name=op.f("fk_platform_payments_restaurant_id_restaurants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_payments")),
    )
    op.create_index(
        "uq_platform_payments_idempotency",
        "platform_payments",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "uq_platform_payments_reference",
        "platform_payments",
        ["normalized_reference"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('CONFIRMED','REFUND_PENDING','REFUND_APPROVED','REFUNDED')"
        ),
    )
    op.create_index(
        "ix_platform_payments_tenant_paid",
        "platform_payments",
        ["restaurant_id", "paid_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_payments_status",
        "platform_payments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "platform_payment_events",
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("restaurant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_payment_events")),
    )
    op.create_index(
        "ix_platform_payment_events_payment_created",
        "platform_payment_events",
        ["payment_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_platform_settings")),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
    op.drop_table("platform_payment_events")
    op.drop_table("platform_payments")
    op.drop_table("platform_invoice_lines")
    op.drop_table("platform_invoices")
    op.drop_table("platform_invoice_sequences")
    op.drop_table("platform_subscription_events")
    op.drop_table("platform_subscriptions")
    op.drop_table("platform_plans")
