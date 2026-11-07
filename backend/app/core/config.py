# API settings
API_API_V1_STR = "/api/v1"

# Application title
TITLE = "Restaurant SaaS Platform"

# Description
DESCRIPTION = "Multi-tenant restaurant management platform"

# Version
VERSION = "1.0.0"

# Email settings
EMAIL_BACKEND = "smtp"  # "smtp" | "log"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "letsoit69960@gmail.com"
SMTP_PASSWORD = "fzyd xjkk zick wgrl"
SMTP_FROM = "letsoit69960@gmail.com"
SMTP_STARTTLS = False

# CORS settings
CORS_ORIGINS = ["http://127.0.0.1:5173", "http://192.168.1.5:5173"]

# Security
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Database
DATABASE_URL = "postgresql+psycopg2://postgres:tara@localhost:5432/restaurant"

# Plan 01 settings
claim_timeout_minutes: int = 10
claims_per_hour_limit: int = 60
escalations_per_hour_limit: int = 12

# Plan 08 waiter claim responsibility
waiter_claim_timeout_minutes: int = 10
waiter_claims_per_hour_limit: int = 60

# Plan 07 customer QR surface
customer_domain_base: str = "platform.com"
qr_hostname_enforcement: bool = True

# Plan 14: invitation email delivery.
email_backend: str = "smtp"  # "smtp" | "log"
smtp_host: str = "smtp.gmail.com"
smtp_port: int = 587
smtp_user: str = "letsoit69960@gmail.com"
smtp_password: str = "fzyd xjkk zick wgrl"
smtp_from: str = "letsoit69960@gmail.com"
smtp_starttls: bool = True  # "smtp" | "log" - Gmail on 587 requires STARTTLS
invitation_base_url: str = ""
invitation_ttl_hours: int = 72

# Plan 13 bootstrap data
restaurant_name: str = ""
currency_code: str = "USD"
timezone: str = "UTC"
bootstrap_owner_email: str = ""
bootstrap_owner_password: str = ""

# Platform (Super Admin) realm
platform_secret_key: str = ""
platform_mfa_key: str = ""
platform_access_token_minutes: int = 15
platform_refresh_token_minutes: int = 720  # 12 h absolute cap
platform_step_up_minutes: int = 5
platform_require_mfa: bool = True
platform_admin_origin: str = ""
platform_dev_admin_origins: str = ""
platform_api_origin: str = ""
platform_tenant_origin: str = ""
platform_cookie_secure: bool = False
platform_cookie_domain: str = ""  # must stay empty (host-only cookies)
platform_bootstrap_email: str = ""
platform_bootstrap_password: str = ""
platform_bootstrap_mfa_secret: str = ""  # dev/test only
platform_timezone: str = "UTC"
platform_login_max_attempts: int = 5
platform_login_lockout_minutes: int = 15
platform_mfa_ticket_minutes: int = 5
platform_enrollment_ticket_minutes: int = 10
platform_recovery_code_count: int = 10
platform_totp_issuer: str = "Restaurant Platform"

# Properties and methods
@property
def cors_origin_list(self) -> list[str]:
    return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@property
def platform_admin_origin_list(self) -> list[str]:
    """Origins allowed to drive the platform API.

    Production: exactly ``PLATFORM_ADMIN_ORIGIN`` (single, explicit).
    Development: that value plus ``PLATFORM_DEV_ADMIN_ORIGINS`` so the same
    machine can use localhost, 127.0.0.1, or its LAN address.
    """
    values = [self.platform_admin_origin]
    if not self.is_production:
        values.extend(self.platform_dev_admin_origins.split(","))
    seen: list[str] = []
    for value in values:
        normalized = value.strip().rstrip("/")
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen

@property
def platform_signing_key(self) -> str:
    """Key used for platform JWTs/tickets.

    Production must set ``PLATFORM_SECRET_KEY``. Development derives a
    stable, realm-separated key from ``SECRET_KEY`` so a fresh checkout can
    sign in without extra setup (tenant tokens remain signed differently).
    """
    if self.platform_secret_key:
        return self.platform_secret_key
    if self.is_production:
        raise RuntimeError("PLATFORM_SECRET_KEY is not configured")
    return hashlib.sha256(f"platform-dev-signing::{self.secret_key}".encode()).hexdigest()

@property
def platform_mfa_material(self) -> str:
    """Key material for encrypting TOTP secrets (Fernet derives the key)."""
    if self.platform_mfa_key:
        return self.platform_mfa_key
    if self.is_production:
        raise RuntimeError("PLATFORM_MFA_KEY is not configured")
    return f"platform-dev-mfa::{self.secret_key}"

@property
def allowed_origin_list(self) -> list[str]:
    """Staff origins plus the configured platform origins (deduplicated)."""
    origins = list(self.cors_origin_list)
    for origin in self.platform_admin_origin_list + [self.platform_tenant_origin]:
        normalized = origin.strip().rstrip("/")
        if normalized and normalized not in origins:
            origins.append(normalized)
    return origins

@property
def is_production(self) -> bool:
    return self.app_env == "production"

def validate_platform_config(self) -> None:
    """Fail fast when the platform realm is misconfigured in production.

    Development and tests may leave these empty; production may not.
    No production domain is invented here — the operators supply it
    (PA-ADR-011).
    """
    if not self.is_production:
        return

    errors: list[str] = []
    if not self.platform_secret_key:
        errors.append("PLATFORM_SECRET_KEY is required")
    elif self.platform_secret_key == self.secret_key:
        errors.append("PLATFORM_SECRET_KEY must differ from SECRET_KEY")
    elif len(self.platform_secret_key) < 32:
        errors.append("PLATFORM_SECRET_KEY must be at least 32 characters")
    if not self.platform_mfa_key:
        errors.append("PLATFORM_MFA_KEY is required")
    elif len(self.platform_mfa_key) < 32:
        errors.append("PLATFORM_MFA_KEY must be at least 32 characters")
    if not self.platform_admin_origin:
        errors.append("PLATFORM_ADMIN_ORIGIN is required")
    if not self.platform_api_origin:
        errors.append("PLATFORM_API_ORIGIN is required")
    if self.platform_cookie_domain:
        errors.append("PLATFORM_COOKIE_DOMAIN must be empty (host-only cookies)")
    if not self.platform_cookie_secure:
        errors.append("PLATFORM_COOKIE_SECURE must be true in production")
    if errors:
        raise RuntimeError("Invalid platform configuration: " + "; ".join(errors))

# ── Pydantic Settings Class ────────────────────────────────────────────────

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App basics
    app_env: str = "development"
    app_name: str = "Restaurant Management API"
    secret_key: str = "dev-only-change-me-not-for-production"
    # D12 (plan 01/03): Postgres-first. The default is the docker-compose
    # dev instance (docker-compose.yml: rest/rest/restaurant on host 5433).
    # SQLite is NOT part of the migration path anymore (no RLS); override
    # via DATABASE_URL only for throwaway local experiments.
    database_url: str = "postgresql://rest:rest@localhost:5433/restaurant"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    tax_rate_bps: int = 1000
    uploads_dir: str = "./data/uploads"
    max_qr_image_bytes: int = 2_097_152  # 2 MB
    # Plan 08: waiter claim responsibility expires automatically and the order
    # escalates; per-waiter hourly action caps prevent queue spam.
    claim_timeout_minutes: int = 10
    claims_per_hour_limit: int = 60
    escalations_per_hour_limit: int = 12
    # Plan 08: waiter claim responsibility expires automatically and the order
    # escalates; per-waiter hourly action caps prevent queue spam.
    waiter_claim_timeout_minutes: int = 10
    waiter_claims_per_hour_limit: int = 60
    # Plan 07 customer QR surface runs on {subdomain}.{customer_domain_base}
    # (D5). Wildcard TLS for *.{customer_domain_base} terminates at the LB;
    # public QR endpoints cross-check the Host header against it.
    customer_domain_base: str = "platform.com"
    qr_hostname_enforcement: bool = True
    # Plan 14: invitation email delivery.
    email_backend: str = "smtp"  # "smtp" | "log"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = "letsoit69960@gmail.com"
    smtp_password: str = "fzyd xjkk zick wgrl"
    smtp_from: str = "letsoit69960@gmail.com"
    smtp_starttls: bool = True  # "smtp" | "log" - Gmail on 587 requires STARTTLS
    invitation_base_url: str = ""
    invitation_ttl_hours: int = 72

    # Plan 13 bootstrap data
    restaurant_name: str = ""
    currency_code: str = "USD"
    timezone: str = "UTC"
    bootstrap_owner_email: str = ""
    bootstrap_owner_password: str = ""

    # Platform (Super Admin) realm — PA-0. Keep these empty outside local/dev.
    # A real production domain is NOT assumed here (PA-ADR-011).
    platform_secret_key: str = ""
    platform_mfa_key: str = ""
    platform_access_token_minutes: int = 15
    platform_refresh_token_minutes: int = 720  # 12 h absolute cap
    platform_step_up_minutes: int = 5
    platform_require_mfa: bool = True
    platform_admin_origin: str = ""
    platform_dev_admin_origins: str = ""
    platform_api_origin: str = ""
    platform_tenant_origin: str = ""
    platform_cookie_secure: bool = False
    platform_cookie_domain: str = ""  # must stay empty (host-only cookies)
    platform_bootstrap_email: str = ""
    platform_bootstrap_password: str = ""
    platform_bootstrap_mfa_secret: str = ""  # dev/test only
    platform_timezone: str = "UTC"
    platform_login_max_attempts: int = 5
    platform_login_lockout_minutes: int = 15
    platform_mfa_ticket_minutes: int = 5
    platform_enrollment_ticket_minutes: int = 10
    platform_recovery_code_count: int = 10
    platform_totp_issuer: str = "Restaurant Platform"

    # Model config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Computed fields and properties
    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def platform_admin_origin_list(self) -> list[str]:
        values = [self.platform_admin_origin]
        if not self.is_production:
            values.extend(self.platform_dev_admin_origins.split(","))
        seen: list[str] = []
        for value in values:
            normalized = value.strip().rstrip("/")
            if normalized and normalized not in seen:
                seen.append(normalized)
        return seen

    @property
    def platform_signing_key(self) -> str:
        if self.platform_secret_key:
            return self.platform_secret_key
        if self.is_production:
            raise RuntimeError("PLATFORM_SECRET_KEY is not configured")
        return hashlib.sha256(f"platform-dev-signing::{self.secret_key}".encode()).hexdigest()

    @property
    def platform_mfa_material(self) -> str:
        if self.platform_mfa_key:
            return self.platform_mfa_key
        if self.is_production:
            raise RuntimeError("PLATFORM_MFA_KEY is not configured")
        return f"platform-dev-mfa::{self.secret_key}"

    @property
    def allowed_origin_list(self) -> list[str]:
        origins = list(self.cors_origin_list)
        for origin in self.platform_admin_origin_list + [self.platform_tenant_origin]:
            normalized = origin.strip().rstrip("/")
            if normalized and normalized not in origins:
                origins.append(normalized)
        return origins

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_platform_config(self) -> None:
        if not self.is_production:
            return

        errors: list[str] = []
        if not self.platform_secret_key:
            errors.append("PLATFORM_SECRET_KEY is required")
        elif self.platform_secret_key == self.secret_key:
            errors.append("PLATFORM_SECRET_KEY must differ from SECRET_KEY")
        elif len(self.platform_secret_key) < 32:
            errors.append("PLATFORM_SECRET_KEY must be at least 32 characters")
        if not self.platform_mfa_key:
            errors.append("PLATFORM_MFA_KEY is required")
        elif len(self.platform_mfa_key) < 32:
            errors.append("PLATFORM_MFA_KEY must be at least 32 characters")
        if not self.platform_admin_origin:
            errors.append("PLATFORM_ADMIN_ORIGIN is required")
        if not self.platform_api_origin:
            errors.append("PLATFORM_API_ORIGIN is required")
        if self.platform_cookie_domain:
            errors.append("PLATFORM_COOKIE_DOMAIN must be empty (host-only cookies)")
        if not self.platform_cookie_secure:
            errors.append("PLATFORM_COOKIE_SECURE must be true in production")
        if errors:
            raise RuntimeError("Invalid platform configuration: " + "; ".join(errors))

# Global settings instance
settings = Settings()