# 03 — Architecture and Security

**Cross-references:** master decisions D2/D3/D4/D14, `05-authentication-authorization.md`, `08-super-admin.md`, `19-security-threat-model.md`.

---

## 1. Realm model

Three realms, three credentials, three route trees. Tokens are not interchangeable.

```
┌──────────────────────────────────────────────────────────────────┐
│ Staff realm        /api/v1/*        secret A   realm=staff        │
│   JWT sub=user, mid=membership, rid=restaurant, ver=token_version │
│   Bearer token in the staff SPA (existing behaviour, unchanged)  │
├──────────────────────────────────────────────────────────────────┤
│ Customer realm     /public/*        QR/session token, no user JWT │
│   Guest ordering flow, scoped to one table/session               │
├──────────────────────────────────────────────────────────────────┤
│ Platform realm     /api/platform/*  secret B   realm=platform     │
│   Access JWT in HttpOnly cookie (15 min)                          │
│   Opaque rotating refresh cookie (12 h) + CSRF double-submit      │
│   Origin admin.{platform_domain}; separate SPA build             │
└──────────────────────────────────────────────────────────────────┘
```

**Hard rules**

1. `get_actor` (staff) rejects any token without `realm == "staff"`.
2. `get_platform_admin` decodes with `platform_secret_key` only and rejects any token without `realm == "platform"`.
3. Platform tokens never carry `mid`/`rid`; tenant scope is always an explicit target ID.
4. No route is reachable by two realms. Cross-realm access is a 401, not a 403.
5. The platform secret is never the same value as the staff secret — startup fails if they match in production.
6. The platform app never reads a token from `Authorization`, a query string, or JS storage. The only sources are the HttpOnly access cookie and the refresh cookie.
7. The admin SPA never stores credentials in `localStorage` or `sessionStorage`.

## 2. Backend module layout

The existing `app/modules/platform/` stub becomes the bounded context. It owns platform tables and must not import other modules’ models.

```
app/modules/platform/
  __init__.py
  models.py                 # platform_admins, plans, subscriptions, invoices, payments, audit, settings
  schemas.py                # Pydantic request/response models
  permissions.py            # PLATFORM_ROLE_PERMISSIONS + require_platform_permission
  deps.py                   # get_platform_admin, require_platform_permission, step-up guard
  router_auth.py            # /auth/login, /mfa/*, /step-up, /refresh, /logout, /sessions, /me
  router_dashboard.py       # /dashboard, /diagnostics/health
  router_tenants.py         # /tenants/*
  router_plans.py           # /plans/*
  router_subscriptions.py   # /subscriptions/*
  router_billing.py         # /invoices/*, /payments/*
  router_admins.py          # /platform-users/*
  router_audit.py           # /audit-logs/*
  router_settings.py        # /settings/*
  services/
    auth.py                 # password + MFA + token lifecycle
    audit.py                # write_platform_audit(...)
    tenants.py              # tenant creation/lifecycle through tenancy service
    billing.py              # invoice totals, payment confirmation, subscription extension
    metrics.py              # dashboard aggregates (SQL)
    permissions.py          # role -> permission set
```

Composition:

```
app/api/platform/__init__.py   # empty package
app/api/platform/router.py     # APIRouter(); includes platform module routers
app/main.py                    # application.include_router(platform_router, prefix="/api/platform")
```

`app/api/platform/router.py` is a composition file; it may import `app.api.deps` and module routers. No module internals import `app.api`.

### 2.1 Cross-module boundary

Platform needs to create/read tenants and read branch/staff counts. The clean seam is a narrow public service in the tenant context:

```
app/modules/tenancy/services/platform_directory.py
    create_tenant_shell(...)
    get_tenant(...)
    set_tenant_status(...)
    list_tenants(...)
    tenant_counts(...)
    force_logout_tenant(...)
```

This adds one known edge: `platform -> tenancy : services.platform_directory`. The structure test freezes imports, so PA-ADR-009 must approve adding exactly that line to `tests/structure/couplings_baseline.txt`. No other cross-module edge is allowed.

Rationale: raw SQL for tenant creation would duplicate settings/membership invariants and bypass future RLS. One documented service edge is safer than copied SQL.

## 3. Authentication and session design

### 3.1 Login flow

```
POST /api/platform/auth/login {email, password}
  ├─ rate-limit by IP + email (5/min, 15-min lockout, exponential backoff)
  ├─ verify Argon2 hash (constant-time; generic error)
  ├─ if disabled/locked → 401 INVALID_CREDENTIALS or 403 ACCOUNT_DISABLED
  └─ password OK
       ├─ MFA not enrolled → mfa_required=true, enrollment_ticket (10 min)
       └─ MFA enrolled     → mfa_required=true, mfa_ticket (5 min)

POST /api/platform/auth/mfa/verify {mfa_ticket, code}
  ├─ validate TOTP (30s step, ±1 window) or recovery code (single use)
  ├─ create a refresh family (session id) and store the hashed refresh token
  ├─ set access cookie   (JWT, 15 min)
  ├─ set refresh cookie  (opaque 256-bit, 12 h, rotating)
  ├─ set csrf cookie     (random, non-HttpOnly, same lifetime as access)
  └─ audit LOGIN_SUCCESS
```

**No token ever appears in a response body.** The success response is `{ "admin": {...}, "expires_in": 900 }`.

### 3.2 Cookies, CSRF, and origin checks

| Cookie | Value | Flags | Path | Lifetime |
|--------|-------|-------|------|----------|
| `platform_access` | signed JWT (`realm=platform`) | `HttpOnly; Secure; SameSite=Strict` | `/api/platform` | 15 min |
| `platform_refresh` | opaque 256-bit token, hash stored server-side | `HttpOnly; Secure; SameSite=Strict` | `/api/platform/auth` | 12 h, rotated |
| `platform_csrf` | random 256-bit value | `Secure; SameSite=Strict` (readable by JS) | `/` | 15 min |

- State-changing requests must send `X-CSRF-Token` equal to `platform_csrf`. The server compares in constant time. Missing/mismatch → `403 CSRF_INVALID`.
- The server validates `Origin` (fallback `Referer`) against `platform_admin_origin` for every state-changing request, and against the allowlist for CORS preflight.
- CORS: `allow_credentials=True`, explicit origins only (`platform_admin_origin`, optionally `platform_tenant_origin`), never `*` with credentials. Unknown origin → preflight rejected; actual request still fails CSRF/origin check.
- Cookies are **host-only** (no `Domain` attribute) so they are tied to `api.{platform_domain}`.
- `Secure` is forced in production; startup refuses to boot with `platform_cookie_secure=false` unless `env=local`.
- Logout and refresh clear all three cookies with the same path/attributes.

### 3.3 Step-up

Sensitive actions require a fresh MFA assertion within `platform_step_up_minutes` (default 5):

- refund approval/completion, payment void,
- tenant suspend/reactivate/delete/export,
- plan price change,
- platform admin invite/role change/disable/MFA reset,
- platform settings change and trial-limit exceptions.

The access token carries `amr` and `auth_time`. If `now - auth_time > step_up_window`, the API returns `401 STEP_UP_REQUIRED` with `details.max_age_seconds`. The frontend opens a modal that re-verifies password + TOTP and calls `POST /api/platform/auth/step-up`; the response re-issues the access cookie with a fresh `auth_time`. Step-up does **not** extend the refresh family beyond its absolute 12-hour lifetime.

### 3.4 Refresh, logout, revocation

- Refresh token is a random 256-bit value; only its SHA-256 hash is stored (`platform_refresh_tokens`), grouped by `family_id`.
- Rotation on every refresh: the old row is marked `rotated_at`, a new token is issued in the same family. Reuse of a rotated token revokes the entire family, revokes access tokens via `token_version`, and audits `REFRESH_REUSE_DETECTED`.
- `POST /auth/refresh` is CSRF-exempt only because it is `SameSite=Strict` + origin-checked; it still validates the refresh cookie and family state.
- `logout` revokes the current family and clears cookies.
- `token_version` on `platform_admins` invalidates all access tokens when incremented (disable, password change, MFA reset, role change, force logout).
- “Sign out everywhere” revokes all refresh families for the admin and increments `token_version`.
- Staff `restaurant_memberships.token_version` is unaffected; tenant force-logout uses its own path.
- Absolute session cap: 12 h from login; a refresh cannot extend past `session_started_at + 12h`. Re-login is required.

### 3.5 MFA

- TOTP (RFC 6238), 6 digits, 30-second step, SHA-1, ±1 step tolerance.
- Secret generated server-side, stored encrypted at rest with a key derived from `platform_mfa_key` (separate from the JWT secret).
- Enrollment returns `otpauth://` URI and a QR rendered by the frontend; the secret is shown once.
- 10 recovery codes, Argon2-hashed, single-use, regenerated on reset. Using one audits `PLATFORM_RECOVERY_CODE_USED` and forces re-enrolment at next login.
- MFA reset is superadmin-only, requires a reason and step-up, increments `token_version`, and forces re-enrolment on next login.
- No SMS fallback in MVP.
- **Recovery is a tested procedure**, not a hope: two superadmins, sealed recovery codes, and the break-glass runbook in `11-operations-runbook.md` §3.

### 3.6 Configuration additions

Add to `app/core/config.py`:

```python
platform_secret_key: str = ""                 # required in production
platform_mfa_key: str = ""                    # required in production
platform_access_token_minutes: int = 15
platform_refresh_token_minutes: int = 720     # 12 h absolute cap
platform_step_up_minutes: int = 5
platform_require_mfa: bool = True
platform_admin_origin: str = ""               # e.g. https://admin.example.com
platform_api_origin: str = ""                 # e.g. https://api.example.com
platform_tenant_origin: str = ""              # e.g. https://www.example.com
platform_cookie_secure: bool = True
platform_cookie_domain: str = ""              # empty = host-only (required)
platform_bootstrap_email: str = ""
platform_bootstrap_password: str = ""
platform_bootstrap_mfa_secret: str = ""       # dev/test only
platform_timezone: str = "UTC"
```

Production startup must fail if `platform_secret_key` is empty, equals `secret_key`, `platform_mfa_key` is empty, `platform_admin_origin`/`platform_api_origin` are empty, `platform_cookie_domain` is non-empty, or `platform_cookie_secure` is false.

## 4. Authorization

### 4.1 Role → permission map (MVP)

Keep the map in code (`permissions.py`) for the pilot; a DB-backed role editor is P3. This mirrors the existing staff role pattern and keeps authorization reviewable in one file.

| Permission | support | billing | ops | superadmin |
|------------|:-------:|:-------:|:---:|:----------:|
| `platform.dashboard.view` | ✅ | ✅ | ✅ | ✅ |
| `tenant.view` | ✅ | ✅ | ✅ | ✅ |
| `tenant.search` | ✅ | ✅ | ✅ | ✅ |
| `tenant.create` | — | — | ✅ | ✅ |
| `tenant.suspend` | — | — | ✅ | ✅ |
| `tenant.reactivate` | — | — | ✅ | ✅ |
| `tenant.force_logout` | — | — | ✅ | ✅ |
| `tenant.export` | — | — | ✅ | ✅ |
| `tenant.delete` | — | — | — | ✅ |
| `plan.view` | ✅ | ✅ | ✅ | ✅ |
| `plan.manage` | — | — | — | ✅ |
| `subscription.view` | ✅ | ✅ | ✅ | ✅ |
| `subscription.manage` | — | ✅ | — | ✅ |
| `subscription.override` | — | — | — | ✅ |
| `invoice.view` | ✅ | ✅ | ✅ | ✅ |
| `invoice.manage` | — | ✅ | — | ✅ |
| `payment.confirm` | — | ✅ | — | ✅ |
| `payment.void` | — | — | — | ✅ |
| `payment.refund.request` | — | ✅ | — | ✅ |
| `payment.refund.approve` | — | ✅ | — | ✅ |
| `payment.refund.complete` | — | ✅ | — | ✅ |
| `platform_user.view` | — | — | — | ✅ |
| `platform_user.manage` | — | — | — | ✅ |
| `audit.view` | ✅ | ✅ | ✅ | ✅ |
| `settings.view` | ✅ | ✅ | ✅ | ✅ |
| `settings.manage` | — | — | — | ✅ |
| `diagnostics.view` | ✅ | ✅ | ✅ | ✅ |
| `analytics.view` | ✅ | ✅ | ✅ | ✅ |

Rules:

- Default deny. Unknown permission or unknown role → 403.
- `superadmin` is not a wildcard in code; it has the explicit full set so a diff shows new permissions.
- Platform roles are independent of tenant roles. A restaurant `owner` has zero platform permissions.
- The frontend hides controls the role cannot use, but the server is the authority.
- **Maker–checker for refunds:** `payment.refund.request`, `payment.refund.approve`, and `payment.refund.complete` are separate permissions. PA-1 has **no fixed monetary dual-approval threshold**; that policy is deferred until a financial risk policy exists. Every refund records requester, approver, and completer. Self-approval is permitted while the policy is deferred but is flagged `single_admin_approval`.
- `billing` is the finance/billing admin role. It confirms payments, requests refunds, approves them, and records completion; it cannot void payments.

### 4.2 Last-superadmin invariant

Any operation that would leave zero `ACTIVE` admins with role `superadmin` is rejected:

```
409 LAST_SUPERADMIN
```

Applies to disable, demote, and delete. Unit-tested and integration-tested. Bootstrap re-assert is the only exception, and it is audited.

**Launch gate:** commercial launch also requires **two** active superadmins, both **real named people** (primary and secondary), plus a documented **emergency recovery owner** and the storage location of recovery/break-glass credentials. The API enforces “never zero”; the two-person requirement is checked in the PA-1.4 launch checklist and shown as a banner in the admin UI. The second admin must be a real invitee who has completed MFA enrolment and a recovery drill — never a seeded placeholder.

## 5. Audit discipline

- Table: `platform_audit_logs` (append-only).
- Every mutation writes exactly one audit row **in the same DB transaction**. If the business change rolls back, the audit row is gone too — no phantom logs.
- Required fields: `actor_admin_id`, `actor_email_snapshot`, `action`, `entity_type`, `entity_id`, `restaurant_id?`, `reason`, `request_id`, `ip`, `user_agent`, `before_json`, `after_json`, `created_at`.
- `reason` is mandatory for mutations, minimum 10 characters, trimmed, max 1000.
- Read-only platform actions are not audited (otherwise the log becomes noise). Login success/failure, MFA events, step-up, refresh reuse, and logout are audited as security events.
- No API updates or deletes audit rows. Production DB grants `INSERT` + `SELECT` only for the app role.
- Retention: 3 years. Export is a read-only CSV/JSON stream; export itself is audited.

Canonical action names:

```
PLATFORM_LOGIN_SUCCESS          PLATFORM_LOGIN_FAILED
PLATFORM_MFA_ENROLLED           PLATFORM_MFA_RESET
PLATFORM_RECOVERY_CODE_USED     PLATFORM_STEP_UP
PLATFORM_LOGOUT                 PLATFORM_SESSION_REVOKED
REFRESH_REUSE_DETECTED          CSRF_REJECTED
TENANT_CREATED                  TENANT_SUSPENDED
TENANT_REACTIVATED              TENANT_FORCE_LOGOUT
TENANT_UPDATED                  TENANT_EXPORTED
TENANT_DELETION_REQUESTED       TENANT_DELETED
PLAN_CREATED                    PLAN_UPDATED
PLAN_ARCHIVED
SUBSCRIPTION_CREATED            SUBSCRIPTION_PLAN_CHANGED
SUBSCRIPTION_TRIAL_EXTENDED     SUBSCRIPTION_CANCELLED
SUBSCRIPTION_REACTIVATED        SUBSCRIPTION_EXPIRED
INVOICE_CREATED                 INVOICE_VOIDED
PAYMENT_CREATED                 PAYMENT_CONFIRMED
PAYMENT_VOIDED                  PAYMENT_REFUND_REQUESTED
PAYMENT_REFUND_APPROVED         PAYMENT_REFUND_COMPLETED
PAYMENT_REFUND_REJECTED         PAYMENT_REFUNDED
PAYMENT_EVENT_CORRECTED         PAYMENT_EVIDENCE_VIEWED
PLATFORM_USER_INVITED           PLATFORM_USER_INVITE_ACCEPTED
PLATFORM_USER_ROLE_CHANGED      PLATFORM_USER_DISABLED
PLATFORM_SETTING_UPDATED
```

## 6. Tenant isolation and suspension

### 6.1 Isolation

- Platform routes never trust `x-tenant-id`. Every tenant-scoped platform request takes an explicit `restaurant_id` in the path or a validated body field.
- Every invoice/payment/subscription lookup validates the parent chain:
  `payment.invoice.restaurant_id == target restaurant_id`.
- Cross-tenant access returns `404 TENANT_NOT_FOUND` (not 403) to avoid confirming existence.
- List endpoints always filter by the requested tenant or return the full platform list only to roles with the relevant permission.
- No platform endpoint proxies arbitrary tenant data. Diagnostics returns counts and configuration checks, not menu/order PII.
- Support role sees contact data (owner email/phone) and counters only; it never sees payment card data (none stored) or customer PII.

### 6.2 Suspension gate (D-6)

Suspension is a platform action, but enforcement lives in the staff request path.

- `restaurants.status` values: `ACTIVE`, `SUSPENDED`, `CANCELLED`. Trial is a **subscription** state (`TRIALING`), not a tenant status; do not duplicate it.
- Both `login` and `get_actor` check tenant status:
  - `ACTIVE` → normal.
  - `SUSPENDED` / `CANCELLED` → 403 `TENANT_SUSPENDED` at login and on requests, except an allowlist.
- Allowlist for suspended tenants (graceful D-6):
  - `GET /api/v1/me`, `GET /api/v1/restaurant`, and token refresh for staff already authenticated
  - read-only reports available to staff already signed in
  - **completing or cancelling orders created before suspension**
  - bill generation and bill settlement/payment capture for the current visit
  - staff logout
- Blocked for suspended tenants: creating dining sessions, creating **new** orders, starting a QR session, new staff/branch/menu writes, new subscription actions, exports.
- The allowlist is implemented as an explicit dependency (`require_active_tenant` on write routers) plus a narrow in-flight check (the order was created before `suspended_at`), not as a broad string match. Each router opts in; the default for new write routes is “blocked while suspended”.
- Enforcement tests must cover the blocked paths, the allowed in-flight order completion path, and the rejection of a **new** order on a suspended tenant.

### 6.3 Force logout

- `POST /tenants/{id}/force-logout` increments `token_version` on every active membership of that tenant in one transaction.
- Existing staff access tokens carry `ver`; `get_actor` rejects mismatches with `401 SESSION_REVOKED`.
- Platform admin sessions are not affected.
- The action is audited with the number of revoked memberships.

## 7. Payments and billing security

No card data is ever stored; the MVP is manual bank/cash/eSewa/Khalti transfer with human confirmation. Because a human is the control surface, the rules below are mandatory (PA-ADR-005).

### 7.1 Confirmation

- A payment requires: invoice `OPEN/OVERDUE`, positive amount ≤ invoice balance, `currency_code`, method, verifiable transaction reference (`provider_reference`), paid date, verifier, and `Idempotency-Key`.
- `provider_reference` is normalized (trim, collapse whitespace, uppercase) and unique per platform via a partial unique index where `status IN ('CONFIRMED','REFUND_PENDING','REFUND_APPROVED','REFUNDED')`. A duplicate is rejected with `409 PAYMENT_REFERENCE_EXISTS`.
- **Evidence is optional in PA-1.** A transaction reference plus the verifier record is sufficient. Manual payment recording must work with no evidence store configured; evidence upload is enabled only after the private bucket/access policy exists. When evidence is supplied it is uploaded to a private object bucket, PostgreSQL stores only the object key, and viewing uses a short-lived signed URL issued only to finance/admin roles after checking the payment record. Content type and size are validated server-side; the client filename is never trusted or used as the key.
- The only exception to the reference requirement is `method=CASH`, which requires `exception_reason` and is flagged `single_admin_confirmation` when only one admin exists.
- Evidence bytes/URLs are never written to logs, audit `before/after`, or error responses; a signed URL's signature is not logged.
- `platform_payments.idempotency_key` is unique. Replaying a key returns the original payment, not a second one.
- `POST /invoices/{id}/pay` performs, in one transaction:
  1. lock the invoice row (`SELECT ... FOR UPDATE`),
  2. reject if already paid/void,
  3. insert `platform_payments` (`status=CONFIRMED`),
  4. append `platform_payment_events` (`payment_confirmed`),
  5. set invoice `PAID` + `paid_at`,
  6. extend subscription `current_period_end` by the plan interval,
  7. append `platform_subscription_events`,
  8. write `platform_audit_logs`.
- Maker–checker: when the platform has more than one active admin, the verifier must differ from the invoice creator. Otherwise the payment is allowed but flagged and audited.

### 7.2 Immutability

- Confirmed payments are immutable. There is **no** endpoint that edits the amount, date, method, or reference of a confirmed payment.
- Corrections use events: `payment_voided` (with reason), then a new payment. `platform_payment_events` is append-only; production DB grants `INSERT` + `SELECT` only.
- Invoice totals are derived from confirmed payments minus approved refunds; they are never typed in by hand.
- Invoices are voided, not deleted. Void keeps the invoice number (`status=VOID`); numbers are never reused.
- Invoice numbering: `INV-{FY}-{000001}`, per-fiscal-year sequence allocated with `SELECT ... FOR UPDATE` on `platform_invoice_sequences`. `fiscal_year_start_month` defaults to 7 (Nepali fiscal year, Shrawan).

### 7.3 Refunds

- Refunds are separate `platform_payments` rows linked by `refund_of_payment_id`; the original is never mutated except a derived `refunded_amount_minor` maintained by the service.
- PA-1 does **not** process refunds automatically and does not call a provider API. Refunds may be executed outside the product if the runbook documents that the platform does not manage refund execution.
- `POST /payments/{id}/refund` creates a `REFUND_PENDING` request with amount, reason code + note, original payment reference, and destination. The requester is recorded.
- `POST /refunds/{id}/approve` records the approver and sets `REFUND_APPROVED`. `POST /refunds/{id}/complete` records the completer, the external refund transaction reference, and whether execution happened outside the platform; it sets `REFUNDED`. Approval and completion each require step-up MFA.
- There is **no fixed monetary dual-approval threshold** in PA-1. The policy is deferred until a written financial risk policy exists. While deferred, an authorised admin may approve and complete their own request, flagged `single_admin_approval`. A future policy may require a different approver; the data model already stores requester/approver/completer separately.
- Rejection records `refund_rejected`; the payment stays `CONFIRMED`.
- Refund amount cannot exceed the confirmed amount minus prior refunds.
- Evidence for refunds is optional and follows the same private-object/signed-URL rules as payment evidence.

### 7.4 Gateway (PA-3)

- Gateway webhooks must verify signatures, deduplicate by provider event id, and fetch the payment from the provider before activating anything.
- Provider events map into `platform_payment_events`; no direct writes to balances.
- Automated reconciliation compares provider settlement reports against `platform_payments` and flags unmatched rows.

### 7.5 Invoice and tax boundaries

- **Platform subscription invoice** = the SaaS company's invoice to a restaurant. It uses `platform_invoices`, the platform invoice series, and the platform issuer snapshot.
- **Restaurant sales invoice** = the restaurant's invoice to its diner. It belongs to the restaurant/tenant domain and is never generated from platform billing tables.
- Platform invoice templates are configurable by issuer name/address, PAN, VAT-registration status, VAT number, and invoice type. Issuer values are snapshotted on the invoice so later settings changes do not rewrite history.
- `tax_treatment` defaults to `UNCONFIRMED`. The product must not claim legal/tax compliance, and must not invent VAT amounts or statutory wording, until a Nepali tax professional confirms the current requirements (Q-5).
- A platform payment never changes a restaurant's order/bill state; a restaurant QR payment never marks a platform invoice paid.

### 7.6 Separation of SaaS billing from restaurant QR payments

- SaaS subscription payments live in `platform_payments` / `platform_payment_events`, use `/api/platform/...` routes, and are gated by platform permissions.
- Restaurant customer QR/table payments live in the tenant payment/order domain and are gated by tenant roles.
- They do not share payment IDs, reference namespaces, evidence buckets/prefixes, or reconciliation reports. Evidence for one must never be retrievable through the other's routes.
- Tests must prove a platform invoice cannot be paid by a restaurant QR callback and that a restaurant bill cannot be settled by a platform payment record.

## 8. Secrets, logging, and sensitive data

- Platform JWT secret, refresh-token hash pepper, MFA encryption key, and bootstrap password live only in environment/secret store; never in API responses, logs, or audit `before/after`.
- Audit snapshots redact `password_hash`, `mfa_secret`, `mfa_recovery_codes`, `token_hash`, `refresh_token`, `provider_reference` (hashed in logs), and authorization/cookie headers.
- Structured logging uses an allowlist; `password`, `token`, `access_token`, `refresh_token`, `cookie`, `authorization`, `csrf`, `secret`, `mfa_code` are dropped before serialization. No request-body logging on auth, MFA, invite, or payment routes.
- Log access is restricted to platform/ops roles and is itself audited; retention is documented in `11-operations-runbook.md`.
- Error responses are generic on auth failure; no “email exists” disclosure.
- Invitation tokens and refresh tokens are stored hashed; the raw value is shown once to the creating admin / set in an HttpOnly cookie and never logged.
- The admin frontend never persists credentials. No `localStorage`, no `sessionStorage`; the browser holds only HttpOnly cookies plus the non-secret CSRF cookie. API calls use `credentials: "include"`.

## 9. Background jobs (PA-2+)

- No worker exists in MVP. Do not add a scheduler to solve a PA-1 problem.
- When PA-2 adds jobs, each job:
  - iterates tenants explicitly and sets the tenant context per item,
  - is idempotent (job key + DB uniqueness),
  - writes audit rows for state changes it performs,
  - never runs without a tenant context on tenant-specific work,
  - has a dry-run mode and a per-run summary.
- Platform-wide jobs (trial expiry, invoice overdue) still record counts and failures per tenant.

## 10. Deployment shape and origins

**Production (required before commercial launch):**

```
www.{platform_domain}      tenant SPA (existing apps/web build)
admin.{platform_domain}    admin SPA (separate build entry, same repo)
api.{platform_domain}      FastAPI; all cookies host-only to this origin
```

- The admin SPA is a distinct build (`src/admin.tsx`, `admin.html`, `vite.admin.config.ts`) and a distinct static deployment. The tenant bundle is never served on the admin origin.
- Separate CSP per origin: the admin CSP has no third-party script/style/eval sources and `connect-src` limited to `api.{platform_domain}`.
- CORS allowlist: `https://admin.{platform_domain}` and `https://www.{platform_domain}` only, `allow_credentials=True`, explicit methods/headers including `X-CSRF-Token`.
- Cookies are host-only to `api.{platform_domain}` — no `Domain` attribute.
- DNS/TLS: separate certificates (or a wildcard) for all three hosts; HSTS on each. The actual domain and the registrar/DNS/TLS owner are **open** in PA-ADR-011. Credentials live in a company-controlled password manager, never the repository or committed `.env` files.
- The admin app and the API are deployable independently; the admin app is static and needs no server-side session.

**Local development:** one Vite dev server may proxy both `/api` and the admin entry. Same-origin is a dev-only convenience; the config must still set explicit origins and cookies with `Secure=false` only under `env=local`.

**Explicitly rejected:** production same-origin `/admin`. If it is ever used, it requires a written security acceptance, a risk entry, and compensating controls (strict CSP, no third-party scripts, short cookie lifetime). It is not the default and not the MVP path.

This adds deployment work (DNS, TLS, CORS, second static deployment, cookie path checks). It is budgeted in PA-0 and verified as a PA-1.4 launch gate.

## 11. Threat model mapping (spec §30)

| Requirement | Implementation | Test |
|-------------|----------------|------|
| Separate auth/authorization | Separate table, secret, realm, route tree, permission map, separate origin | Cross-realm token tests, origin tests |
| MFA | TOTP mandatory, recovery codes, reset flow, step-up | Missing/invalid/replayed TOTP, recovery-code single use |
| Session protection | HttpOnly access + refresh cookies, rotation, reuse detection, revocation | Cookie flag test, rotation/reuse test, sign-out-everywhere test |
| CSRF | Double-submit token + Origin check | Missing/mismatched token, cross-origin request |
| Least privilege | Explicit role map, default deny, maker–checker for refunds | Role matrix tests per endpoint |
| Tenant isolation | Explicit IDs, parent-chain checks, 404 on mismatch | Two-tenant fixture |
| Audit everything | Same-transaction append-only log, reason required | Mutation-without-reason test, audit immutability |
| No silent impersonation | Not built | Route absent + 404 test |
| Secure payments | Unique reference, optional private evidence with signed URLs, maker–checker, manual refunds with recorded participants, immutable events | Duplicate reference, duplicate confirmation, evidence access, refund participant/reference, SaaS/QR isolation |
| Protect secrets | Env only, redaction allowlist, no token in logs | Response + log snapshot test |
| Protect deletion | Soft delete, export first, step-up + typed confirmation | Deletion workflow test |
| Background jobs | No jobs in MVP; PA-2 explicit tenant context | Job context test in PA-2 |
