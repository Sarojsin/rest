# 07 — Implementation Roadmap

**Model:** engineering weeks for one senior engineer with full context. Calendar = engineering × 1.3–1.4 plus review/QA. No phase starts before the previous phase’s exit criteria are met.

**Task ID format:** `PA-<phase>.<sequence>` — every PR must cite one.

---

## 0. Prerequisites (before PA-0)

| # | Prerequisite | Owner | Done when |
|---|--------------|-------|-----------|
| P-1 | Approve PA-ADR-001 through PA-ADR-010 (at minimum 001, 002, 003, 005, 009, 010) | Product + tech lead + security | Decision recorded in `09-risks-and-decisions.md`; §2.1 decisions accepted. PA-ADR-011 stays **Open** and must be accepted before PA-1.4. |
| P-2 | Freeze the staff/tenant feature surface for the duration | Product | No new tenant features merged during PA-1 |
| P-3 | Backend + frontend suites green | Eng | `pytest -q` and `npm run build` pass |
| P-4 | Alembic is at head; dev DB reachable | Eng | `alembic current` == head |
| P-5 | Add `pyotp` dependency (TOTP) | Eng | `pyproject.toml` updated; tests can generate codes |
| P-6 | Decide email strategy for MVP (none) | Product | Confirmed: invitation tokens are copied manually |
| P-7 | Confirm platform currency and fiscal year | Product + finance | NPR; `fiscal_year_start_month=7`; recorded in settings allowlist |
| P-8 | Provide the actual `platform_domain` and name the registrar/DNS/hosting/TLS owner (PA-ADR-011) before PA-1.4 | Ops / company owner | Three hosts resolve, TLS valid, CORS origins configured; credentials in a company password manager |
| P-9 | Choose the private payment-evidence store (bucket/path + access policy); evidence is optional in PA-1 | Security + ops | Documented in `11-operations-runbook.md`; signed-URL access restricted and audited |
| P-10 | Name the **real** primary Super Admin, secondary Super Admin, and emergency recovery owner, plus where recovery/break-glass credentials are stored | Ops / company owner | Recorded; secondary invitation planned for PA-1.4; no fictional seed |

**Do not start PA-0 if P-1 is open.** The identity, origin, and cookie decisions change the migration and the frontend build.

---

## 1. PA-0 — Architecture and security foundation (3–3.5 weeks)

**Goal:** a platform admin can authenticate with password + TOTP over HttpOnly cookies from the admin origin, hit a permission-guarded endpoint, and leave an audit trail. No tenant management yet.

| ID | Task | Est. | Depends on | Exit evidence |
|----|------|------|------------|---------------|
| PA-0.1 | Add platform config keys; fail startup on missing/matching secret, missing origins, non-host-only cookies, `Secure=false` outside local | 0.5d | — | Config tests |
| PA-0.2 | Add `realm: "staff"` to staff JWT; reject wrong realm in `get_actor` | 0.25d | — | Cross-realm test |
| PA-0.3 | Create `platform_admins`, `platform_refresh_tokens`, `platform_one_time_tokens`, `platform_audit_logs` models + Alembic revision | 1d | PA-0.1 | Migration up/down; model import |
| PA-0.4 | Platform permission map + `get_platform_admin` + `require_platform_permission` + maker–checker helpers | 0.75d | PA-0.3 | Unit tests for every role |
| PA-0.5 | Login, MFA enrollment/verify, recovery codes, **HttpOnly access/refresh cookies**, refresh rotation + reuse detection, logout, `/me`, `/sessions` | 2.5d | PA-0.3/0.4 | API tests incl. cookie flags, rotation, reuse, revocation |
| PA-0.6 | **CSRF double-submit + Origin allowlist + CORS with credentials**; global guard on non-GET platform routes | 1d | PA-0.5 | Missing/mismatched token, evil-origin tests |
| PA-0.7 | Step-up guard for destructive actions (fresh MFA, `auth_time`) | 0.5d | PA-0.5 | Stale/fresh tests |
| PA-0.8 | `write_platform_audit` service + reason validation + redaction allowlist | 1d | PA-0.3 | Audit tests; no secret in payload |
| PA-0.9 | Bootstrap first superadmin (idempotent) + development-only seed for fixture admins | 0.5d | PA-0.3 | Empty-DB test; production guard; no production second-admin seed |
| PA-0.10 | Staff `token_version` on memberships + claim check + force-logout service stub | 1d | PA-0.2 | Revocation test |
| PA-0.11 | Tenant status guard + in-flight allowlist plumbing (no platform action yet) | 1d | PA-0.10 | New-order blocked, in-flight bill allowed |
| PA-0.12 | **Separate admin build entry** (`admin.html`, `src/admin.tsx`, `vite.admin.config.ts`), admin-origin config, CSP skeleton | 1d | PA-0.5/0.6 | Two clean builds; admin bundle excludes tenant pages; tenant bundle excludes admin pages |
| PA-0.13 | Admin shell: router, layout, auth provider (cookie-based), login, MFA, guard, CSRF client | 2d | PA-0.5/0.6/0.12 | Browser smoke, no JS token storage |
| PA-0.14 | Platform API composition + OpenAPI tags | 0.25d | PA-0.4/0.5 | `/api/platform` reachable |
| PA-0.15 | PA-0 security tests + docs + threat-model updates | 1d | all | Phase gate |

**PA-0 exit criteria**

- A superadmin logs in with password + TOTP; the response body contains **no tokens**.
- Cookies are `HttpOnly; Secure; SameSite=Strict` with host-only scope and correct paths in a production-like config.
- A state-changing request without `X-CSRF-Token` returns `403 CSRF_INVALID`; a request from a non-allowlisted origin is rejected.
- A staff token on `/api/platform/me` returns 401 `WRONG_REALM`; a platform token on `/api/v1/me` returns 401.
- A mutation without a reason returns 422; a successful mutation writes exactly one audit row.
- A stale admin gets `STEP_UP_REQUIRED` on a destructive route.
- Disabling an admin or bumping `token_version` kills existing access tokens; refresh-family revocation works.
- Bootstrap works on an empty DB and is idempotent.
- The admin build serves from the admin entry with no tokens in `localStorage`/`sessionStorage`; 0 console errors.
- `npm run build` and `npm run build:admin` both pass.

**PA-0 explicitly does not include:** tenants, plans, invoices, dashboard metrics, support, notifications, payment evidence storage.

---

## 2. PA-1 — Commercial MVP (9–10 weeks)

### 2.1 PA-1.1 — Read surfaces and dashboard (2–2.5 weeks)

| ID | Task | Est. | Depends on |
|----|------|------|------------|
| PA-1.1.1 | `platform_plans`, `platform_subscriptions` models + migration | 1d | PA-0 |
| PA-1.1.2 | Dev seed: plans + demo subscription | 0.5d | PA-1.1.1 |
| PA-1.1.3 | Tenant directory service (`platform_directory`) + ADR-009 baseline edge | 1d | PA-0 |
| PA-1.1.4 | `GET /tenants` + `GET /tenants/{id}` + counts | 1d | PA-1.1.3 |
| PA-1.1.5 | `GET /plans`, `GET /subscriptions` | 1d | PA-1.1.1 |
| PA-1.1.6 | `GET /dashboard` with metric dictionary + SQL aggregates | 2d | PA-1.1.4/1.1.5 |
| PA-1.1.7 | `GET /diagnostics/health`, `GET /tenants/{id}/diagnostics` | 1d | PA-1.1.4 |
| PA-1.1.8 | Frontend: dashboard, tenant list/detail, plan list, subscription list | 3d | PA-1.1.4/1.1.5 |
| PA-1.1.9 | Backend + UI tests for read surfaces | 1d | all |

**Exit:** dashboard numbers match fixtures; list/search/filter/pagination work; every page has loading/empty/error/forbidden states; no mutation buttons yet.

### 2.2 PA-1.2 — Tenant and subscription lifecycle (2.5–3 weeks)

| ID | Task | Est. | Depends on |
|----|------|------|------------|
| PA-1.2.1 | `platform_plans` CRUD + archive + price snapshot rules | 2d | PA-1.1.1 |
| PA-1.2.2 | Tenant create (shell + owner invite) + invite accept endpoint/page + slug/email conflicts | 2d | PA-1.1.3 |
| PA-1.2.3 | Suspend/reactivate/force-logout + reason + typed confirm + audit | 2d | PA-1.2.2, PA-0.10/0.11 |
| PA-1.2.4 | Subscription create/change/extend-trial/cancel/reactivate + events | 2d | PA-1.1.1 |
| PA-1.2.5 | Audit log API + filters + export (≤31 days) | 1d | PA-0.7 |
| PA-1.2.6 | Frontend: tenant create/detail actions, plan editor, subscription actions, audit viewer | 3d | PA-1.2.1–1.2.5 |
| PA-1.2.7 | Lifecycle + audit tests | 1d | all |

**Exit:** full tenant lifecycle works; suspension blocks new orders but allows bill completion; force logout kills sessions; plan archive blocked while live; every mutation audited; last-superadmin invariant still holds.

### 2.3 PA-1.3 — Manual billing with anti-fraud controls (3–3.5 weeks)

| ID | Task | Est. | Depends on |
|----|------|------|------------|
| PA-1.3.1 | Invoice + line models, totals, fiscal-year numbering (`INV-{FY}-{seq}` + sequence table), status machine | 2d | PA-1.1.1 |
| PA-1.3.2 | `POST /invoices`, `GET /invoices`, `GET /invoices/{id}` | 1.5d | PA-1.3.1 |
| PA-1.3.3 | `POST /invoices/{id}/void` (number preserved) | 0.5d | PA-1.3.1 |
| PA-1.3.4 | Invoice/payment models + events ledger + unique normalized reference + manual verification + `POST /invoices/{id}/pay` transaction + idempotency (**no evidence-store dependency**) | 2d | PA-1.3.1 |
| PA-1.3.4b | **Optional** evidence metadata + private object upload + short-lived signed URL endpoint; enabled only when P-9 private storage/access policy is configured | 1d | PA-1.3.4, P-9 |
| PA-1.3.5 | `POST /payments/{id}/void`; no amount-edit route | 0.5d | PA-1.3.4 |
| PA-1.3.6 | Refund request/approve/complete/reject flow with requester/approver/completer + external refund reference; **no threshold setting**; policy deferred | 2d | PA-1.3.4 |
| PA-1.3.7 | `GET /payments`, `GET /payments/{id}`, `GET /payments/{id}/events`, `GET /refunds`, `GET /invoices/{id}/payment-instructions` | 1d | PA-1.3.4/1.3.6 |
| PA-1.3.8 | MRR/ARR/collections/pending/failed metrics wired to billing tables | 1d | PA-1.3.4 |
| PA-1.3.9 | Frontend: invoice list/detail/create + issuer/tax notice, pay dialog with transaction reference, payment instructions, void, refund request/approve/complete, refund queue; evidence upload UI only when PA-1.3.4b is enabled | 3.5d | PA-1.3.2–1.3.8 |
| PA-1.3.10 | Billing tests: totals, replay, already-paid, duplicate reference, manual verification without evidence, optional evidence/signed URL (skipped when the store is not configured), refund bounds, participant/reference fields, period extension, immutable events, SaaS/QR isolation | 2.5d | all |

**Exit:** invoice → payment → subscription extension is atomic; replay returns the original payment; a duplicate reference is rejected; a transaction reference is required or the cash exception is audited; **manual recording works with no evidence store**; evidence, when configured and supplied, is private with signed-URL access; refunds record requester/approver/completer and external reference with no fixed threshold; confirmed amounts cannot be edited; dashboard money matches the ledger; no client-supplied total is trusted; platform billing cannot touch restaurant QR payments.

**Dependency handling:** PA-1.3.4 (invoice/payment/reference/verification/audit) does not depend on P-9. The evidence upload in PA-1.3.4b is enabled only when the private store and access policy exist; until then the UI hides upload and accepts reference-only payments. Invoice issuer/PAN/VAT fields and numbering are built in PA-1.3.1–1.3.3 without waiting for tax sign-off; `tax_treatment` stays `UNCONFIRMED` and the production template is not finalized.

### 2.4 PA-1.4 — Platform users, settings, launch hardening (2 weeks)

| ID | Task | Est. | Depends on |
|----|------|------|------------|
| PA-1.4.1 | Platform user invite/accept, role/disable/reset-MFA/reset-password + last-superadmin invariant + two-superadmin gate | 2d | PA-0.5 |
| PA-1.4.2 | Platform settings API + allowlist validation + fiscal/trial/invoice-issuer/payment-instruction/evidence/export keys (no refund threshold) | 0.75d | PA-0.8 |
| PA-1.4.3 | Profile: change name/password, own MFA reset, own sessions, revoke-all | 1d | PA-0.5 |
| PA-1.4.4 | Frontend: users, settings, profile, diagnostics, refund queue polish | 2d | PA-1.4.1–1.4.3 |
| PA-1.4.5 | Rate limiting, generic auth errors, redaction audit, CSP + security headers | 1d | PA-0.5 |
| PA-1.4.6 | **Production origin/cookie verification**: DNS, TLS, host-only cookies, CORS, CSRF, `Set-Cookie` inspection in a staging environment (requires PA-ADR-011) | 1.5d | PA-0.6/0.12, P-8 |
| PA-1.4.7 | **Launch gates**: two real superadmins enrolled + recovery drill, domain/DNS/TLS owner confirmed, evidence store live, backup restore test passed, category-specific retention policy approved, Nepali tax-professional invoice sign-off, export scope approved | 2d | PA-1.4.1/1.4.6 |
| PA-1.4.8 | Full acceptance script + docs + runbook updates | 1d | all |

**Exit:** all PA-1 acceptance criteria in `02-scope-and-priorities.md` §8 pass; structure tests green; both frontend builds clean; production-origin checks signed off; two real active superadmins; restore drill recorded; retention and tax sign-offs recorded; runbook reviewed.

---

## 3. PA-2 — Operational maturity (8–10 weeks, conditionally)

Do not start until a trigger in `02-scope-and-priorities.md` §5 is met. The separate admin origin is already a PA-0/PA-1.4 deliverable; PA-2 only completes it if launch was granted a documented exception.

Suggested order:

1. **Email + notification infrastructure** (2 wk): one transport, templates, retries, delivery log. Unblocks invitations and suspension/renewal notices.
2. **Automated reminders + worker** (2 wk): trial expiry, renewal reminders, overdue invoices, cleanup; every job carries an explicit `tenant_id` and is idempotent.
3. **Data export + category-specific retention workflows** (1.5 wk): the PA-1.4-approved export scope, artefact expiry, deletion-request intake/approval, legal-hold handling; execution remains PA-3.
4. **Monitoring, backups, and restore drills** (1.5 wk): dashboards, alerting, daily backups, monthly restore test, incident records.
5. **Support tickets** (2 wk): tickets, messages, internal notes, tenant-visible replies, SLA fields.
6. **Onboarding + analytics** (1.5 wk): checklist, funnel events, date-range reports, CSV export.
7. **Admin-origin completion** (0.5 wk, conditional): finish the split if a documented launch exception was used; remove the same-origin fallback and re-verify cookies/CORS.
8. **Feature flags + integrations** (2 wk): flag targeting, provider configs, webhook event log.

Each item gets its own task table before coding. No item is “while we are in there”.

---

## 4. PA-3 — Advanced platform (8–12 weeks, separate business case)

- Gateway payments (eSewa/Khalti/Stripe), webhooks, reconciliation.
- Promotions, coupons, referrals.
- CMS.
- Developer API/keys.
- SSO/OIDC/SAML only if a future business case exists (`PL-021`); **not promised in PA-3**.
- Advanced usage analytics and customer-success automation.
- DB-backed role editor.
- Time-limited, read-only impersonation (dedicated security review + tenant notice).

PA-3 requires a new roadmap revision. It is not estimated in detail here on purpose.

---

## 5. Definition of Done (every task)

A task is done only when:

- [ ] Model + migration (if schema changed) and rollback tested.
- [ ] Pydantic schema with validation and `extra="forbid"` where appropriate.
- [ ] Router with correct permission + step-up + reason + CSRF.
- [ ] Audit row written in the same transaction for mutations; payment events appended where applicable.
- [ ] Backend tests: happy path, validation, permission, cross-realm, cross-tenant (where relevant).
- [ ] Security tests: cookie flags, CSRF, origin rejection, refresh rotation/reuse, revocation.
- [ ] Frontend page/component with loading, empty, error, forbidden states.
- [ ] No credentials in `localStorage`/`sessionStorage`; `credentials: "include"` + CSRF header.
- [ ] Permission-gated nav and action buttons.
- [ ] No secrets/PII in responses or logs.
- [ ] OpenAPI docs updated.
- [ ] Plan files updated if behavior differs from this document.
- [ ] PR references `PA-x.y`.

## 6. Estimation and re-planning rules

1. If a phase exceeds its estimate by 25%, stop feature work and re-plan. Do not borrow time from PA-2.
2. If a task reveals a missing prerequisite (email, worker, gateway), move the dependent feature to the parking lot; do not build the prerequisite inside the task.
3. If two tasks need the same new cross-module edge, write one ADR and one service; do not duplicate SQL.
4. If a security test fails, the phase does not exit, regardless of the demo.
5. Estimates exclude production support and review latency. Add 30–40% calendar overhead.
6. The roadmap is revised only at a phase boundary, never mid-phase.

## 7. Suggested sprint shape

For a two-week cadence:

- Sprint 1: PA-0.1–0.9 (foundation, auth, no UI).
- Sprint 2: PA-0.10–0.15 + PA-1.1.1–1.1.4 (origin/build + foundation gate + reads).
- Sprint 3: PA-1.1.5–1.1.9 + PA-1.2.1–1.2.2 (dashboard + plan CRUD + tenant create).
- Sprint 4: PA-1.2.3–1.2.7 (lifecycle + audit).
- Sprint 5: PA-1.3.1–1.3.6 (billing backend: invoices, payments, refunds).
- Sprint 6: PA-1.3.7–1.3.10 + PA-1.4.1–1.4.3 (billing UI/queue + admin/settings).
- Sprint 7: PA-1.4.4–1.4.8 + launch gates + acceptance + buffer.

If the team has two engineers, parallelize PA-1.3 backend with PA-1.2 frontend only after the API contracts in `05-api-contracts.md` are frozen.
