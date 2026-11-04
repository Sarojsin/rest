# 02 — Scope and Priorities

**Rule:** if it is not listed as IN for the active phase, it is OUT. Out-of-scope work goes to `10-parking-lot.md`; it does not get “just one small endpoint”.

---

## 1. Product scope statement

The Super Admin product is a **platform back office**. It lets a small platform team:

- see the health of the SaaS business,
- manage tenant lifecycle,
- define and assign plans,
- bill tenants manually and record payments,
- manage platform staff and roles,
- audit every sensitive action,
- diagnose tenant problems without operating the restaurant.

It is **not** a second restaurant dashboard, not an impersonation tool, and not a replacement for the tenant owner’s daily operations.

## 2. Priority vocabulary

| Tag | Meaning | Consequence |
|-----|---------|-------------|
| **P0** | Blocks secure launch | Must ship in PA-0/PA-1 |
| **P1** | MVP / commercial launch | Must ship in PA-1 |
| **P2** | Operational maturity | Only after PA-1 has run with real tenants |
| **P3** | Advanced SaaS | Separate business case |
| **NO** | Explicitly not planned | Requires a new ADR to reconsider |

A P2/P3 item is not a bug. It is a deliberate deferral.

## 3. MVP (PA-1) — IN

### 3.1 Platform foundation (PA-0)

- Separate `platform_admins` identity store with roles: `support`, `billing`, `ops`, `superadmin`.
- Separate platform JWT secret + `realm: "platform"` claim; staff tokens get `realm: "staff"`.
- **Separate admin origin** (`admin.{platform_domain}`) with a separate build entry; same-origin only in local dev.
- **HttpOnly access + refresh cookies** (`Secure`, `SameSite=Strict`, host-only), CSRF double-submit + Origin checks, CORS allowlist.
- Mandatory TOTP MFA for every platform admin. Enrollment on first login; single-use recovery codes.
- Short access lifetime (15 min), rotating refresh (12 h absolute cap), reuse detection, session revocation, step-up re-auth for destructive actions.
- **At least two active, real superadmins** before commercial launch (primary + secondary + documented emergency recovery owner); invite-only account creation; no fictional seed.
- Platform permission map, enforced server-side on every route; maker–checker for refunds.
- `platform_audit_logs`: append-only, actor, target, reason, before/after, IP, UA, request id.
- Idempotent bootstrap of the first superadmin from environment variables.
- Admin app shell, login, MFA, permission-gated navigation, step-up dialog.
- Staff `token_version` and tenant-status guard (needed for force-logout and suspension).

### 3.2 Dashboard and read surfaces (PA-1.1)

- Platform dashboard with date-range filter and a **defined metric dictionary** (see §7).
- Tenant list: search by name/slug/owner email, filter by status and plan, pagination.
- Tenant detail: profile, subscription, plan, branch/staff counts, recent audit, usage summary.
- Plan list and plan detail (read).
- Subscription list and detail (read).
- Audit log viewer: filter by action, tenant, actor, date; read-only.
- Platform health card (API + database only; no fake Redis/worker status).

### 3.3 Tenant and subscription lifecycle (PA-1.2)

- Create tenant shell + owner invitation token (no email in MVP).
- Suspend tenant with mandatory reason + typed confirmation; owner email is **not** sent in MVP (PA-2), but the action is audited.
- Reactivate tenant with reason.
- Force logout all tenant sessions via token version bump.
- Plan create/edit/archive (superadmin only); price changes affect new subscriptions only.
- Subscription create/change plan/extend trial/cancel-at-period-end/reactivate.
- Subscription event history.
- Audit viewer covers all these actions.

### 3.4 Manual billing with anti-fraud controls (PA-1.3)

**Sequencing:** manual invoice creation, transaction references, verification, payment status, and audit history ship **without** waiting for the private evidence store. Evidence upload is an optional follow-on capability enabled when P-9 is configured. Likewise, configurable invoice issuer/PAN/VAT fields and fiscal-year numbering can be built now; the final production template and any compliance claim wait for Nepali tax-professional sign-off.

- Invoice create with line items; due date; status `DRAFT/OPEN/PAID/VOID/OVERDUE`.
- Invoice numbering: `INV-{FY}-{000001}`, unique per fiscal year, configurable start month (default 7); voided numbers are not reused.
- Manual payment confirmation with method, **unique transaction reference**, paid date, verifier, idempotency key, and **optional evidence**.
- Evidence, when supplied, goes to private object storage; only the object key is stored; viewing uses short-lived signed URLs restricted to the payment and finance/admin roles. Validate type/size; never trust the filename; keep it out of public URLs and logs.
- Duplicate references are rejected; confirmed amounts are immutable; corrections use void + re-record.
- `platform_payment_events`: append-only ledger for create/confirm/void/refund events.
- Payment confirmation extends the subscription period and writes an audit row **in the same transaction**.
- Void invoice with reason (only before payment); void payment (superadmin, before activation).
- Refund request by `billing`/`superadmin` with amount, reason, original payment reference, and destination; approval and completion record separate participants and the external refund transaction reference. **No automated refund execution and no fixed monetary dual-approval threshold in PA-1**; the threshold is deferred until a financial risk policy exists.
- Refunds may be executed outside the product if the runbook documents that the platform does not manage execution.
- Invoice templates are configurable by issuer, PAN, VAT-registration status, and invoice type; platform subscription invoices are distinct from restaurant sales invoices. `tax_treatment` stays `UNCONFIRMED` until Nepali tax-professional sign-off.
- Invoice/payment/refund list and detail; pending-refund queue; read-only payment instructions for the owner.
- MRR, ARR, collections, pending/failed counts derived from these tables.
- Currency: NPR in MVP; `currency_code` stored on every money row; no FX conversion.
- SaaS subscription payments/evidence are strictly separate from restaurant customer QR payments/evidence.

### 3.5 Platform users, settings, diagnostics, launch hardening (PA-1.4)

- Platform admin list, invite/accept, change role, disable, reset MFA/password.
- Last-active-superadmin invariant plus the **two-real-superadmin launch gate**.
- Reset MFA for another admin (superadmin only, audited, forces re-enrollment); recovery drill completed.
- Platform settings: allowlisted keys for company, support email, currency (NPR), invoice prefix, fiscal-year start month, invoice issuer/PAN/VAT/template, payment instructions, trial defaults/limits, evidence limits, export retention, session/step-up/login limits. Refund threshold is **not** a PA-1 setting.
- Tenant diagnostics: read-only checks (owner membership exists, settings row exists, active subscription, branch count, last audit).
- Profile and personal security: change display name/password, re-enroll MFA, view/revoke own sessions, sign out everywhere.
- Security hardening: login rate limit, generic auth errors, no secret/PII leakage, CSP + security headers, audit immutability, cross-realm tests, cookie/CSRF/origin tests, no JS token storage.
- Production origin verification (DNS/TLS/cookies/CORS) and backup restore test as launch gates.
- Tenant export scope and **category-specific** retention policy approved (implementation in PA-2).
- Nepali tax-professional sign-off for the platform invoice template before any compliance claim.
- Evidence store and real primary/secondary/emergency-recovery identities confirmed before launch.

## 4. MVP — OUT (do not build in PA-1)

| Not in MVP | Why | Where it goes |
|------------|-----|---------------|
| Payments gateway / webhooks | Master plan D6 defers Stripe; no gateway exists | PA-3 / `PL-001` |
| Automatic renewal/dunning jobs | No worker/scheduler | PA-2 / `PL-002` |
| Email delivery (invites, suspensions, reminders) | No mail transport | PA-2 / `PL-003` |
| Impersonation / “login as tenant” | High risk; explicit no in plan 08 | `PL-013` |
| Support tickets and messages | Requires new product surface | PA-2 / `PL-004` |
| Announcements / notification center | Needs delivery infra | PA-2 / `PL-005` |
| Onboarding funnel monitoring | Needs event tracking | PA-2 / `PL-006` |
| Feature flags and targeting | Not needed for first tenants | PA-2 / `PL-007` |
| Integration management | No integrations yet | PA-2 / `PL-008` |
| Incident management / status page | Ops process first | PA-2 / `PL-009` |
| Backup monitoring UI | Infra job first | PA-2 / `PL-010` |
| Advanced analytics and business exports | Dashboard subset is enough | PA-2 / `PL-011` |
| Tenant data export + retention workflow | Scope/retention must be defined before launch; implementation after | PA-2 / `PL-017` |
| Hard tenant deletion / GDPR console | Legal process first; PA-1 is archive-only | PA-3 / `PL-017` |
| Coupons, promotions, referrals | Billing complexity | PA-3 / `PL-014` |
| CMS / website content | Separate product | PA-3 / `PL-015` |
| Developer API / API keys | Separate product | PA-3 / `PL-016` |
| Automated reconciliation | Needs gateway + volume | PA-3 / `PL-018` |
| Customer-success automation | Needs usage data | PA-3 / `PL-019` |
| Tenant staff management from platform | Tenant owns its staff; platform only reads counts | `PL-020` |
| Branch editing from platform | Tenant owns operations | `PL-020` |

## 5. P2 — Operational maturity (PA-2)

Ship only when at least one trigger is true:

- ≥10 paying tenants, or
- support requests exceed what the audit/diagnostics screens can answer, or
- payment failures require a repeatable dunning process.

P2 scope:

- Support tickets + internal notes + tenant-visible replies.
- Email delivery + notification preferences.
- Automated reminders/worker: trial expiry, renewal reminders, overdue invoices; explicit tenant context.
- Tenant data export + retention/deletion-request workflow (scope approved in PA-1.4).
- Monitoring, backups, and monthly restore testing.
- Admin-origin completion only if a documented launch exception was used.
- Onboarding checklist and funnel monitoring.
- Branch overview (read-only across tenants).
- Business analytics (cohorts, churn reasons, plan mix, date-range exports).
- Integration management (provider configs, webhook event log).
- Feature flags with tenant targeting.
- Incident and maintenance management.
- Backup monitoring (read-only status from infrastructure).

## 6. P3 — Advanced SaaS (PA-3)

Requires a separate business case and a new plan revision:

- Promotions, coupons, referrals.
- Website CMS.
- Developer API and API keys.
- Advanced data governance and deletion workflows.
- Automated payment reconciliation.
- Advanced usage analytics.
- Customer-success automation.
- Gateway payments, refunds against gateway, dunning automation.
- SSO/OIDC/SAML for platform admins: **future capability only**, not committed to PA-3; revisit after PA-2 with a business case.
- Time-limited, read-only impersonation with tenant notice (only after a dedicated security review).

## 7. Metric dictionary (binding for dashboard and tests)

Ambiguous metrics become bugs. These definitions are the contract.

| Metric | Definition | Source |
|--------|------------|--------|
| `tenants_total` | Count of non-archived `restaurants` | `restaurants` |
| `tenants_active` | `status = 'ACTIVE'` | `restaurants` |
| `tenants_trial` | Active subscription `status = 'TRIALING'` | `platform_subscriptions` |
| `tenants_suspended` | `restaurants.status = 'SUSPENDED'` | `restaurants` |
| `tenants_cancelled` | `status = 'CANCELLED'` | `restaurants` |
| `branches_total` | Count of branches for non-archived tenants | `branches` |
| `staff_total` | Count of active restaurant memberships | `restaurant_memberships` |
| `platform_users_total` | Count of active platform admins | `platform_admins` |
| `active_subscriptions` | `status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE')` | `platform_subscriptions` |
| `mrr_minor` | Sum of normalized monthly price of active paid subscriptions, excluding trials | `platform_subscriptions` + plan snapshot |
| `arr_minor` | `mrr_minor * 12` | derived |
| `collections_minor` | Sum of confirmed, non-void payments in range minus approved refunds | `platform_payments` |
| `pending_payments` | Invoices `OPEN/OVERDUE` with no confirmed payment | `platform_invoices` |
| `failed_payments` | `platform_payments.status = 'FAILED'` in range | `platform_payments` |
| `trial_conversion_rate` | Trials that became ACTIVE in range ÷ trials that ended in range | subscription events |
| `new_tenants` | Tenants created in range | `restaurants.created_at` |
| `renewal_rate` | Subscriptions renewed in range ÷ subscriptions due in range | subscription events |
| `churn_rate` | Subscriptions cancelled/expired in range ÷ active at range start | subscription events |
| `platform_health` | API `/health` + database `SELECT 1` | runtime |

Rules:

- Money is always integer minor units + ISO currency. No floats.
- A trial is never counted in MRR.
- Annual plans are normalized to monthly for MRR (`annual_price / 12`).
- Discounts reduce the invoice line, not the plan price.
- All date filters use the platform timezone (UTC in MVP).
- Every metric response includes its `from`/`to` and `definitions_version`.

## 8. Product-level acceptance for MVP

PA-1 is accepted only when all are true:

1. A superadmin can log in with password + TOTP at `admin.{platform_domain}`, and the response contains no tokens.
2. Access/refresh cookies are `HttpOnly; Secure; SameSite=Strict`, host-only; CSRF is enforced on every non-GET platform request; no credential is in JS storage.
3. A staff token/session cannot access `/api/platform`; a platform session cannot access `/api/v1`.
4. At least two active, real superadmins exist; the last one cannot be disabled or demoted; recovery codes and break-glass are tested; the emergency recovery owner is documented.
5. A superadmin can create a tenant, invite an owner, suspend it, reactivate it, and force logout its sessions.
6. Suspended tenants cannot start new dining sessions or create new orders; in-flight orders and bill completion still work per D-6.
7. A superadmin can create a plan, assign it, extend a trial (within configured limits), cancel at period end, and reactivate.
8. A billing admin can create an invoice with a fiscal-year number, confirm a payment with a unique transaction reference (evidence optional), and see the subscription period extend; the same idempotency key cannot create two payments.
9. A duplicate reference is rejected; confirmed amounts cannot be edited; payment events are append-only; evidence is private and only viewable through a short-lived signed URL.
10. A refund records requester, approver, completer, original reference, destination, and external refund reference; no fixed threshold is enforced while the financial risk policy is deferred.
11. Void/refund actions require a reason and produce audit rows; no audit row or payment event is ever updated or deleted.
12. The dashboard numbers match the metric dictionary against a seeded fixture.
13. Every destructive action requires step-up re-auth within 5 minutes.
14. The admin app has no console errors, each page has loading/empty/error/forbidden states, and CORS/CSRF failures are handled without loops.
15. The full backend suite, structure tests, both frontend builds, and the manual acceptance script pass; a backup restore drill is recorded.
16. The domain/DNS/TLS owner (PA-ADR-011), the real two-admin roster, the private evidence store, the Nepali tax sign-off, and the category-specific retention policy are recorded before commercial launch. Until then, no legal/tax compliance claim is made.

## 9. Change-control rule

Any request to add, remove, or reshape MVP scope needs:

1. a `PL-xxx` entry,
2. an ADR in `09-risks-and-decisions.md`,
3. an explicit statement of what leaves the phase (equal or greater size),
4. a refreshed estimate for the phase,
5. sign-off recorded in the ADR.

“It is only a small addition” is not a trade. If nothing leaves, nothing enters.
