"""Allowlisted platform settings (plan 04 §1.12 / plan 05 §10)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.platform.models import PlatformSetting
from app.shared.errors import AppError

# key -> (type, default, description)
SETTING_DEFINITIONS: dict[str, tuple[type, Any, str]] = {
    "platform.company_name": (str, "Restaurant Platform", "Platform company name"),
    "platform.support_email": (str, "support@example.com", "Support contact email"),
    "platform.default_currency": (str, "NPR", "Default billing currency (ISO code)"),
    "platform.invoice_prefix": (str, "INV", "Invoice number prefix"),
    "platform.fiscal_year_start_month": (int, 7, "Fiscal year start month (1-12)"),
    "platform.default_trial_days": (int, 14, "Default trial length in days"),
    "platform.billing_grace_days": (int, 7, "Grace period after a missed payment"),
    "platform.trial_extension_max_days_per_action": (int, 30, "Trial extension per action"),
    "platform.trial_extension_max_days_total": (int, 60, "Total trial extension allowed"),
    "platform.export_retention_days": (int, 30, "Tenant export retention"),
    "platform.export_max_rows": (int, 500000, "Tenant export row cap"),
    "platform.invoice.issuer_name": (str, "", "Legal name printed on invoices"),
    "platform.invoice.issuer_address": (str, "", "Issuer address printed on invoices"),
    "platform.invoice.issuer_pan": (str, "", "Issuer PAN (tax sign-off required)"),
    "platform.invoice.issuer_vat_registered": (bool, False, "Issuer VAT registration"),
    "platform.invoice.issuer_vat_number": (str, "", "Issuer VAT number"),
    "platform.invoice.default_template_version": (str, "v1-unapproved", "Invoice template"),
    "platform.invoice.tax_treatment": (str, "UNCONFIRMED", "Tax treatment label"),
    "platform.payment.instructions_text": (str, "", "Payment instructions sent to owners"),
    "platform.payment.qr_image_ref": (str, "", "Company payment QR asset path"),
    "platform.evidence.max_size_bytes": (int, 5 * 1024 * 1024, "Payment evidence size cap"),
    "platform.evidence.allowed_content_types": (
        list,
        ["image/jpeg", "image/png", "application/pdf"],
        "Allowed payment evidence types",
    ),
    "platform.evidence.signed_url_ttl_seconds": (int, 300, "Evidence signed-URL lifetime"),
    "platform.session_absolute_hours": (int, 12, "Platform session absolute cap"),
    "platform.step_up_minutes": (int, 5, "Step-up validity window"),
    "platform.login_max_attempts": (int, 5, "Login attempts before lockout"),
    "platform.login_lockout_minutes": (int, 15, "Login lockout duration"),
    "platform.self_service_enabled": (bool, True, "Enable self-service registration"),
}

INT_BOUNDS: dict[str, tuple[int, int]] = {
    "platform.fiscal_year_start_month": (1, 12),
    "platform.default_trial_days": (0, 365),
    "platform.billing_grace_days": (0, 365),
    "platform.trial_extension_max_days_per_action": (1, 365),
    "platform.trial_extension_max_days_total": (1, 730),
    "platform.export_retention_days": (1, 365),
    "platform.export_max_rows": (1, 5_000_000),
    "platform.evidence.max_size_bytes": (1024, 50 * 1024 * 1024),
    "platform.evidence.signed_url_ttl_seconds": (30, 3600),
    "platform.session_absolute_hours": (1, 72),
    "platform.step_up_minutes": (1, 60),
    "platform.login_max_attempts": (1, 20),
    "platform.login_lockout_minutes": (1, 1440),
}


def defaults() -> dict[str, Any]:
    return {key: meta[1] for key, meta in SETTING_DEFINITIONS.items()}


def current_settings(db: Session) -> dict[str, Any]:
    values = defaults()
    for row in db.query(PlatformSetting).all():
        if row.key in values:
            values[row.key] = row.value_json
    return values


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(PlatformSetting, key)
    if row is not None:
        return row.value_json
    if key in SETTING_DEFINITIONS:
        return SETTING_DEFINITIONS[key][1]
    return default


def _validate(key: str, value: Any) -> Any:
    if key not in SETTING_DEFINITIONS:
        raise AppError(422, "UNKNOWN_SETTING", "Invalid setting", f"Unknown setting: {key}")
    expected, _, _ = SETTING_DEFINITIONS[key]
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise AppError(422, "INVALID_SETTING", "Invalid setting", f"{key} must be an integer.")
        low, high = INT_BOUNDS.get(key, (0, 2**31 - 1))
        if not low <= value <= high:
            raise AppError(
                422, "INVALID_SETTING", "Invalid setting", f"{key} must be between {low} and {high}."
            )
        return value
    if expected is bool:
        if not isinstance(value, bool):
            raise AppError(422, "INVALID_SETTING", "Invalid setting", f"{key} must be true or false.")
        return value
    if expected is str:
        if not isinstance(value, str):
            raise AppError(422, "INVALID_SETTING", "Invalid setting", f"{key} must be text.")
        return value.strip()
    if expected is list:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise AppError(422, "INVALID_SETTING", "Invalid setting", f"{key} must be a list of text values.")
        return value
    return value


def update_settings(db: Session, changes: dict[str, Any], *, admin_id) -> tuple[dict, dict]:
    before = current_settings(db)
    for key, value in changes.items():
        normalized = _validate(key, value)
        row = db.get(PlatformSetting, key)
        if row is None:
            row = PlatformSetting(
                key=key,
                value_json=normalized,
                description=SETTING_DEFINITIONS[key][2],
                updated_by_admin_id=admin_id,
                updated_at=datetime.now(UTC),
            )
            db.add(row)
        else:
            row.value_json = normalized
            row.updated_by_admin_id = admin_id
            row.updated_at = datetime.now(UTC)
    db.flush()
    after = current_settings(db)
    return before, after


def ensure_defaults(db: Session) -> None:
    """Persist defaults for keys that do not exist yet (idempotent)."""
    for key, (_, default, description) in SETTING_DEFINITIONS.items():
        if db.get(PlatformSetting, key) is None:
            db.add(
                PlatformSetting(
                    key=key,
                    value_json=default,
                    description=description,
                    updated_at=datetime.now(UTC),
                )
            )
    db.commit()
