# 05 — API Contracts

**Base path:** `/api/platform`
**Content type:** `application/json`; the optional evidence upload is `multipart/form-data`; errors use `application/problem+json` (same shape as the staff API).
**Auth:** HttpOnly cookies (`platform_access`, `platform_refresh`) plus `X-CSRF-Token` on state-changing requests. No bearer token is accepted or returned. Public endpoints are `/auth/login`, `/auth/mfa/*`, `/auth/refresh`, `/auth/invitations/*`, `/auth/password-reset/*`.
**CORS:** `allow_credentials=true`; only `platform_admin_origin` (and optionally `platform_tenant_origin`). No wildcard.
**Versioning:** path-free within `/api/platform`; breaking changes require `/api/platform/v2`. MVP is v1.

---

## 1. Common conventions

### 1.1 Pagination

Request: `?page=1&page_size=25` (default 25, max 100).
Response:

```json
{ "items": [], "total": 0, "page": 1, "page_size": 25 }
```

### 1.2 Errors

```json
{
  "type": "about:blank",
  "title": "Conflict",
  "status": 409,
  "code": "INVOICE_ALREADY_PAID",
  "detail": "Invoice INV-2082-000123 is already paid.",
  "request_id": "..."
}
```

Rules:

- `401` — missing/invalid/expired token, wrong realm, revoked session, step-up required.
- `403` — authenticated but role lacks permission, tenant suspended, or CSRF/origin rejected.
- `404` — target missing **or** outside the caller’s authorized scope (no existence leak).
- `409` — state conflict (already paid, last superadmin, live subscription exists, duplicate reference).
- `422` — validation (including missing/short reason, missing transaction reference, invalid evidence type/size).
- `429` — rate limited.

### 1.3 Mutations, CSRF, and step-up

- Every mutating endpoint requires `reason` (string, 10–1000 chars) in the JSON body unless explicitly marked system-only.
- Destructive endpoints additionally require `confirm` equal to the tenant slug, invoice number, or admin email.
- Every non-GET request must carry `X-CSRF-Token` matching the `platform_csrf` cookie, **except** `POST /auth/refresh`, which is protected by `SameSite=Strict` plus the origin check (the access/CSRF cookies may be expired when it runs). `Origin` must match the configured admin origin for every state-changing request. Failure → `403 CSRF_INVALID` (and `CSRF_REJECTED` audit).
- Routes marked `[step-up]` require `auth_time` within `platform_step_up_minutes`; otherwise `401 STEP_UP_REQUIRED`.
- Payment/refund endpoints require `Idempotency-Key` header (8–120 chars).
- Responses include the affected resource and `audit_id` where useful.

### 1.4 Dates and money

- ISO-8601 UTC timestamps (`2026-11-04T10:00:00Z`).
- Money as integer minor units + `currency_code`. Never floats.
- Date-range filters: `from`/`to` inclusive, UTC.

### 1.5 Permission notation

`[tenant.view]` means the route requires that permission. `[step-up]` means the step-up guard is also required.

---

## 2. Authentication

### `POST /auth/login`

```json
{ "email": "platform@example.com", "password": "..." }
```

200 (MFA required):

```json
{
  "mfa_required": true,
  "mfa_ticket": "one-time-ticket",
  "enrollment_required": false,
  "expires_in": 300
}
```

200 (MFA not enrolled, first login):

```json
{
  "mfa_required": true,
  "enrollment_required": true,
  "enrollment_ticket": "one-time-ticket",
  "expires_in": 600
}
```

Errors: `401 INVALID_CREDENTIALS`, `403 ACCOUNT_DISABLED`, `429 ACCOUNT_LOCKED`.

> Dev-only: if `platform_require_mfa=false` and `app_env != "production"`, login completes by setting the cookies directly with `mfa_required=false`. Production startup rejects `platform_require_mfa=false`. Tests must still cover the MFA-on path.

### `POST /auth/mfa/verify`

```json
{ "mfa_ticket": "...", "code": "123456" }
```

200 (no tokens in the body):

```json
{
  "expires_in": 900,
  "admin": {
    "id": "...",
    "email": "...",
    "display_name": "...",
    "role": "superadmin",
    "permissions": ["tenant.view", "..."]
  }
}
```

Sets three cookies:

- `platform_access` — `HttpOnly; Secure; SameSite=Strict; Path=/api/platform`, 15 min
- `platform_refresh` — `HttpOnly; Secure; SameSite=Strict; Path=/api/platform/auth`, 12 h, rotated
- `platform_csrf` — `Secure; SameSite=Strict; Path=/`, 15 min (JS-readable)

Errors: `401 MFA_INVALID`, `401 MFA_TICKET_EXPIRED`, `429 MFA_LOCKED`.

### `POST /auth/mfa/enroll/start`

Body: `{ "enrollment_ticket": "..." }` for first login, or no body for an authenticated admin re-enrolling.

200:

```json
{ "otpauth_uri": "otpauth://totp/...", "secret": "BASE32", "recovery_codes": ["..."] }
```

### `POST /auth/mfa/enroll/verify`

```json
{ "enrollment_ticket": "...", "code": "123456" }
```

`enrollment_ticket` is omitted only for an already-authenticated admin re-enrolling. 200: `{ "mfa_enabled": true }`. On success the admin must log in again.

### `POST /auth/step-up`

```json
{ "password": "...", "code": "123456" }
```

200: `{ "step_up_until": "2026-11-04T10:05:00Z", "expires_in": 900 }`. Re-issues the access cookie with a fresh `auth_time`; the refresh family and its 12-hour absolute cap are unchanged.
Requires `X-CSRF-Token`. Errors: `401 INVALID_CREDENTIALS`, `401 MFA_INVALID`, `403 CSRF_INVALID`.

### `POST /auth/refresh`

No body; uses the `platform_refresh` cookie. Rotates the family and re-issues the access + CSRF cookies.

200: `{ "expires_in": 900, "admin": { ... } }` (no token in the body). `401 REFRESH_INVALID` on reuse/expiry; reuse revokes the family and audits `REFRESH_REUSE_DETECTED`.

### `POST /auth/logout`

Revokes the current refresh family, increments nothing on other sessions, and clears all three cookies. `204`.

### `POST /auth/sessions/revoke-all` [step-up]

Revokes every refresh family for the current admin and increments `token_version` (“sign out everywhere”). `200 { "revoked_families": 3 }`.

### `GET /auth/sessions`

Lists active refresh families for the current admin: `{ id, created_at, last_used_at, ip, user_agent, current }`.

### `DELETE /auth/sessions/{id}` [step-up]

Revokes one family. Cannot revoke the current session through this route; use `/auth/logout`.

### `GET /me`

200: admin summary + permissions + `mfa_enabled` + `last_auth_at` + `step_up_until`.

### `PATCH /me`

```json
{ "display_name": "..." }
```

### `POST /me/password`

```json
{ "current_password": "...", "new_password": "..." }
```

Increments `token_version`, revokes other refresh families, audits.

### `POST /me/mfa/reset`

Starts self-service re-enrollment after password + TOTP verification. `[step-up]`.

### 2.1 Invitations and password resets (public, rate-limited)

These endpoints do **not** issue a platform token. They consume a one-time token and activate the target account. The user then logs in through the normal realm.

#### `GET /auth/invitations/{token}`

Validates an owner/admin invitation. Returns `{ "email": "...", "purpose": "OWNER_INVITE", "tenant_name": "...", "expires_at": "..." }`. Used by the accept page before rendering the form. `404 INVITATION_NOT_FOUND` for missing/expired/used tokens (do not distinguish).

#### `POST /auth/invitations/{token}/accept`

```json
{ "password": "...", "display_name": "Maya Chen" }
```

Creates/activates the owner `users` row and membership through the tenancy service, consumes the token, and audits `OWNER_INVITE_ACCEPTED` (or `PLATFORM_USER_INVITE_ACCEPTED`). Returns `{ "ok": true }`. The user then signs in at `/login` (owner) or `/admin/login` (platform admin). Password policy applies.

#### `POST /auth/password-reset/{token}/accept`

```json
{ "password": "..." }
```

Consumes an `ADMIN_PASSWORD_RESET` token, sets the new hash, increments `token_version`, revokes refresh tokens, and audits. Returns `{ "ok": true }`.

All three endpoints are rate-limited by IP + token and return the same `404` for invalid/expired/used tokens.

---

## 3. Dashboard and diagnostics

### `GET /dashboard?from=&to=` [platform.dashboard.view]

```json
{
  "from": "2026-10-01T00:00:00Z",
  "to": "2026-11-01T00:00:00Z",
  "definitions_version": 1,
  "metrics": {
    "tenants_total": 42,
    "tenants_active": 30,
    "tenants_trial": 7,
    "tenants_suspended": 3,
    "tenants_cancelled": 2,
    "branches_total": 51,
    "staff_total": 210,
    "platform_users_total": 4,
    "active_subscriptions": 37,
    "mrr_minor": 7400000,
    "arr_minor": 88800000,
    "collections_minor": 6200000,
    "pending_payments": 5,
    "failed_payments": 1,
    "trial_conversion_rate": 0.42,
    "new_tenants": 9,
    "renewal_rate": 0.91,
    "churn_rate": 0.03,
    "currency_code": "NPR"
  },
  "health": { "api": "ok", "database": "ok" },
  "recent_activity": [
    { "id": "...", "action": "TENANT_SUSPENDED", "actor_email": "...", "created_at": "..." }
  ]
}
```

Metric definitions are binding; see `02-scope-and-priorities.md` §7.

### `GET /diagnostics/health` [diagnostics.view]

```json
{ "api": "ok", "database": "ok", "migrations": "head", "checked_at": "..." }
```

No fake components. If a component does not exist (Redis/worker), omit it.

### `GET /tenants/{id}/diagnostics` [diagnostics.view]

```json
{
  "tenant_id": "...",
  "checks": [
    { "key": "owner_membership", "status": "ok", "detail": "1 active owner" },
    { "key": "settings_row", "status": "ok" },
    { "key": "active_subscription", "status": "warning", "detail": "Trial ends in 3 days" },
    { "key": "branch_count", "status": "ok", "detail": "2 branches" },
    { "key": "recent_audit", "status": "ok", "detail": "last action 2h ago" }
  ]
}
```

Read-only. No tenant PII beyond contact fields and counts.

---

## 4. Tenants

### `GET /tenants?status=&plan=&q=&page=&page_size=` [tenant.view]

`q` searches name, slug, and owner email. Returns summary rows:

```json
{
  "items": [{
    "id": "...",
    "name": "Harbor Table",
    "slug": "harbor-table",
    "status": "ACTIVE",
    "plan_code": "growth",
    "subscription_status": "ACTIVE",
    "owner_email": "owner@example.com",
    "branches": 2,
    "staff": 12,
    "created_at": "..."
  }],
  "total": 1, "page": 1, "page_size": 25
}
```

### `POST /tenants` [tenant.create] [step-up]

```json
{
  "name": "Harbor Table",
  "slug": "harbor-table",
  "owner_email": "owner@example.com",
  "owner_display_name": "Maya Chen",
  "contact_email": "billing@harbor.example",
  "contact_phone": "+977...",
  "legal_name": "Harbor Table Pvt. Ltd.",
  "timezone": "Asia/Kathmandu",
  "currency_code": "NPR",
  "plan_code": "growth",
  "trial_days": 14,
  "source": "sales-assisted",
  "reason": "Signed after demo call"
}
```

201:

```json
{
  "tenant": { "id": "...", "slug": "harbor-table", "status": "ACTIVE" },
  "subscription": { "id": "...", "status": "TRIALING", "trial_ends_at": "..." },
  "invitation": {
    "token": "one-time-token",
    "expires_at": "...",
    "accept_url": "https://app.example.com/invite/one-time-token"
  }}
```

The raw invitation token is returned **once** and never logged. In MVP the admin copies the link manually. Errors: `409 SLUG_TAKEN`, `409 OWNER_EMAIL_EXISTS`, `409 PLAN_NOT_ACTIVE`.

### `GET /tenants/{id}` [tenant.view]

Returns profile, contact fields, status, plan, subscription summary, counts, recent audit (last 20), and usage summary.

### `PATCH /tenants/{id}` [tenant.create]

Editable: name, contact fields, legal name, timezone, currency. Slug is immutable. Requires reason.

### `POST /tenants/{id}/suspend` [tenant.suspend] [step-up]

```json
{ "reason": "Non-payment for 45 days", "confirm": "harbor-table" }
```

200: updated tenant + `audit_id`. Errors: `409 TENANT_ALREADY_SUSPENDED`, `404 TENANT_NOT_FOUND`.

### `POST /tenants/{id}/reactivate` [tenant.reactivate] [step-up]

```json
{ "reason": "Payment received", "confirm": "harbor-table" }
```

Restores `ACTIVE` and the subscription state per policy. Errors: `409 TENANT_NOT_SUSPENDED`.

### `POST /tenants/{id}/force-logout` [tenant.force_logout] [step-up]

```json
{ "reason": "Credential leak reported", "confirm": "harbor-table" }
```

200: `{ "revoked_memberships": 12, "audit_id": "..." }`.

### `POST /tenants/{id}/export` [tenant.export] [step-up] (PA-2)

```json
{ "format": "JSON_CSV_ZIP", "reason": "Customer requested a copy before renewal" }
```

202 with `{ "export_id": "...", "status": "PENDING", "expires_at": "..." }`. Export scope is fixed by the server (tenant profile, staff, menu, orders, bills, payments, inventory, loyalty, reviews, tenant audit events). Never includes other tenants or platform-internal notes. The manifest records row counts and a tenant-id hash. Artefacts expire after `export_retention_days`.

### `POST /tenants/{id}/archive` [tenant.delete] [step-up]

Soft delete only in PA-1: sets `archived_at`, cancels the live subscription per policy, and revokes staff sessions. Data is retained. Errors: `409 TENANT_HAS_LIVE_SUBSCRIPTION` unless `cancel_subscription=true`.

### `POST /tenants/{id}/delete` [tenant.delete] [step-up] (PA-3, gated)

Hard delete is **not** available in PA-1 or PA-2. In PA-3 it requires: a completed export, the retention window elapsed, typed confirmation of the tenant slug, step-up MFA, and approval by a second real superadmin. Without all of these → `409 DELETION_PRECONDITIONS_UNMET`.

### `GET /tenants/{id}/usage` [tenant.view]

Returns entitlement limits and current usage once enforcement exists (PA-2). In PA-1, returns counts only:

```json
{ "branches": { "used": 2 }, "staff": { "used": 12 }, "orders_this_month": { "used": 431 } }
```

### `GET /tenants/{id}/audit` [audit.view]

Paginated platform audit entries scoped to that tenant.

---

## 5. Plans

### `GET /plans?include_archived=false` [plan.view]

List of plans with prices, limits, entitlements, and active subscription count.

### `POST /plans` [plan.manage] [step-up]

```json
{
  "code": "growth",
  "name": "Growth",
  "description": "For growing restaurants",
  "price_monthly_minor": 199900,
  "price_annual_minor": 1999000,
  "currency_code": "NPR",
  "trial_days": 14,
  "entitlements": { "branches": { "limit": 3 } },
  "is_public": true,
  "reason": "New plan for Q4"
}
```

201 with the plan. Errors: `409 PLAN_CODE_EXISTS`, `422 INVALID_ENTITLEMENTS`.

### `GET /plans/{id}` [plan.view]

### `PATCH /plans/{id}` [plan.manage] [step-up]

Editable: name, description, prices, trial days, entitlements, `is_public`, `sort_order`. `code` is immutable. Price changes affect **new** subscriptions only; existing subscriptions keep their `price_snapshot_minor` until renewal. Requires reason.

### `POST /plans/{id}/archive` [plan.manage] [step-up]

```json
{ "reason": "Replaced by Growth v2", "confirm": "growth" }
```

Cannot archive a plan with live subscriptions; returns `409 PLAN_IN_USE` with `active_subscriptions` count.

---

## 6. Subscriptions

### `GET /subscriptions?tenant_id=&status=&plan_id=&page=` [subscription.view]

### `GET /subscriptions/{id}` [subscription.view]

Includes tenant summary, plan, period, cancel flag, and last 20 events.

### `POST /subscriptions` [subscription.manage] [step-up]

```json
{
  "restaurant_id": "...",
  "plan_code": "growth",
  "trial_days": 14,
  "reason": "Assign plan after sales call"
}
```

Errors: `409 LIVE_SUBSCRIPTION_EXISTS`, `404 PLAN_NOT_FOUND`, `409 PLAN_ARCHIVED`.

### `PATCH /subscriptions/{id}` [subscription.manage] [step-up]

```json
{
  "plan_code": "professional",
  "cancel_at_period_end": false,
  "current_period_end": "2026-12-01T00:00:00Z",
  "reason": "Upgrade requested"
}
```

Allowed fields: `plan_code`, `cancel_at_period_end`, `current_period_end` (bounded to +1 interval, with reason), `grace_ends_at` (superadmin only). Status is **not** directly writable. Errors: `409 INVALID_STATUS_TRANSITION`.

### `POST /subscriptions/{id}/extend-trial` [subscription.manage] [step-up]

```json
{ "days": 7, "reason": "Customer asked for evaluation time" }
```

`days` must be 1–`trial_extension_max_days_per_action` (default 30). Total trial extension above `trial_extension_max_days_total` (default 60) requires superadmin step-up plus a mandatory override reason; the audit event records both limits, the configured values, and the reason. Non-superadmin attempts return `403 TRIAL_LIMIT_REQUIRES_SUPERADMIN`.

### `POST /subscriptions/{id}/cancel` [subscription.manage] [step-up]

```json
{ "at_period_end": true, "reason": "Customer requested cancellation" }
```

### `POST /subscriptions/{id}/reactivate` [subscription.manage] [step-up]

```json
{ "reason": "Payment received" }
```

### `GET /subscriptions/{id}/events` [subscription.view]

Paginated event history.

---

## 7. Invoices and payments

### `GET /invoices?tenant_id=&status=&from=&to=&page=` [invoice.view]

### `POST /invoices` [invoice.manage] [step-up]

```json
{
  "restaurant_id": "...",
  "subscription_id": "...",
  "due_at": "2026-11-11T00:00:00Z",
  "currency_code": "NPR",
  "notes": "November subscription",
  "lines": [
    { "kind": "PLAN", "description": "Growth — November", "quantity": 1, "unit_amount_minor": 199900 },
    { "kind": "OVERAGE", "description": "1,200 extra orders", "quantity": 1, "unit_amount_minor": 50000 }
  ],
  "discount_minor": 0,
  "reason": "Monthly billing"
}
```

201 with `invoice_number` (`INV-{FY}-{000001}`), `fiscal_year`, `sequence_number`, totals, status `OPEN`. Server computes line amounts and totals; client cannot send `total_minor`. The number is allocated under a fiscal-year row lock. The server snapshots the issuer name/address/PAN/VAT status and `template_version`; `tax_treatment` is `UNCONFIRMED` by default and no tax amount is invented until the template is approved.

### `GET /invoices/{id}` [invoice.view]

Includes lines, confirmed payments, payment events, `refunded_amount_minor`, `fiscal_year`, the issuer snapshot, and `tax_treatment`. It never includes evidence bytes or signed evidence URLs.

### `GET /invoices/{id}/payment-instructions` [invoice.view]

Returns the read-only instructions the operator sends to the restaurant owner:

```json
{
  "invoice_number": "INV-2082-000123",
  "amount_minor": 199900,
  "currency_code": "NPR",
  "due_at": "...",
  "instructions_text": "Transfer to ... or scan the company QR ...",
  "qr_image_ref": "/assets/platform-payment-qr.png",
  "reference_to_quote": "INV-2082-000123"
}
```

These instructions are informational. There is no customer-facing “mark as paid” route; an invoice becomes `PAID` only through `POST /invoices/{id}/pay` after an authorised admin verifies receipt. A tenant-facing invoice screen is not part of PA-1.

### `POST /invoices/{id}/void` [invoice.manage] [step-up]

```json
{ "reason": "Issued to wrong tenant", "confirm": "INV-2082-000123" }
```

Only `DRAFT`/`OPEN`. The number is kept and marked `VOID`; it is never reused. Errors: `409 INVOICE_ALREADY_PAID`, `409 INVOICE_ALREADY_VOID`.

### `POST /invoices/{id}/pay` [payment.confirm] [step-up]

Header: `Idempotency-Key: <unique>`

```json
{
  "method": "BANK_TRANSFER",
  "reference": "NMB-2026-11-001",
  "provider_reference": "NMB-2026-11-001",
  "evidence_type": "BANK_SLIP",
  "evidence_ref": "evidence/platform-payments/2026/11/harbor-nov-slip.pdf",
  "paid_at": "2026-11-04T09:00:00Z",
  "reason": "Bank statement matched"
}
```

`reference` is required and must be unique among non-void payments. `provider_reference` (the transaction reference) is required unless `method=CASH` with an audited `exception_reason`. **Evidence is optional in PA-1**: `evidence_type`/`evidence_ref` may be omitted; a transaction reference plus the verifier record is sufficient. When evidence is supplied, `evidence_ref` must be a **private object key** obtained from the evidence-upload endpoint, not a public URL. The server normalizes the reference and rejects duplicates with `409 PAYMENT_REFERENCE_EXISTS`.

Evidence handling:

### `POST /payments/evidence` [payment.confirm]

Accepts a multipart upload; validates server-detected content type and size (settings), ignores the client filename, stores the object in the private bucket under a platform-payment prefix, and returns `{ "evidence_ref": "...", "content_type": "...", "size_bytes": ... }`.

### `GET /payments/{id}/evidence-url` [invoice.view]

Checks the payment record and finance/admin permission, then returns a **short-lived signed URL** (`expires_at`). It never returns a public URL and never proxies bytes through JSON. The URL is audit-logged without its signature.

- Evidence is excluded from logs, audit `before/after`, and error responses.

200:

```json
{
  "payment": { "id": "...", "status": "CONFIRMED", "amount_minor": 199900, "confirmed_by_admin_id": "..." },
  "invoice": { "id": "...", "status": "PAID", "paid_at": "...", "refunded_amount_minor": 0 },
  "subscription": { "id": "...", "current_period_end": "..." },
  "payment_event_id": "...",
  "audit_id": "..."
}
```

Errors: `409 INVOICE_ALREADY_PAID`, `409 INVOICE_VOID`, `409 PAYMENT_REFERENCE_EXISTS`, `422 INVALID_AMOUNT`, `422 PAYMENT_REFERENCE_REQUIRED`, `422 IDEMPOTENCY_KEY_REQUIRED`, `422 EVIDENCE_TYPE_INVALID`, `413 EVIDENCE_TOO_LARGE`.

### `POST /payments/{id}/void` [payment.void] [step-up]

```json
{ "reason": "Entered against the wrong invoice", "confirm": "NMB-2026-11-001" }
```

Only `CONFIRMED` payments before period activation. Sets `VOIDED`, appends `payment_voided`, and recalculates the invoice. There is **no** endpoint that edits a confirmed amount.

### `POST /payments/{id}/refund` [payment.refund.request] [step-up]

Header: `Idempotency-Key`

```json
{
  "amount_minor": 50000,
  "reason_code": "SERVICE_FAILURE",
  "reason": "Service credit agreed",
  "original_reference": "NMB-2026-11-001",
  "destination": "Bank account ending 1234",
  "processed_outside_platform": true,
  "evidence_ref": null
}
```

Creates a `REFUND_PENDING` request (`kind=REFUND`), records the requester, appends `refund_requested`, and returns `201`. It does **not** change the original payment, move money, or call a payment provider. `original_reference`, `amount_minor`, `reason`, and `destination` are required; `evidence_ref` is optional. `processed_outside_platform=true` is allowed when refund execution is handled outside the product, but it must be documented in the runbook and the external refund reference is still required at completion.

There is **no fixed monetary dual-approval threshold** in PA-1. The response returns `second_approval_policy: "DEFERRED"`. An authorised admin may approve their own request; the record is flagged `single_admin_approval`. A future financial risk policy may make a second approver mandatory in a later phase.

Errors: `409 REFUND_EXCEEDS_PAID`, `409 ALREADY_REFUNDED`, `422 REASON_REQUIRED`, `422 REFUND_DESTINATION_REQUIRED`, `422 ORIGINAL_REFERENCE_REQUIRED`.

### `POST /refunds/{id}/approve` [payment.refund.approve] [step-up]

```json
{ "reason": "Verified with finance" }
```

Records `refund_approved_by_admin_id` and `refund_approved_at`, sets `REFUND_APPROVED`, and appends `refund_approved`. Approval does **not** claim the money has moved. If the approver is also the requester, the event carries `single_admin_approval: true`; this is permitted until the risk policy exists. Approval requires step-up.

Errors: `409 REFUND_NOT_PENDING`, `422 REASON_REQUIRED`.

### `POST /refunds/{id}/complete` [payment.refund.complete] [step-up]

```json
{
  "external_reference": "ESEWA-RFND-88213",
  "completed_at": "2026-11-06T10:00:00Z",
  "destination": "Bank account ending 1234",
  "processed_outside_platform": true,
  "note": "Refund sent from the company bank account"
}
```

Records `refund_completed_by_admin_id`, `refund_completed_at`, `refund_external_reference`, and `refund_processed_outside_platform`; sets `REFUNDED`; appends `refund_completed`; updates invoice `refunded_amount_minor`; writes audit. No money is moved by the API. `external_reference` is mandatory even when the refund was executed outside the product.

Errors: `409 REFUND_NOT_APPROVED`, `422 EXTERNAL_REFUND_REFERENCE_REQUIRED`.

### `POST /refunds/{id}/reject` [payment.refund.approve] [step-up]

```json
{ "reason": "Insufficient evidence" }
```

Sets `REJECTED`, appends `refund_rejected`; the original payment stays `CONFIRMED`.

### `GET /payments?tenant_id=&status=&kind=&from=&to=&page=` [invoice.view]

### `GET /payments/{id}` [invoice.view]

Includes the immutable `payment_events` timeline and, for refunds, the original payment summary.

### `GET /payments/{id}/events` [invoice.view]

Append-only event list. No write routes.

### `GET /refunds?status=&tenant_id=&page=` [invoice.view]

Pending approvals queue, with `second_approval_policy: "DEFERRED"`, requester/approver/completer fields, and the external refund reference.

---

## 8. Platform users

### `GET /platform-users?role=&status=&q=` [platform_user.view]

### `POST /platform-users` [platform_user.manage] [step-up]

```json
{
  "email": "new.ops@example.com",
  "display_name": "Ops Person",
  "role": "ops",
  "reason": "New operations hire"
}
```

201 returns:

```json
{
  "admin": { "id": "...", "email": "...", "role": "ops", "status": "INVITED" },
  "invitation": {
    "token": "one-time-token",
    "expires_at": "...",
    "accept_url": "https://app.example.com/admin/invite/one-time-token"
  }
}
```

Raw token shown once. No email in MVP.

### `PATCH /platform-users/{id}` [platform_user.manage] [step-up]

```json
{ "role": "billing", "status": "ACTIVE", "reason": "Role change" }
```

Last-superadmin invariant applies to demote/disable. Errors: `409 LAST_SUPERADMIN`.

### `POST /platform-users/{id}/disable` [platform_user.manage] [step-up]

```json
{ "reason": "Left the company", "confirm": "person@example.com" }
```

Increments `token_version`, revokes refresh tokens, audits.

### `POST /platform-users/{id}/reset-mfa` [platform_user.manage] [step-up]

```json
{ "reason": "Lost phone", "confirm": "person@example.com" }
```

Clears MFA, increments token version, forces enrollment on next login. Superadmin only.

### `POST /platform-users/{id}/reset-password`

Superadmin-initiated one-time reset token (no email in MVP).

---

## 9. Audit

### `GET /audit-logs?action=&tenant_id=&actor_id=&from=&to=&page=` [audit.view]

```json
{
  "items": [{
    "id": "...",
    "action": "TENANT_SUSPENDED",
    "actor_email": "ops@example.com",
    "entity_type": "restaurant",
    "entity_id": "...",
    "restaurant_id": "...",
    "reason": "Non-payment for 45 days",
    "before": { "status": "ACTIVE" },
    "after": { "status": "SUSPENDED" },
    "ip": "203.0.113.10",
    "created_at": "..."
  }],
  "total": 1, "page": 1, "page_size": 25
}
```

### `GET /audit-logs/{id}` [audit.view]

No update/delete routes. Any attempt returns `405`.

> Implementation note: register `/audit-logs/export` **before** `/audit-logs/{id}` so FastAPI does not capture `export` as an ID.

### `GET /audit-logs/export?from=&to=` [audit.view]

Streams CSV or NDJSON; the export itself is audited (`AUDIT_EXPORTED`). MVP can return a one-off file for ranges ≤ 31 days.

---

## 10. Settings

### `GET /settings` [settings.view]

Returns the allowlisted keys and current values.

### `PATCH /settings` [settings.manage] [step-up]

```json
{
  "changes": {
    "platform.company_name": "Rest OS",
    "platform.default_trial_days": 14
  },
  "reason": "Brand update"
}
```

Rejects unknown keys (`422 UNKNOWN_SETTING`) and invalid types. Audits before/after.

---

## 11. Error code catalog (MVP)

| Code | Status | Meaning |
|------|--------|---------|
| `PLATFORM_AUTH_REQUIRED` | 401 | Missing/bad platform session cookie |
| `WRONG_REALM` | 401 | Staff/customer token on platform route |
| `TOKEN_EXPIRED` | 401 | Access cookie expired |
| `SESSION_REVOKED` | 401 | `token_version` mismatch or family revoked |
| `REFRESH_INVALID` | 401 | Refresh cookie missing/expired/rotated |
| `REFRESH_REUSE_DETECTED` | 401 | Rotated refresh token replayed; family revoked |
| `MFA_REQUIRED` | 401 | Login needs MFA |
| `MFA_INVALID` | 401 | Wrong TOTP/recovery code |
| `MFA_TICKET_EXPIRED` | 401 | Ticket timed out |
| `MFA_RECOVERY_EXHAUSTED` | 403 | All recovery codes used; superadmin reset required |
| `STEP_UP_REQUIRED` | 401 | Fresh re-auth needed |
| `PLATFORM_FORBIDDEN` | 403 | Role lacks permission |
| `CSRF_INVALID` | 403 | Missing/mismatched CSRF token |
| `ORIGIN_NOT_ALLOWED` | 403 | Request origin not in the allowlist |
| `ACCOUNT_DISABLED` | 403 | Admin disabled |
| `ACCOUNT_LOCKED` | 429 | Login lockout |
| `TENANT_NOT_FOUND` | 404 | Missing or out of scope |
| `TENANT_ALREADY_SUSPENDED` | 409 | Duplicate suspension |
| `TENANT_NOT_SUSPENDED` | 409 | Reactivate a live tenant |
| `SLUG_TAKEN` | 409 | Tenant slug exists |
| `OWNER_EMAIL_EXISTS` | 409 | Owner identity exists |
| `PLAN_CODE_EXISTS` | 409 | Duplicate plan code |
| `PLAN_IN_USE` | 409 | Archive blocked by live subscriptions |
| `PLAN_ARCHIVED` | 409 | Assign archived plan |
| `LIVE_SUBSCRIPTION_EXISTS` | 409 | Second live subscription |
| `INVALID_STATUS_TRANSITION` | 409 | Illegal lifecycle move |
| `INVOICE_ALREADY_PAID` | 409 | Pay/void a paid invoice |
| `INVOICE_VOID` | 409 | Pay a void invoice |
| `INVOICE_ALREADY_VOID` | 409 | Void twice |
| `PAYMENT_REFERENCE_EXISTS` | 409 | Duplicate normalized reference |
| `PAYMENT_IMMUTABLE` | 409 | Attempt to edit a confirmed payment |
| `REFUND_EXCEEDS_PAID` | 409 | Refund > captured minus prior refunds |
| `ALREADY_REFUNDED` | 409 | Refund fully consumed |
| `REFUND_NOT_PENDING` | 409 | Approve/reject a refund not in `REFUND_PENDING` |
| `REFUND_NOT_APPROVED` | 409 | Complete a refund before approval |
| `TRIAL_LIMIT_REQUIRES_SUPERADMIN` | 403 | Trial exception needs superadmin |
| `DELETION_PRECONDITIONS_UNMET` | 409 | Export/retention/approval missing |
| `LAST_SUPERADMIN` | 409 | Would leave zero superadmins |
| `REASON_REQUIRED` | 422 | Missing/short reason |
| `PAYMENT_REFERENCE_REQUIRED` | 422 | No transaction reference and not the audited cash exception |
| `REFUND_DESTINATION_REQUIRED` | 422 | Refund request missing destination |
| `ORIGINAL_REFERENCE_REQUIRED` | 422 | Refund request missing original payment reference |
| `EXTERNAL_REFUND_REFERENCE_REQUIRED` | 422 | Refund completion missing the external refund reference |
| `EVIDENCE_TYPE_INVALID` | 422 | Uploaded evidence content type not allowed |
| `EVIDENCE_TOO_LARGE` | 413 | Uploaded evidence exceeds the configured max size |
| `CONFIRMATION_MISMATCH` | 422 | Typed confirm does not match |
| `UNKNOWN_SETTING` | 422 | Setting key not allowlisted |
| `IDEMPOTENCY_KEY_REQUIRED` | 422 | Missing payment/refund idempotency key |

## 12. OpenAPI and documentation

- Tag routers: `platform-auth`, `platform-dashboard`, `platform-tenants`, `platform-plans`, `platform-billing`, `platform-admins`, `platform-audit`, `platform-settings`.
- Every route includes a summary, permission requirement, and error responses.
- The contract is frozen at the end of PA-1.1; later phases add endpoints, they do not silently change payloads.
- The frontend types in `packages/api-client` are generated/updated from the same schema definitions; no hand-written duplicate types in pages.
