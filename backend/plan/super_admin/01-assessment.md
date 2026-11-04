# 01 — Assessment of `super_admin_plan.md`

**Verdict:** the spec is a good product map and a bad single-phase implementation plan.
Build the MVP subset in PA-1. Do not attempt the other ~20 modules now.

---

## 1. What the spec gets right

- **Correct separation of responsibilities.** Business control (tenants, plans, billing), operational control (support, onboarding, diagnostics), and technical control (audit, security, monitoring) is the right mental model for a SaaS back office.
- **Correct warning about entitlements.** “Build one centralized entitlement service” is exactly right and matches existing plan `07-entitlements-enforcement.md`.
- **Correct security posture.** Separate platform role, MFA, least privilege, tenant isolation, append-only audit, no silent impersonation, backend-verified payments, protected deletion, tenant context on background jobs.
- **Correct launch instinct.** Section 31 explicitly says not to build all modules at once. The three priority tiers are sensible.

## 2. Where the spec is not yet an implementation plan

| Problem | Consequence |
|---------|-------------|
| 32 modules described at product level, not task level | No sequencing, no dependency graph, no exit criteria |
| Mixes MVP, next release, and multi-quarter ideas | Every reader sees “missing features” in the current phase |
| Assumes infrastructure the repo does not have | Email, worker/scheduler, payment gateway, monitoring, object storage |
| Assumes platform-scoped billing tables | Existing subscription tables are tenant-scoped and per-membership |
| Reuses names (`subscriptions`, `plans`, `payments`) already taken | A literal implementation would collide with existing modules |
| Describes dashboards before defining metric formulas | MRR/ARR/churn become opinionated and untestable |
| Describes support access and impersonation near MVP language | High-risk feature that should be deferred behind its own ADR |
| Does not define audit schema, reason rules, or step-up | Security requirements exist as prose, not as gates |

## 3. Current repo baseline (what actually exists)

### Backend

- FastAPI + SQLAlchemy 2.0 + PostgreSQL. Alembic exists with four revisions; production startup requires `alembic upgrade head`.
- Staff auth: Argon2 passwords, HS256 JWT with `sub`/`mid`/`rid`, 480-minute lifetime, in-memory lockout. No `realm` claim, no token version, no refresh token.
- Tenancy: `restaurants`, `restaurant_settings`, `restaurant_memberships`. `Restaurant.status` exists but is only a string; no suspension gate in `get_actor`.
- Audit: `audit_events` is **tenant-scoped** (`restaurant_id NOT NULL`). It is not a platform audit log.
- Notifications: `outbox_events` is tenant-scoped and no worker processes it.
- Subscriptions: `subscription_plans`, `subscriptions`, `subscription_billing_info` are **tenant-scoped**; `subscriptions` is unique per **membership**, not per tenant. This is not SaaS billing.
- Entitlements: `app/modules/entitlements/` is a one-line stub.
- Platform: `app/modules/platform/` is a one-line stub.
- No invoices, payments (platform), plans (platform), feature flags, support, platform settings, platform admins, MFA, refresh tokens, email delivery, scheduler, or payment gateway.
- Seed data: one demo restaurant, five staff logins, menu, tables, payment methods. No platform data.

### Frontend

- React 18 + React Router 6 SPA. Staff app under `/staff`, permission-gated sidebar, `useAuth()` from `/api/v1/me`.
- Token stored in `sessionStorage` under `rest.access_token`.
- No `/admin` route, no separate auth context, no platform API client.
- No frontend test runner; verification is currently build + manual browser smoke.

### Tests

- Backend suite is green at planning time.
- Structure tests enforce: no new cross-module imports beyond the frozen baseline, no `app.api` imports from module internals, no naive `datetime.now()`.
- Integration tests use the real PostgreSQL database and `drop_all`/`create_all`; fixtures reseed. Any platform seed data must be fixture-driven or it will be wiped.

## 4. Gap analysis

| Capability | Today | Needed for the spec | Size | Phase |
|------------|-------|---------------------|------|-------|
| Platform identity | none | `platform_admins`, roles, status | M | PA-0 |
| Platform auth | staff JWT only | separate secret, `realm`, MFA, HttpOnly cookies, CSRF, refresh rotation, step-up | L | PA-0 |
| Platform authorization | tenant roles only | explicit platform permission map | M | PA-0 |
| Platform audit | tenant-only `audit_events` | `platform_audit_logs`, append-only, reason | M | PA-0 |
| Force logout | none | token version on memberships + platform admins | M | PA-0 |
| Tenant suspension | status string only | enforcement gate + lifecycle actions | M | PA-1.2 |
| Dashboard metrics | none | defined aggregate formulas + endpoint | M | PA-1.1 |
| Tenant management | none | list/search/detail/create/suspend/reactivate | L | PA-1.1/1.2 |
| Platform plans | tenant-scoped plans | `platform_plans` with entitlements JSON | M | PA-1.1/1.2 |
| Platform subscriptions | tenant-scoped, per membership | `platform_subscriptions`, one active per tenant | L | PA-1.2 |
| Invoices | none | `platform_invoices` + lines, manual lifecycle | L | PA-1.3 |
| Platform payments | none | `platform_payments`, unique reference, optional private evidence, idempotent confirmation, append-only events | L | PA-1.3 |
| Refund recording | none | request/approve/complete split, participant fields, external refund reference; threshold deferred | M | PA-1.3 |
| Platform users/roles | none | admin CRUD + last-superadmin invariant + two-superadmin gate | M | PA-1.4 |
| Platform settings | none | key/value settings + audit | S | PA-1.4 |
| Diagnostics | `/health` only | tenant-scoped read-only checks | M | PA-1.4 |
| Frontend admin | none | separate admin build/origin, login/MFA, pages | L | PA-0/PA-1 |
| Email delivery | none | invitations, suspension notices, renewal reminders | L | PA-2 |
| Background jobs | none | trial expiry, dunning, usage rollups | L | PA-2 |
| Payment gateway | none | Stripe or local provider, webhooks | XL | PA-3 |
| Support tickets | none | `platform_support_*` tables + UI | L | PA-2 |
| Feature flags | none | flags + tenant targeting | M | PA-2 |
| Analytics/reports | none | date-range aggregates, export | L | PA-2 |
| Promotions/CMS/API | none | separate product surfaces | XL | PA-3 |

## 5. Architectural blockers to resolve before PA-1

### B1. The subscription tables are semantically wrong for SaaS billing

`SubscriptionPlan` requires `restaurant_id`; `Subscription` is unique per membership. A SaaS plan is platform-wide, and a tenant has one subscription, not one per staff member. Reusing these tables would corrupt both the tenant subscription screen and the platform billing model.

**Decision:** create parallel `platform_*` tables and freeze the existing tenant-scoped subscription module. Do not migrate or delete it in MVP. See `PA-ADR-002`.

### B2. The auth model has no realm claim and no revocation

`decode_access_token` accepts any HS256 token signed with `settings.secret_key`, and `get_actor` looks up a membership. A platform token would be structurally similar. Without an explicit realm claim, a coding mistake can cross realms.

**Decision:** add `realm: "staff"` to staff tokens, use a separate `platform_secret_key` and `realm: "platform"` for platform tokens, and add `token_version` to both identities. See `03-architecture-and-security.md`.

### B3. Audit is tenant-scoped

`AuditEvent.restaurant_id` is non-nullable. Platform actions like “created a plan” or “disabled an admin” have no tenant. A nullable tenant column on the existing table would weaken tenant audit queries.

**Decision:** separate `platform_audit_logs` with a nullable `restaurant_id` and no FK to tenants, so logs survive tenant archival. See `04-data-model.md`.

### B4. No email or worker

Invitations, suspension notices, and renewal reminders all want email. There is no mail transport and no worker. Building those silently inside MVP would add two infrastructure projects.

**Decision:** MVP uses one-time invitation tokens displayed/copied by the platform admin; in-app notifications only. Email and scheduled reminders are PA-2. See `PA-ADR-004`.

### B5. Manual billing must be a first-class path, not a “mark as paid” button

The spec’s payment section leans on provider events. The existing master plan defers Stripe (`D6`) and the repo has no gateway. Manual confirmation is therefore the entire control surface, so it needs anti-fraud rules.

**Decision:** PA-1 implements manual invoices and manual payment confirmation with a unique transaction reference, a verifier, optional private evidence, idempotency, and immutable events. Refunds are manual and record requester/approver/completer plus the external refund reference; the monetary second-approval threshold is deferred until a financial risk policy exists. Gateway integration is PA-3. See `PA-ADR-005`.

### B6. Same-origin admin is not acceptable for production

A separate JWT secret isolates the token-signing key but not the browser origin. If malicious JavaScript runs on the tenant origin, it can read any JS-accessible admin storage and drive authenticated requests. The platform realm can affect every tenant.

**Decision:** production requires `admin.{platform_domain}` as a separate build/deployment, HttpOnly access + refresh cookies, CSRF protection, and a CORS allowlist. Same-origin `/admin` is local-dev only. See `PA-ADR-003` and `PA-ADR-010`.

### B7. Operational and legal facts are not engineering assumptions

The plan can design configurable invoice templates and configurable retention, but it cannot invent the production domain, the DNS/TLS owner, the Nepali tax treatment, or the legally required retention periods. Treating guesses as facts would create security, tax, and data-protection risk.

**Decision:** The domain/DNS/TLS ownership is **PA-ADR-011 (Open)**. Platform invoices are distinguished from restaurant sales invoices and remain `tax_treatment=UNCONFIRMED` until a Nepali tax professional signs off. Retention is category-specific and requires legal/accounting confirmation. SSO is not committed to any phase.

## 6. Feasibility and effort

| Scope | Engineering estimate | Confidence | Notes |
|-------|---------------------|------------|-------|
| PA-0 architecture/security foundation | 3–3.5 weeks | High | Auth/MFA/audit plus cookie/CSRF/origin and the separate admin build |
| PA-1 commercial MVP | 9–10 weeks | Medium | Tenant lifecycle + manual billing with anti-fraud + the admin UI are the long poles |
| PA-2 operational maturity | 8–10 weeks | Low–medium | Email/worker/export/analytics are new infrastructure |
| PA-3 advanced | 8–12 weeks | Low | Gateway, CMS, and developer API are separate products; SSO is not committed |

Assumptions: one senior engineer with full context, no meeting load, no production incidents, and the current staff app frozen. Add 30–40% calendar overhead per the master plan. A second engineer parallelizing frontend during PA-1 pulls the MVP calendar toward ~12–14 weeks.

## 7. Recommendation

1. **Approve the MVP boundary** in `02-scope-and-priorities.md`.
2. **Approve PA-ADR-001/002/003/005/010** before writing code. These determine whether the work is safe.
3. **Build PA-0 and PA-1 only.** Then stop, operate with real tenants, and re-evaluate PA-2 from evidence (support volume, payment failures, onboarding drop-off) — not from the wishlist.
4. **Keep the spec’s P2/P3 sections in the parking lot**, not in the active backlog. This is the mechanism that prevents distraction.

## 8. Conditions that would change this recommendation

- A paying tenant requires a gateway before PA-1 ships → pull a narrow gateway slice forward only with a new ADR and an explicit PA-1 scope cut.
- A support contract requires ticketing before PA-2 → build a read-only support queue as a PA-1 extension, not the full ticket system.
- A regulatory requirement forces hard deletion before PA-2 → pull the approved deletion workflow forward, with export and retention gates.
- The team grows beyond two engineers → parallelize PA-1.3 (billing) and PA-1.4 (admin/settings) only after PA-1.1/1.2 contracts are frozen.
