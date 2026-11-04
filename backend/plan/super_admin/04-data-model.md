# 04 — Data Model, Migrations, and Seed Data

**Conventions (inherited):** UUID primary keys, timezone-aware timestamps (`TimestampMixin`), integer minor units for money, ISO currency codes, `snake_case`, no cross-module ORM relationships. Platform tables live in `app/modules/platform/models.py` and are imported by `app/modules/__init__.py` so `create_all` sees them.

**Scope note:** “tenant” in product language maps to the existing `restaurants` row. Platform tables use `restaurant_id` for consistency with the rest of the schema.

---

## 1. New tables (MVP)

### 1.1 `platform_admins`

Separate identity store for platform staff. Intentionally **not** linked to `users` (see PA-ADR-001).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `email` | varchar(255) | unique, stored lowercase |
| `password_hash` | varchar(255) | Argon2 |
| `display_name` | varchar(120) | |
| `role` | varchar(32) | `support`, `billing`, `ops`, `superadmin` |
| `status` | varchar(32) | `INVITED`, `ACTIVE`, `DISABLED` |
| `mfa_secret_encrypted` | text | nullable until enrollment |
| `mfa_enabled_at` | timestamptz | nullable |
| `mfa_recovery_codes_hash` | text | JSON array of hashes, nullable |
| `token_version` | integer | default 0, not null |
| `last_auth_at` | timestamptz | drives step-up (`auth_time` claim) |
| `last_login_at` | timestamptz | nullable |
| `password_changed_at` | timestamptz | nullable |
| `failed_login_count` | integer | default 0 |
| `locked_until` | timestamptz | nullable |
| `disabled_reason` | varchar(1000) | nullable |
| `created_by_admin_id` | UUID | nullable; set by invite flow |
| `created_at`, `updated_at` | timestamptz | |

Indexes: `uq_platform_admins_email`, `ix_platform_admins_status_role`.

Invariants:
- `status=ACTIVE` requires `mfa_enabled_at IS NOT NULL` after first login.
- At least two `ACTIVE` `superadmin` rows are required before commercial launch (enforced operationally; the API rejects dropping to zero).

### 1.2 `platform_refresh_tokens`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `admin_id` | UUID FK → `platform_admins.id` `ON DELETE CASCADE` | |
| `token_hash` | varchar(64) | SHA-256 hex, unique |
| `family_id` | UUID | rotation family |
| `session_started_at` | timestamptz | absolute 12-hour cap is measured from this |
| `expires_at` | timestamptz | |
| `rotated_at` | timestamptz | nullable; set when exchanged |
| `replaced_by_id` | UUID | nullable; next token in the family |
| `revoked_at` | timestamptz | nullable |
| `revoked_reason` | varchar(64) | nullable (`LOGOUT`, `REUSE_DETECTED`, `ADMIN_DISABLED`, `PASSWORD_CHANGED`, `SIGN_OUT_ALL`) |
| `created_at` | timestamptz | |
| `ip` | varchar(64) | nullable |
| `user_agent` | varchar(255) | nullable |

Indexes: `ix_platform_refresh_admin`, `ix_platform_refresh_family`.

### 1.2a `platform_one_time_tokens`

Supports owner invitations, platform-admin invitations, and admin password resets. Only the hash is stored; the raw token is shown once.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `token_hash` | varchar(64) | SHA-256 hex, unique |
| `purpose` | varchar(32) | `OWNER_INVITE`, `ADMIN_INVITE`, `ADMIN_PASSWORD_RESET` |
| `email` | varchar(255) | target email |
| `restaurant_id` | UUID | nullable; no FK, so the token can be cleaned up independently |
| `platform_admin_id` | UUID FK → `platform_admins.id` `ON DELETE CASCADE` | nullable |
| `expires_at` | timestamptz | |
| `used_at` | timestamptz | nullable; single use |
| `created_by_admin_id` | UUID | nullable |
| `created_at` | timestamptz | |

Indexes: `uq_platform_one_time_tokens_hash`, `ix_platform_one_time_tokens_email_purpose`.

### 1.3 `platform_audit_logs`

Append-only. No FK to `restaurants` or `platform_admins`, so logs survive archival.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `actor_admin_id` | UUID | nullable for system/bootstrap actions |
| `actor_email_snapshot` | varchar(255) | snapshot |
| `action` | varchar(80) | canonical action name |
| `entity_type` | varchar(64) | |
| `entity_id` | varchar(64) | |
| `restaurant_id` | UUID | nullable; no FK |
| `reason` | varchar(1000) | required for mutations |
| `request_id` | varchar(64) | from middleware |
| `ip` | varchar(64) | |
| `user_agent` | varchar(255) | |
| `before_json` | JSONB | nullable, redacted |
| `after_json` | JSONB | nullable, redacted |
| `created_at` | timestamptz | |

Indexes: `ix_platform_audit_created`, `ix_platform_audit_action`, `ix_platform_audit_tenant`, `ix_platform_audit_actor`.

Production grants: `INSERT` + `SELECT` only; no `UPDATE`/`DELETE`.

### 1.4 `platform_plans`

Platform-wide products sold to tenants.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `code` | varchar(40) | unique, immutable after creation (`starter`, `growth`, `professional`) |
| `name` | varchar(120) | |
| `description` | text | nullable |
| `price_monthly_minor` | integer | >= 0 |
| `price_annual_minor` | integer | >= 0 |
| `currency_code` | varchar(3) | default `USD` |
| `trial_days` | integer | default 0 |
| `entitlements` | JSONB | shape from plan 07 |
| `status` | varchar(32) | `DRAFT`, `ACTIVE`, `ARCHIVED` |
| `is_public` | boolean | default true |
| `sort_order` | integer | default 0 |
| `archived_at` | timestamptz | nullable |
| `created_by_admin_id` | UUID | nullable |
| `created_at`, `updated_at` | timestamptz | |

Indexes: `uq_platform_plans_code`, `ix_platform_plans_status_sort`.

Entitlements JSON (reuse plan 07):

```json
{
  "branches":            { "limit": 1 },
  "staff_users":         { "limit": 10 },
  "tables":              { "limit": 30 },
  "menu_items":          { "limit": 200 },
  "orders_per_month":    { "limit": 5000 },
  "qr_ordering":         { "enabled": true },
  "kitchen_display":     { "enabled": true },
  "inventory":           { "enabled": false },
  "loyalty":             { "enabled": false },
  "advanced_reports":    { "enabled": false },
  "multi_branch_analytics": { "enabled": false },
  "custom_domain":       { "enabled": false },
  "api_access":          { "enabled": false }
}
```

Absent key = not entitled. Enforcement is PA-2; PA-1 only stores and displays the document.

### 1.5 `platform_subscriptions`

One live subscription per tenant. Parallel to the existing tenant-scoped `subscriptions` table; it does not replace or migrate it in MVP.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK → `restaurants.id` | not null, indexed |
| `plan_id` | UUID FK → `platform_plans.id` | not null |
| `status` | varchar(32) | see transitions |
| `trial_ends_at` | timestamptz | nullable |
| `current_period_start` | timestamptz | not null |
| `current_period_end` | timestamptz | not null |
| `cancel_at_period_end` | boolean | default false |
| `canceled_at` | timestamptz | nullable |
| `grace_ends_at` | timestamptz | nullable |
| `price_snapshot_minor` | integer | price at assignment |
| `currency_snapshot` | varchar(3) | |
| `billing_interval_snapshot` | varchar(16) | `MONTHLY` or `ANNUAL` |
| `created_by_admin_id` | UUID | nullable |
| `created_at`, `updated_at` | timestamptz | |

Statuses: `TRIALING`, `ACTIVE`, `PAST_DUE`, `GRACE`, `SUSPENDED`, `CANCELLED`, `EXPIRED`.

Partial unique index guarantees one live subscription per tenant:

```sql
CREATE UNIQUE INDEX uq_platform_subscriptions_live_tenant
ON platform_subscriptions (restaurant_id)
WHERE status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE','SUSPENDED');
```

Indexes: `ix_platform_subscriptions_status`, `ix_platform_subscriptions_plan`.

### 1.6 `platform_subscription_events`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `subscription_id` | UUID FK → `platform_subscriptions.id` `ON DELETE CASCADE` | |
| `event_type` | varchar(48) | `CREATED`, `TRIAL_EXTENDED`, `PLAN_CHANGED`, `RENEWED`, `PAST_DUE`, `GRACE_STARTED`, `SUSPENDED`, `REACTIVATED`, `CANCELLED`, `EXPIRED`, `PAYMENT_RECORDED` |
| `from_status` | varchar(32) | nullable |
| `to_status` | varchar(32) | nullable |
| `actor_admin_id` | UUID | nullable for system |
| `reason` | varchar(1000) | nullable for system events |
| `metadata_json` | JSONB | e.g. old/new plan, days extended |
| `created_at` | timestamptz | |

Index: `ix_platform_sub_events_subscription_created`.

### 1.7 `platform_invoices`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `invoice_number` | varchar(40) | unique, generated as `INV-{FY}-{000001}` |
| `fiscal_year` | varchar(8) | e.g. `2082`; part of the unique pair |
| `sequence_number` | integer | per-fiscal-year sequence; unique with `fiscal_year` |
| `restaurant_id` | UUID FK → `restaurants.id` | not null, indexed |
| `subscription_id` | UUID FK → `platform_subscriptions.id` | nullable |
| `status` | varchar(24) | `DRAFT`, `OPEN`, `PAID`, `VOID`, `OVERDUE`, `REFUNDED` |
| `subtotal_minor` | integer | sum of lines |
| `discount_minor` | integer | default 0 |
| `total_minor` | integer | subtotal − discount |
| `refunded_amount_minor` | integer | default 0; derived, never hand-edited |
| `currency_code` | varchar(3) | default `NPR` in MVP |
| `issued_at` | timestamptz | nullable while draft |
| `due_at` | timestamptz | not null |
| `paid_at` | timestamptz | nullable |
| `voided_at` | timestamptz | nullable |
| `void_reason` | varchar(1000) | nullable; required when voided |
| `notes` | text | nullable |
| `invoice_type` | varchar(32) | `PLATFORM_SUBSCRIPTION` in PA-1; reserved values for other platform invoice types. Never used for restaurant sales invoices. |
| `issuer_name` | varchar(255) | snapshot of the platform company issuing the invoice |
| `issuer_address` | varchar(500) | nullable snapshot |
| `issuer_pan` | varchar(32) | nullable; must be confirmed by a Nepali tax professional before being treated as mandatory/compliant |
| `issuer_vat_registered` | boolean | default false; drives VAT wording/fields on the template |
| `issuer_vat_number` | varchar(32) | nullable |
| `buyer_name` | varchar(255) | restaurant/legal entity snapshot |
| `buyer_pan` | varchar(32) | nullable; captured when available |
| `buyer_address` | varchar(500) | nullable |
| `tax_treatment` | varchar(24) | `UNCONFIRMED` by default; no tax amount is invented. Values such as `VAT`, `EXEMPT`, `ZERO_RATED` are only used after tax sign-off. |
| `tax_amount_minor` | integer | default 0; derived from approved template, never hand-typed |
| `template_version` | varchar(32) | identifies the approved invoice template/config used |
| `created_by_admin_id` | UUID | nullable |
| `created_at`, `updated_at` | timestamptz | |

Indexes: `uq_platform_invoices_number`, `uq_platform_invoices_fy_sequence (fiscal_year, sequence_number)`, `ix_platform_invoices_tenant_status`, `ix_platform_invoices_due`.

Numbering rules:
- Sequence is allocated inside the invoice transaction with `SELECT ... FOR UPDATE` on `platform_invoice_sequences`.
- `VOID` invoices keep their number; numbers are never reused.
- `fiscal_year` is derived from `issued_at` using `fiscal_year_start_month` (default 7 = Shrawan, Nepal).
- This table issues **platform subscription invoices only**. Restaurant sales invoices to diners are a separate document with a different issuer, PAN/VAT status, numbering, and financial record; the platform billing tables never store or generate them.
- Issuer/tax fields are snapshots so old invoices do not change when settings change. `tax_treatment` defaults to `UNCONFIRMED` until a Nepali tax professional signs off the template (Q-5).

### 1.8 `platform_invoice_lines`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `invoice_id` | UUID FK → `platform_invoices.id` `ON DELETE CASCADE` | |
| `kind` | varchar(24) | `PLAN`, `OVERAGE`, `DISCOUNT`, `ADJUSTMENT` |
| `description` | varchar(255) | |
| `quantity` | integer | default 1 |
| `unit_amount_minor` | integer | |
| `amount_minor` | integer | quantity × unit, signed for discounts |
| `sort_order` | integer | default 0 |

### 1.9 `platform_invoice_sequences`

One row per fiscal year. Locked `FOR UPDATE` when allocating an invoice number.

| Column | Type | Notes |
|--------|------|-------|
| `fiscal_year` | varchar(8) PK | e.g. `2082` |
| `next_sequence` | integer | default 1, not null |
| `updated_at` | timestamptz | |

### 1.10 `platform_payments`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `invoice_id` | UUID FK → `platform_invoices.id` | not null, indexed |
| `restaurant_id` | UUID FK → `restaurants.id` | not null, indexed |
| `kind` | varchar(16) | `PAYMENT` (default) or `REFUND` |
| `amount_minor` | integer | > 0; kind determines direction |
| `currency_code` | varchar(3) | default `NPR` |
| `method` | varchar(32) | `CASH`, `BANK_TRANSFER`, `CARD_TERMINAL`, `ESEWA`, `KHALTI`, `OTHER` |
| `reference` | varchar(120) | human-entered reference |
| `normalized_reference` | varchar(120) | trimmed/uppercased; unique for non-void payments |
| `provider` | varchar(40) | `MANUAL` in MVP; gateway name in PA-3 |
| `provider_reference` | varchar(120) | nullable; the verifiable external transaction reference (bank/eSewa/Khalti). Required unless the audited cash exception applies. |
| `evidence_type` | varchar(24) | nullable; `BANK_SLIP`, `ESEWA_RECEIPT`, `KHALTI_RECEIPT`, `CARD_SLIP`, `OTHER`. **Optional in PA-1.** |
| `evidence_ref` | varchar(500) | nullable; **private object-storage key/path only** (never bytes, never a public URL, never a signed URL). |
| `evidence_content_type` | varchar(100) | nullable; server-detected, not taken from the filename |
| `evidence_size_bytes` | bigint | nullable; validated against the configured maximum |
| `evidence_uploaded_at` | timestamptz | nullable |
| `exception_reason` | varchar(1000) | nullable; required when `method=CASH` and no verifiable reference |
| `status` | varchar(24) | `PENDING`, `CONFIRMED`, `REFUND_PENDING`, `REFUND_APPROVED`, `REFUNDED`, `REJECTED`, `VOIDED`, `FAILED` |
| `paid_at` | timestamptz | when the money moved |
| `recorded_by_admin_id` | UUID | who created the row |
| `confirmed_by_admin_id` | UUID | verifier; mandatory when `CONFIRMED` |
| `confirmed_at` | timestamptz | nullable |
| `voided_at` | timestamptz | nullable |
| `void_reason` | varchar(1000) | nullable |
| `refund_of_payment_id` | UUID FK → `platform_payments.id` | nullable; required for `kind=REFUND` |
| `refund_original_reference` | varchar(120) | snapshot of the original payment's reference |
| `refund_destination` | varchar(255) | nullable at request, required before completion; bank account / eSewa-Khalti id / other destination (masked where appropriate) |
| `refund_requested_by_admin_id` | UUID | nullable |
| `refund_requested_at` | timestamptz | nullable |
| `refund_reason_code` | varchar(32) | nullable (`DUPLICATE`, `SERVICE_FAILURE`, `GOODWILL`, `BILLING_ERROR`, `OTHER`) |
| `refund_reason_note` | varchar(1000) | nullable |
| `refund_approved_by_admin_id` | UUID | nullable; recorded even when the same admin approves (flagged) |
| `refund_approved_at` | timestamptz | nullable |
| `refund_completed_by_admin_id` | UUID | nullable; the person who confirms the external refund happened |
| `refund_completed_at` | timestamptz | nullable |
| `refund_external_reference` | varchar(120) | nullable; actual external refund transaction reference |
| `refund_processed_outside_platform` | boolean | default false; true when refund execution is handled outside the product |
| `refund_rejected_reason` | varchar(1000) | nullable |
| `idempotency_key` | varchar(120) | unique when present |
| `raw_payload_json` | JSONB | nullable; gateway payload in PA-3 |
| `created_at`, `updated_at` | timestamptz | |

Indexes:
- `uq_platform_payments_idempotency`
- `uq_platform_payments_reference` — unique on `normalized_reference` where `status IN ('CONFIRMED','REFUND_PENDING','REFUND_APPROVED','REFUNDED')`
- `ix_platform_payments_tenant_paid`
- `ix_platform_payments_status`

Rules:
- Confirmed rows are immutable; there is no amount-edit endpoint.
- A refund is a separate `kind=REFUND` row; the original row is never mutated except a derived `refunded_amount_minor` on the invoice.
- A refund amount cannot exceed the original confirmed amount minus prior approved/paid refunds.
- Evidence is optional. When present, only the private object key is stored; viewing requires a short-lived signed URL issued after checking the payment record and finance/admin permission.
- SaaS subscription payments and restaurant customer QR payments never share a row, table, reference namespace, or evidence prefix. Restaurant QR payment data stays in the restaurant/payment modules and is never copied here.
- Refund requester, approver, and completer are separate audit-relevant fields. A refund completed outside the product sets `refund_processed_outside_platform=true` and must still carry `refund_external_reference`.

### 1.11 `platform_payment_events`

Append-only ledger. Corrections are new events, never `UPDATE`/`DELETE`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `payment_id` | UUID | not null, indexed; no FK so events survive archival |
| `invoice_id` | UUID | not null, indexed |
| `restaurant_id` | UUID | not null |
| `event_type` | varchar(48) | `payment_created`, `payment_confirmed`, `payment_voided`, `refund_requested`, `refund_approved`, `refund_completed`, `refund_rejected`, `refund_paid`, `payment_corrected` |
| `amount_minor` | integer | snapshot |
| `currency_code` | varchar(3) | snapshot |
| `actor_admin_id` | UUID | nullable for system |
| `reason` | varchar(1000) | required |
| `metadata_json` | JSONB | nullable; snapshots, participants, external references |
| `created_at` | timestamptz | |

Index: `ix_platform_payment_events_payment_created`.

Production grants: `INSERT` + `SELECT` only.

### 1.12 `platform_settings`

| Column | Type | Notes |
|--------|------|-------|
| `key` | varchar(80) PK | allowlisted keys |
| `value_json` | JSONB | |
| `description` | varchar(255) | |
| `updated_by_admin_id` | UUID | nullable |
| `updated_at` | timestamptz | |

MVP allowlist:

```
platform.company_name                      string
platform.support_email                     string
platform.default_currency                  "NPR" (MVP); ISO code list later
platform.invoice_prefix                    string (e.g. "INV")
platform.fiscal_year_start_month           integer 1-12 (default 7 = Shrawan)
platform.default_trial_days                integer
platform.billing_grace_days                integer
platform.trial_extension_max_days_per_action  integer (default 30)
platform.trial_extension_max_days_total       integer (default 60)
platform.export_retention_days                integer (default 30)
platform.export_max_rows                      integer (default 500000)
platform.invoice.issuer_name                  string (platform company legal name)
platform.invoice.issuer_address               string
platform.invoice.issuer_pan                   string (nullable until tax sign-off)
platform.invoice.issuer_vat_registered        boolean (default false)
platform.invoice.issuer_vat_number            string (nullable)
platform.invoice.default_template_version     string (approved template identifier)
platform.invoice.tax_treatment                string (default "UNCONFIRMED")
platform.payment.instructions_text            string (multiline; company QR/bank instructions)
platform.payment.qr_image_ref                 string (deployment asset path; not payment evidence)
platform.evidence.max_size_bytes              integer (default 5 MiB)
platform.evidence.allowed_content_types       list  (default ["image/jpeg","image/png","application/pdf"])
platform.evidence.signed_url_ttl_seconds      integer (default 300)
platform.session_absolute_hours               integer (default 12)
platform.step_up_minutes                      integer (default 5)
platform.login_max_attempts                   integer (default 5)
platform.login_lockout_minutes                integer (default 15)
```

`platform.refund_dual_approval_threshold_minor` is **not** a PA-1 setting. It is deferred until a written financial risk policy exists (see `09-risks-and-decisions.md` Q-3).

Unknown keys are rejected. Settings changes require `settings.manage` + step-up and are audited (`PLATFORM_SETTING_UPDATED`) with before/after.

### 1.13 `platform_data_exports`

Audit-safe record of tenant exports (PA-2, but schema decided now).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `restaurant_id` | UUID | not null, indexed |
| `requested_by_admin_id` | UUID | not null |
| `status` | varchar(24) | `PENDING`, `READY`, `EXPIRED`, `FAILED` |
| `format` | varchar(16) | `JSON_CSV_ZIP` |
| `scope_json` | JSONB | exact entity list and row counts |
| `artifact_ref` | varchar(500) | nullable; object-store key |
| `expires_at` | timestamptz | `created_at + export_retention_days` |
| `created_at`, `updated_at` | timestamptz | |

Exports are filtered by `restaurant_id` from the authenticated path, never from a request body. The manifest records row counts per entity and a hash of the tenant id, so an isolation test can detect leakage.

## 2. Existing table changes

### 2.1 `restaurants`

Add:

| Column | Type | Notes |
|--------|------|-------|
| `archived_at` | timestamptz | nullable; soft delete only |
| `suspended_at` | timestamptz | nullable |
| `suspended_reason` | varchar(1000) | nullable |
| `contact_email` | varchar(255) | nullable |
| `contact_phone` | varchar(40) | nullable |
| `legal_name` | varchar(200) | nullable |

Status values become `ACTIVE`, `SUSPENDED`, `CANCELLED`. Trial is a **subscription** state (`TRIALING`), not a tenant status. Existing `ACTIVE` rows are compatible. No destructive migration.

### 2.2 `restaurant_memberships`

Add:

| Column | Type | Notes |
|--------|------|-------|
| `token_version` | integer | default 0, not null |

Used by tenant force-logout. Staff JWT gains `ver`; `get_actor` compares.

### 2.3 No changes to `subscription_plans` / `subscriptions` / `subscription_billing_info`

These remain the tenant-facing “subscription” screens. They are frozen for the duration of PA-1. Do not add platform logic to them, and do not migrate historical rows. A later cleanup (rename/deprecate) needs its own ADR after PA-1.

## 3. Status transitions

### 3.1 Subscription

```
(create) → TRIALING ──trial ends/paid──→ ACTIVE
                │                          │
                │                          ├─ payment overdue → PAST_DUE
                │                          │        ├─ grace → GRACE
                │                          │        └─ end  → SUSPENDED
                │                          ├─ cancel at period end → CANCELLED
                │                          └─ period ends unpaid → EXPIRED
                └─ cancel → CANCELLED
SUSPENDED ──reactivate/paid──→ ACTIVE
CANCELLED ──reactivate──→ ACTIVE (new period, reason required)
EXPIRED   ──new paid invoice──→ ACTIVE
```

PA-1 implements: create trial/active, extend trial, change plan, cancel at period end, reactivate, expire via manual action or invoice due date. Automatic transitions are PA-2.

### 3.2 Invoice

```
DRAFT → OPEN → PAID
  │       ├── VOID
  │       └── OVERDUE → PAID | VOID
  └── VOID
PAID → PAID (partial refund, refunded_amount_minor > 0)
PAID → REFUNDED (fully refunded)
```

Only `DRAFT` and `OPEN` can be voided. `PAID` cannot be voided; use a refund. `VOID` keeps its invoice number.

### 3.3 Payment

```
PENDING → CONFIRMED
        └→ FAILED
CONFIRMED → VOIDED (reason required; only before period activation, superadmin)
CONFIRMED → REFUND_PENDING → REFUND_APPROVED → REFUNDED (completed)
                          └→ REJECTED
                          └→ CONFIRMED (rejected/cancelled request)
```

The original `CONFIRMED` payment row is never edited or deleted. Refunds are separate `kind=REFUND` rows linked by `refund_of_payment_id`, and every transition appends `platform_payment_events`.

## 4. Migration plan

### 4.1 Revision

One revision: `pa0001_platform_core.py` (down_revision = current head at implementation time).

Contents:

1. Create `platform_admins`, `platform_refresh_tokens`, `platform_one_time_tokens`, `platform_audit_logs`.
2. Create `platform_plans`, `platform_subscriptions`, `platform_subscription_events`.
3. Create `platform_invoice_sequences`, `platform_invoices`, `platform_invoice_lines`, `platform_payments`, `platform_payment_events`.
4. Create `platform_settings`, `platform_data_exports` (the latter may be deferred to PA-2 with its own revision if PA-1 does not use it).
5. Add columns to `restaurants` and `restaurant_memberships`.
6. Create indexes, the partial unique subscription index, the unique payment-reference index, and the `(fiscal_year, sequence_number)` invoice index.
7. Seed nothing in the migration. Seed is app-level and idempotent.
8. Append-only tables (`platform_audit_logs`, `platform_payment_events`) get `INSERT`/`SELECT` grants only for the app role in the deploy step.

### 4.2 Dev and test behavior

- Dev startup still uses `Base.metadata.create_all`; importing `app.modules.platform` registers the models.
- Tests call `drop_all`/`create_all`; fixtures must create platform admins/plans per test module.
- The structure test requires no new cross-module import beyond the documented `platform -> tenancy : services.platform_directory` edge.

### 4.3 Production behavior

- `alembic upgrade head` before deploy.
- Startup check already fails if the DB is not at head.
- Backfill: none required for platform tables. `restaurant_memberships.token_version` defaults to 0 for existing rows. New nullable restaurant columns need no backfill.
- Rollback: drop the new tables and the added columns. No existing data is rewritten, so rollback is safe during PA-1.

### 4.4 Data retention

Category-specific, not one blanket period. Periods marked “pending sign-off” are placeholders for engineering behavior, not legal claims; Q-6 in `09-risks-and-decisions.md` must close them.

| Data category | Retention | Notes |
|---------------|-----------|-------|
| Subscription invoices / payments | Pending tax/accounting sign-off; never hard-deleted in PA-1/PA-2 | Financial record |
| VAT-related records | Applicable statutory period once confirmed | No universal “6 years for everything” rule |
| Platform audit logs | 3 years (proposed; security/legal sign-off) | append-only |
| Payment events | Same as the related payment | append-only ledger |
| Uploaded payment evidence | Pending financial-record sign-off (proposed 7 years) | private object store; access restricted and audited |
| Platform admins | indefinite while active; anonymize 3 years after disable | no hard delete in MVP |
| Restaurant operational data | Category-specific export + post-cancellation deletion rules | see lifecycle below |
| Tenants | no hard delete in MVP | archive only; export before deletion |
| Refresh tokens | purge 30 days after expiry/revocation | maintenance job PA-2 |
| Invitation tokens | 72 hours | hashed at rest |
| Data exports | `export_retention_days` (default 30) | artefact deleted; audit event kept permanently |
| Backups | documented expiry + deletion propagation | restore must not resurrect deleted data beyond policy |

**Cancellation lifecycle:** cancellation request → defined export window → read-only/access-restricted → deletion after the documented period, except records under legal retention or hold → deletion recorded in the audit log. No “delete all tenant data 30 days after cancellation” rule.

## 5. Seed data

### 5.1 Production bootstrap (idempotent)

`bootstrap_platform(db, settings)` runs after schema check:

- If no active `superadmin` exists and `PLATFORM_BOOTSTRAP_EMAIL/PASSWORD` are set:
  - create the admin with `role=superadmin`, `status=ACTIVE`, `mfa_enabled_at=null` (enrollment required on first login),
  - audit `PLATFORM_BOOTSTRAP_ADMIN_CREATED`.
- If the bootstrap admin exists but is disabled, re-enable it and audit loudly (break-glass path per plan 08 §1.1).
- Never overwrite an existing password or MFA secret.
- If the table is empty and env vars are missing, fail startup with a clear error.
- The bootstrap account is the **primary** Super Admin. The **secondary** Super Admin and the **emergency recovery owner** are real people supplied by the company before launch (PA-ADR-001 / Q-4). Do not seed a fake second admin in production; a development seed is not a launch credential.

### 5.2 Development/demo seed

When the dev database is empty, seed in addition to the existing `seed_if_empty`:

```
platform@harbor.example   / PlatformOwner!1    role=superadmin
platform2@harbor.example  / PlatformOwner!2    role=superadmin   # DEV/TEST ONLY (maker–checker fixtures); never a production launch credential
support@harbor.example    / PlatformSupport!1  role=support
billing@harbor.example    / PlatformBilling!1  role=billing
ops@harbor.example        / PlatformOps!1      role=ops

TOTP secret (dev only): JBSWY3DPEHPK3PXP
```

Plans (NPR, MVP currency):

```
starter       NPR  999 / month   trial 14
growth        NPR 1999 / month   trial 14
professional  NPR 3999 / month   trial 14
enterprise    custom / annual    trial 30
```

Demo subscription: `harbor-table` → `growth`, status `TRIALING`, 14-day trial. Demo invoice: one `OPEN` invoice for `growth`, due in 7 days.

**Security:** these credentials are development-only. `seed_if_empty` is already skipped in production; the platform demo seed must follow the same rule and must never run when `app_env == "production"`.

### 5.3 Fixtures for tests

Add `tests/fixtures/platform.py` (or extend `conftest.py`) with:

- `platform_admin` factory per role (including two superadmins for maker–checker),
- `platform_cookies(admin)` returning a valid access/refresh/CSRF cookie set (no bearer tokens),
- `platform_client(admin)` — an HTTP client with the cookie jar and automatic `X-CSRF-Token`,
- `mfa_code_for(secret)` helper using the same TOTP library,
- `platform_plan` factory,
- `tenant_with_subscription` factory,
- `invoice` factory (with allocated fiscal-year sequence),
- `payment` factory with a unique reference; evidence optional.

Fixtures must be independent of the demo seed and must clean up in the same order as the foreign keys.
