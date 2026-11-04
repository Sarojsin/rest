"""Platform (Super Admin) identity, session, and audit tables — PA-0.3.

These tables are intentionally separate from the tenant ``users`` table
(PA-ADR-001). They are imported by ``app.modules.platform`` so that
``Base.metadata.create_all`` sees them in development and tests.

No production domain, admin identity, or credential is seeded here.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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


__all__ = [
    "PlatformAdmin",
    "PlatformAuditLog",
    "PlatformOneTimeToken",
    "PlatformRefreshToken",
]
