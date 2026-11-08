"""Platform (Super Admin) identity, session, and audit tables — PA-0.3.

These tables are intentionally separate from the tenant ``users`` table
(PA-ADR-001). They are imported by ``app.modules.platform`` so that
``Base.metadata.create_all`` sees them in development and tests.

No production domain, admin identity, or credential is seeded here.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _now_utc() -> datetime:
    return datetime.now(UTC)


class PlatformAdmin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_admins"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="INVITED")

    mfa_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # JSON array of hashes; raw recovery codes are shown once and never stored.
    mfa_recovery_codes_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    token_version: Mapped[int] = mapped_column(nullable=False, default=0)
    last_auth_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_platform_admins_status_role", "status", "role"),)


class PlatformRefreshToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "platform_refresh_tokens"

    admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[UUID] = mapped_column(nullable=False, default=uuid4)
    session_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_platform_refresh_admin", "admin_id"),
        Index("ix_platform_refresh_family", "family_id"),
    )


class PlatformOneTimeToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "platform_one_time_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # No FK: invitations must survive cleanup of the referenced rows.
    restaurant_id: Mapped[UUID | None] = mapped_column(nullable=True)
    platform_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="CASCADE"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index("ix_platform_one_time_tokens_email_purpose", "email", "purpose"),
    )


class PlatformAuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only platform audit trail.

    No FK to ``restaurants`` or ``platform_admins`` so archived rows survive.
    Production grants are INSERT/SELECT only.
    """

    __tablename__ = "platform_audit_logs"

    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    actor_email_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    restaurant_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index("ix_platform_audit_created", "created_at"),
        Index("ix_platform_audit_action", "action"),
        Index("ix_platform_audit_tenant", "restaurant_id"),
        Index("ix_platform_audit_actor", "actor_admin_id"),
    )


class PlatformPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform-wide products sold to tenants (plan 04 §1.4)."""

    __tablename__ = "platform_plans"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_annual_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entitlements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_platform_plans_status_sort", "status", "sort_order"),
    )


class PlatformSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One live platform subscription per tenant (plan 04 §1.5).

    Snapshots a specific plan version at creation time so changing a plan's
    price or limits never silently alters existing subscribers' terms.
    """

    __tablename__ = "platform_subscriptions"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_plans.id"), nullable=False
    )
    plan_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_plan_versions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    grace_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    price_snapshot_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency_snapshot: Mapped[str] = mapped_column(
        String(3), nullable=False, default="NPR"
    )
    billing_interval_snapshot: Mapped[str] = mapped_column(
        String(16), nullable=False, default="MONTHLY"
    )
    trial_extension_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    trial_extension_total_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)

    plan_version: Mapped["PlatformPlanVersion | None"] = relationship(  # noqa: F821
        foreign_keys=[plan_version_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "uq_platform_subscriptions_live_tenant",
            "restaurant_id",
            unique=True,
            postgresql_where=text(
                "status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE','SUSPENDED')"
            ),
        ),
        Index("ix_platform_subscriptions_status", "status"),
        Index("ix_platform_subscriptions_plan", "plan_id"),
        Index("ix_platform_subscriptions_plan_version", "plan_version_id"),
    )


class PlatformSubscriptionEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only subscription timeline (plan 04 §1.6)."""

    __tablename__ = "platform_subscription_events"

    subscription_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index(
            "ix_platform_sub_events_subscription_created",
            "subscription_id",
            "created_at",
        ),
    )


class PlatformInvoiceSequence(Base):
    """Per-fiscal-year invoice counter, locked during allocation."""

    __tablename__ = "platform_invoice_sequences"

    fiscal_year: Mapped[str] = mapped_column(String(8), primary_key=True)
    next_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        onupdate=_now_utc,
    )


class PlatformInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform subscription invoices only (never restaurant sales invoices)."""

    __tablename__ = "platform_invoices"

    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(8), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_subscriptions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN")
    subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunded_amount_minor: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PLATFORM_SUBSCRIPTION"
    )
    issuer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issuer_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issuer_pan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    issuer_vat_registered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    issuer_vat_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buyer_pan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    buyer_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_treatment: Mapped[str] = mapped_column(
        String(24), nullable=False, default="UNCONFIRMED"
    )
    tax_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    template_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_platform_invoices_fy_sequence", "fiscal_year", "sequence_number", unique=True),
        Index("ix_platform_invoices_tenant_status", "restaurant_id", "status"),
        Index("ix_platform_invoices_due", "due_at"),
    )


class PlatformInvoiceLine(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "platform_invoice_lines"

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_invoices.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="PLAN")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PlatformPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """REST/API payment or refund row. Confirmed rows are immutable."""

    __tablename__ = "platform_payments"

    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_invoices.id"), nullable=False
    )
    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="PAYMENT")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="BANK_TRANSFER")
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL")
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evidence_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    evidence_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exception_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recorded_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    confirmed_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    refund_of_payment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_payments.id"), nullable=True
    )
    refund_original_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    refund_destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_requested_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    refund_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refund_reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    refund_reason_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    refund_approved_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    refund_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refund_completed_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    refund_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refund_external_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    refund_processed_outside_platform: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    refund_rejected_reason: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("uq_platform_payments_idempotency", "idempotency_key", unique=True),
        Index(
            "uq_platform_payments_reference",
            "normalized_reference",
            unique=True,
            postgresql_where=text(
                "status IN ('CONFIRMED','REFUND_PENDING','REFUND_APPROVED','REFUNDED')"
            ),
        ),
        Index("ix_platform_payments_tenant_paid", "restaurant_id", "paid_at"),
        Index("ix_platform_payments_status", "status"),
    )


class PlatformPaymentEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only payment ledger (plan 04 §1.11)."""

    __tablename__ = "platform_payment_events"

    payment_id: Mapped[UUID] = mapped_column(nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(nullable=False)
    restaurant_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    actor_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index("ix_platform_payment_events_payment_created", "payment_id", "created_at"),
    )


class PlatformPaymentWebhookLog(UUIDPrimaryKeyMixin, Base):
    """Outbound payment-gateway webhook delivery ledger (PA-01.5).

    Tracks delivery attempts and retries for webhooks the platform sends to a
    payment provider. Append-mostly; ``retry_count`` and delivery timestamps
    are updated as delivery progresses.
    """

    __tablename__ = "platform_payment_webhook_logs"

    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="sent", server_default="sent"
    )
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index("ix_platform_payment_webhook_logs_event_type", "event_type"),
    )


class PlatformSetting(Base):
    """Allowlisted platform configuration key/value store (plan 04 §1.12)."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value_json: Mapped[dict | list | str | int | bool | None] = mapped_column(
        JSON, nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        onupdate=_now_utc,
    )


class PlatformPlanVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned pricing and trial config for a plan.

    Existing subscribers remain on their plan version until explicitly
    migrated. Changing a plan's price or limits only affects new
    subscriptions created after the new version is published.
    """

    __tablename__ = "platform_plan_versions"

    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_plans.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    price_monthly_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    price_annual_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Grace window (days) after an invoice due date before suspension (PA-01.5).
    grace_period_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7, server_default="7"
    )

    __table_args__ = (
        Index("ix_platform_plan_versions_plan_active", "plan_id", "is_active"),
        Index("ix_platform_plan_versions_effective", "effective_from", "effective_to"),
    )


class PlatformPlanFeature(UUIDPrimaryKeyMixin, Base):
    """A feature belonging to a plan version."""

    __tablename__ = "platform_plan_features"

    plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_plan_versions.id", ondelete="CASCADE"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_plan_features_version", "plan_version_id"),
    )


class PlatformPlanLimit(UUIDPrimaryKeyMixin, Base):
    """A usage limit belonging to a plan version."""

    __tablename__ = "platform_plan_limits"

    plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_plan_versions.id", ondelete="CASCADE"), nullable=False
    )
    limit_key: Mapped[str] = mapped_column(String(64), nullable=False)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_plan_limits_version", "plan_version_id"),
    )


class PlatformTenantUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cached usage counters per tenant.

    Denormalized cache for fast limit checks. platform_usage_events is
    the source of truth for reconciliation.
    """

    __tablename__ = "platform_tenant_usage"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    branch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manager_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waiter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kitchen_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cashier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    table_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_platform_tenant_usage_restaurant", "restaurant_id", unique=True),
    )


class PlatformUsageEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only ledger of usage changes.

    Source of truth for reconciling platform_tenant_usage counters. Append-only:
    rows are never updated, so there is no ``updated_at`` column.
    """

    __tablename__ = "platform_usage_events"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    change: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1
    actor_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_platform_usage_events_restaurant_created", "restaurant_id", "created_at"),
        Index("ix_platform_usage_events_resource", "resource_type"),
    )


class PlatformSubscriptionTrialHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Track all trials per tenant to prevent repeated trial creation."""

    __tablename__ = "platform_subscription_trial_history"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False
    )
    trial_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    trial_end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    plan_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_plan_versions.id", ondelete="SET NULL"), nullable=True
    )
    converted_to_paid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    converted_payment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_payments.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    __table_args__ = (
        Index("ix_platform_subscription_trial_history_restaurant", "restaurant_id"),
        Index("ix_platform_subscription_trial_history_trial_end", "trial_end_at"),
    )


class SelfServiceRegistration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Restaurant-owner self-service registration (PA-01.4).

    Captures an inbound registration request before an operator approves or
    rejects it. On approval a restaurant + subscription are provisioned and an
    invitation token is issued to the owner.
    """

    __tablename__ = "self_service_registrations"
    __table_args__ = (
        UniqueConstraint(
            "restaurant_slug", name="uq_self_service_registrations_restaurant_slug"
        ),
        UniqueConstraint(
            "owner_email", name="uq_self_service_registrations_owner_email"
        ),
    )

    restaurant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True
    )
    restaurant_name: Mapped[str] = mapped_column(String(160), nullable=False)
    restaurant_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plan_code: Mapped[str] = mapped_column(String(40), nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="NPR")
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    invitation_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invitation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invitation_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PlatformSupportTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Customer support ticket linked to a restaurant tenant."""

    __tablename__ = "platform_support_tickets"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open"
    )  # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # low, medium, high, urgent
    assigned_to_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_platform_support_tickets_restaurant", "restaurant_id"),
        Index("ix_platform_support_tickets_status", "status"),
    )


class PlatformSubscriptionChangeHistory(UUIDPrimaryKeyMixin, Base):
    """Audit trail for subscription plan changes (Plan 12).

    Records every plan change: which tenant, from which plan version,
    to which plan version, who changed it, and why.
    """

    __tablename__ = "platform_subscription_change_history"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_plan_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_plan_versions.id", ondelete="SET NULL"), nullable=True
    )
    to_plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_plan_versions.id", ondelete="SET NULL"), nullable=False
    )
    changed_by_admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    prorated_amount_minor: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Prorated amount charged/credited
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )

    __table_args__ = (
        Index(
            "ix_platform_sub_change_history_restaurant", "restaurant_id", "created_at"
        ),
    )


class PlatformExportJob(UUIDPrimaryKeyMixin, Base):
    """Async export job for tenant data (Plan 13).

    Tracks data export jobs: pending -> completed/failed, with download URL
    when ready. Jobs expire after a configurable TTL.
    """

    __tablename__ = "platform_export_jobs"

    restaurant_id: Mapped[UUID] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending"
    )  # pending, completed, failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    download_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Kept nullable so deleting a platform admin does not fail on historical
    # export jobs (the FK uses ON DELETE SET NULL).
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_platform_export_jobs_status", "status"),
    )


__all__ = [
    "PlatformAdmin",
    "PlatformAuditLog",
    "PlatformExportJob",
    "PlatformInvoice",
    "PlatformInvoiceLine",
    "PlatformInvoiceSequence",
    "PlatformOneTimeToken",
    "PlatformPayment",
    "PlatformPaymentEvent",
    "PlatformPaymentWebhookLog",
    "PlatformPlan",
    "PlatformPlanFeature",
    "PlatformPlanLimit",
    "PlatformPlanVersion",
    "PlatformRefreshToken",
    "PlatformSetting",
    "PlatformSubscription",
    "PlatformSubscriptionEvent",
    "PlatformSubscriptionTrialHistory",
    "PlatformTenantUsage",
    "PlatformUsageEvent",
    "SelfServiceRegistration",
    "PlatformSupportTicket",
    "PlatformSubscriptionChangeHistory",
]

