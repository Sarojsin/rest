# 09 — Risks, Decisions, and Open Questions

**Status:** ADRs below are **proposed** unless marked otherwise. PA-ADR-011 is **Open**: it cannot be accepted until the real production domain and its responsible owner are supplied. PA-0 cannot start until PA-ADR-001, -002, -003, -005, -006, -008, -009, and -010 are accepted. The decisions in §2.1 are already settled and are binding on implementation.

**Revision note (2026-11-04b):** Reconciled with the owner's operational/legal guidance. PA-ADR-011 makes domain/DNS/TLS ownership an explicit open decision instead of an assumed value. Payment evidence is now **optional** in PA-1, stored only in private object storage as an object key, and served through short-lived signed URLs. Refunds no longer use a fixed monetary dual-approval threshold; the threshold is deferred until a financial risk policy exists, and refund execution is manual and external in PA-1. The second superadmin must be a real named person, not a seeded placeholder. Nepal invoice/tax requirements and category-specific retention are launch gates requiring professional sign-off. SSO is no longer a PA-3 commitment.

---

## 1. Decision records (ADRs)

Format: context → decision → consequences → alternatives.

### PA-ADR-001 — Platform admins are a separate identity store

**Status:** Proposed
**Context:** The repo has one global `users` table used by tenant staff. Master decision D4 says “one global identity per person”. Plan `08` describes a `platform_admins` realm with a separate secret and cookie. Reusing `users` would let a tenant owner’s credential be linked to platform access and would blur realm isolation.
**Decision:** Create `platform_admins` with its own credentials, roles, MFA, token version, and refresh tokens. Do not link it to `users` in PA-1. Require:
- at least **two active superadmins** before commercial launch (bootstrap creates the **primary** admin; the **secondary** admin is a real named person who is invited and enrolled during PA-1.4 — no fictional or shared “second admin” account is created to satisfy a checklist),
- a named **primary** Super Admin, **secondary** Super Admin, and **emergency account-recovery owner**, with the storage location for recovery codes and break-glass credentials documented before launch (see `11-operations-runbook.md` §2–§3),
- TOTP MFA + single-use recovery codes for every admin,
- account lockout and rate limiting,
- `token_version` + refresh-family revocation for session revocation,
- invite-only account creation (no self-signup),
- the break-glass procedure in `11-operations-runbook.md` §3.
**Consequences:**
- Strong realm isolation; a tenant breach does not directly yield a platform credential.
- A person who is both a tenant owner and a platform admin needs two accounts. Acceptable for a small platform team; revisit in PA-3 if it becomes operationally painful.
- Operations must maintain a second real superadmin and test recovery; this is a launch gate, not an optional nicety. If a real second person cannot be named, commercial launch is blocked.
- Deviates from D4; this ADR is the explicit exception.
**Alternatives:** `users` + `platform_admin_memberships` (rejected: weaker isolation, more complex authorization); external IdP (deferred, not committed).

### PA-ADR-002 — New platform billing tables, existing tenant subscription tables frozen

**Status:** Proposed
**Context:** `subscription_plans` requires `restaurant_id`; `subscriptions` is unique per membership. SaaS plans are platform-wide and a tenant has one subscription. Reusing the tables would corrupt the tenant-facing subscription screen and make per-tenant plans meaningless.
**Decision:** Add `platform_plans`, `platform_subscriptions`, `platform_subscription_events`, `platform_invoices`, `platform_invoice_lines`, `platform_payments`. Leave the existing `subscription_*` tables untouched in PA-1. Mark them “legacy tenant subscription surface” in docs.
**Consequences:**
- No data migration risk; existing tests and UI keep working.
- Two “subscription” concepts coexist temporarily. The platform UI must label its own clearly; the tenant UI keeps its current label.
- A later cleanup (rename/deprecate) needs its own ADR after PA-1.
**Alternatives:** migrate the existing tables (rejected: high risk, ambiguous semantics); reuse with nullable `restaurant_id` (rejected: breaks constraints and tenant queries).

### PA-ADR-003 — Separate admin origin required before commercial launch

**Status:** Proposed (security-sensitive; requires explicit acceptance)
**Context:** A separate JWT secret does not provide browser-origin isolation. If malicious JavaScript executes on the same origin as the admin UI, it can read any JS-accessible storage and make authenticated requests with the admin’s cookies. The platform realm can affect every tenant, so origin isolation is a commercial-launch requirement, not a nice-to-have.
**Decision:**
- Production topology:
  - `www.{platform_domain}` (or `app.{platform_domain}`) — tenant web app
  - `admin.{platform_domain}` — Super Admin SPA
  - `api.{platform_domain}` — FastAPI
- The actual `platform_domain`, registrar, DNS provider, hosting account, and TLS owner are **not assumed**. They are an open operational decision in **PA-ADR-011**; this ADR only fixes the topology shape. Do not hard-code a domain in code, docs-as-config, or `.env` examples.
- The admin SPA is a **separate build entry** (same repo, `src/admin.tsx` + `admin.html` + `vite.admin.config.ts`) deployed only to the admin origin. The tenant bundle is not served there.
- Cookies are host-only to the API origin, `HttpOnly`, `Secure`, `SameSite=Strict`; CORS allows only the admin and tenant origins with credentials.
- Local development may use same-origin `/admin` through the Vite proxy. That is not a production configuration.
- PA-0 builds the config-driven origins, separate admin entry, CORS allowlist, and host checks. PA-1.4 verifies the production topology and makes it a launch gate.
- If same-origin is ever used in production, it requires a written security acceptance, a risk-register entry, and compensating controls (strict CSP, no third-party scripts, short cookie lifetime). It is not the default.
**Consequences:**
- Strong browser-origin isolation; an XSS in the tenant app cannot read or drive the admin session.
- More deployment work: DNS, wildcard/individual TLS, CORS, cookie domain/path, separate CSP, and a second static deployment. Estimate +3–5 days in PA-0/PA-1.4.
- The admin bundle is smaller and has a distinct CSP, reducing attack surface.
- Commercial launch gate: admin origin live, cookies verified, CORS locked down, no same-origin fallback in production.
**Alternatives:** same-origin `/admin` (rejected for production; allowed only in local dev); iframe (rejected: worse isolation, confusing auth); separate backend (deferred: not needed for origin isolation).

### PA-ADR-004 — No email delivery in MVP

**Status:** Proposed
**Context:** Invitations, suspension notices, and renewal reminders want email. There is no mail transport, template system, retry queue, or delivery log.
**Decision:** MVP returns one-time invitation/reset links that the platform admin copies and sends through an existing channel. In-app notifications only. Email is PA-2.
**Consequences:**
- Tenant onboarding is manual and depends on the operator.
- No automated suspension/renewal communication; the audit log and tenant detail are the source of truth.
- Avoids building two infrastructure projects inside the commercial MVP.
**Alternatives:** SMTP directly in the request (rejected: no retry, blocks requests, poor deliverability); transactional email SaaS (deferred: vendor/security review).

### PA-ADR-005 — Manual billing only in PA-1, with anti-fraud controls

**Status:** Proposed
**Context:** Master decision D6 defers the gateway. The repo has no provider integration. The spec’s automated payment flow assumes webhooks and reconciliation. Manual confirmation by a human is the whole control surface, so it needs explicit anti-fraud rules rather than a generic “mark as paid” button.
**Decision:** PA-1 supports manual invoices and manual payment confirmation only. Gateway integration, webhooks, and automated reconciliation are PA-3. Manual billing must satisfy all of the following:
1. **Unique transaction reference.** Every payment requires a platform-unique reference (`provider_reference`); a partial unique index plus a normalized-value check rejects a second confirmation with the same reference.
2. **Verifiable reference is the requirement; evidence is optional.** A payment must carry a verifiable external reference (bank slip / eSewa / Khalti transaction id) plus the channel. A screenshot or other evidence document is **optional** in PA-1: `transaction_reference` + the Super Admin's verification record is sufficient when evidence is unavailable. When evidence is supplied it is stored in a **private object-storage bucket**; PostgreSQL stores only the object key/path, never the bytes and never a public URL. Viewing uses short-lived signed URLs restricted to the payment record and to finance/admin roles. Uploads validate content type and size, never trust the original filename, and are excluded from public URLs and logs. “Cash, no reference” is a privileged exception that requires a reason and is flagged in the audit trail.
3. **No duplicate confirmation.** Confirmation is idempotent: `POST /platform/payments/{id}/confirm` requires an `Idempotency-Key`; the payment row is locked `FOR UPDATE`; a payment already in `CONFIRMED` returns the original result instead of creating a second ledger entry.
4. **Verifier recorded.** `verified_by_admin_id` and `verified_at` are mandatory. The verifier cannot be the admin who created the invoice when the platform has more than one admin (maker–checker); if only one admin exists, the action is allowed but flagged `single_admin_confirmation`.
5. **Refunds are manual and recorded, with no automated execution.** PA-1 does **not** call a payment provider to move money. A refund request records amount, reason, original payment reference, destination, and (when known) the external refund transaction reference. The system separately records who requested, approved, and completed the refund. The monetary threshold that makes a second approval mandatory is **deferred** until a written financial risk policy exists; while it is deferred, an authorised admin may approve and complete a refund but the record is flagged `single_admin_approval`. Refunds may also be executed outside the product initially, provided the plan and runbook state that the platform does not manage refund execution and the external reference is recorded.
6. **Immutable history.** `platform_payment_events` is append-only (`payment_created`, `payment_confirmed`, `refund_requested`, `refund_approved`, `refund_completed`, `refund_rejected`, `payment_voided`). No `UPDATE`/`DELETE` on events; corrections are new events.
7. **Confirmed amounts are immutable.** There is no endpoint that edits the amount of a confirmed payment. A wrong amount is corrected by voiding the payment (with reason + audit) and recording a new one. `platform_invoices` totals are derived from confirmed payments and are never typed in by hand.
8. **Separate payment worlds.** SaaS subscription payments/evidence recorded here are never mixed with a restaurant's customer QR payments or their evidence. They use different tables, routes, permissions, and storage prefixes. Restaurant sales invoices are likewise separate from platform subscription invoices.
**Consequences:**
- Revenue operations stay manual but are auditable and resistant to the common fraud/typo paths.
- Maker–checker for payment confirmation still encourages two billing-capable admins, reinforcing PA-ADR-001’s two-superadmin launch gate.
- Refunds are explicit, multi-participant records rather than an automated money movement. A later gateway/refund policy needs its own ADR.
- More states and endpoints (`requested`/`approved`/`completed`/`rejected` refunds) and more tests. Estimate +2–3 days in PA-1.3.
- No card data is stored, reducing PCI scope.
- Dunning and automatic renewal are PA-2/PA-3.
**Alternatives:** Stripe/eSewa/Khalti now (rejected: D6, scope, no webhook infrastructure); free-text “mark paid” (rejected: unauditable, duplicate-prone); mandatory evidence screenshots (rejected: excludes legitimate bank/QR payments where only a reference is available); fixed refund threshold now (rejected: no financial risk policy yet, so the number would be invented).

### PA-ADR-006 — Platform roles live in code for MVP

**Status:** Proposed
**Context:** The spec suggests `platform_admin_roles` and `platform_admin_permissions` tables. The existing staff app uses a code map (`ROLE_PERMISSIONS`), which is reviewable and testable.
**Decision:** MVP uses `PLATFORM_ROLE_PERMISSIONS` in `app/modules/platform/permissions.py`. A DB-backed role editor is PA-3.
**Consequences:**
- Adding a permission is a code change + test, not a data change.
- No runtime role creation; the four roles are fixed.
- Simpler authorization review and no migration for role definitions.
**Alternatives:** DB roles now (rejected: no customer need, more surface area).

### PA-ADR-007 — No impersonation in the pilot

**Status:** Proposed (locked by plan 08)
**Context:** “Login as tenant” is the highest-risk feature in the spec. It requires scoped tokens, tenant notice, time limits, read-only mode, and a dedicated audit trail.
**Decision:** Do not build impersonation in PA-1 or PA-2. Support uses read-only diagnostics. Reconsider only in PA-3 with a dedicated threat model and tenant-visible notice.
**Consequences:** support may need screenshots/logs from the tenant; acceptable at pilot scale.
**Alternatives:** read-only impersonation now (rejected: insufficient review time).

### PA-ADR-008 — Audit rows are written in the business transaction

**Status:** Proposed
**Context:** A separate audit write can succeed while the business change fails (phantom log) or fail while the change succeeds (missing log).
**Decision:** `write_platform_audit` uses the same `Session` and transaction as the mutation. If either fails, both roll back. Security events (login failures) use their own transaction because there is no business change.
**Consequences:** audit is consistent with state; a failed audit insert blocks the action, which is intentional.
**Alternatives:** outbox-based audit (deferred: complexity, eventual consistency).

### PA-ADR-009 — One documented platform→tenancy service edge

**Status:** Proposed
**Context:** Platform needs to create tenants and read counts. The structure test freezes cross-module imports. Raw SQL would duplicate tenant invariants; importing tenancy models directly would create a broader, less controlled edge.
**Decision:** Add `app/modules/tenancy/services/platform_directory.py` as the only cross-module seam, and add exactly one line to `tests/structure/couplings_baseline.txt`:
`platform -> tenancy : services.platform_directory`.
**Consequences:** one reviewable edge; all tenant mutations stay in the tenancy context; no direct model imports.
**Alternatives:** raw SQL (rejected: duplicates invariants); direct model imports (rejected: broad coupling).

### PA-ADR-010 — HttpOnly cookie authentication with CSRF protection

**Status:** Proposed (security-sensitive; supersedes the earlier sessionStorage design)
**Context:** The staff app stores its token in `sessionStorage`. That reduces persistence versus `localStorage` but does not protect against XSS — any script on the origin can read it. The platform realm can act on every tenant, so the admin session must not be readable by JavaScript at all.
**Decision:**
- **Access token:** `HttpOnly; Secure; SameSite=Strict; Path=/api/platform`, 15-minute lifetime. Never returned in a response body, never in JS-readable storage.
- **Refresh token:** `HttpOnly; Secure; SameSite=Strict; Path=/api/platform/auth`, 12-hour lifetime, opaque (not a JWT), rotated on every use. Reuse of a rotated token revokes the whole refresh family and emits a security audit event.
- **CSRF:** double-submit token — a non-HttpOnly `csrf_token` cookie plus a required `X-CSRF-Token` header on every state-changing request. The server also validates `Origin`/`Referer` against the configured admin origin. Missing/mismatched token → `403 CSRF_INVALID`.
- **CORS:** credentials allowed only for the configured admin and tenant origins; wildcard `*` is forbidden with credentials; unknown origins are rejected at the middleware.
- **Session revocation:** `token_version` on `platform_admins` invalidates all access tokens; refresh families can be revoked individually (“sign out everywhere”), per admin, on password change, on role change, and on MFA reset.
- **Step-up (MFA re-assert):** sensitive operations (refund approval/completion, tenant deletion, admin creation/role change, MFA reset, platform settings change, trial-exception grant) require a fresh MFA assertion within 5 minutes using `POST /platform/auth/step-up`.
- **Separate admin origin** is required before commercial launch (PA-ADR-003); cookies are host-only to the API origin.
- No JS-accessible token storage anywhere in the admin app (`localStorage` and `sessionStorage` are both forbidden for credentials).
**Consequences:**
- XSS can no longer exfiltrate the session token; it can still perform actions in the page context, which is why CSP, origin isolation, and step-up remain required.
- Every mutating frontend call needs the CSRF header; the shared admin API client attaches it centrally.
- Cookie/CSRF behaviour must be tested explicitly (flags, rotation, reuse detection, origin checks, revocation). Estimate +3–4 days in PA-0.
- Local dev uses `Secure=false` only when `ENV=local`; production startup fails if `Secure` is off.
**Alternatives:** access token in memory only (rejected: still XSS-readable during the session); access token in `sessionStorage` (rejected: XSS-readable, no origin isolation); bearer tokens in `Authorization` header (rejected for the admin app: no CSRF problem but token is JS-readable); SSO/OIDC (not committed to any phase; kept as a future capability, `PL-021`).

### PA-ADR-011 — Production domain, DNS, and TLS ownership

**Status:** Open (operational/legal decision, not an engineering assumption)
**Context:** The plan can define the topology, but it cannot invent the production domain, the registrar, the DNS provider, the hosting account, or the person who controls certificate issuance and renewal. A guessed domain becomes a real security and availability problem: cookies, CORS, HSTS, certificate renewal, and email identity all depend on it. Storing registrar or DNS credentials in the repository or `.env` files would put company infrastructure at risk.
**Decision (pending):** Before PA-0 deployment work and before commercial launch, the owner must record:
1. the actual production `platform_domain`;
2. the **registrar** account owner;
3. the **DNS provider** account owner;
4. the **hosting** account owner for the tenant, admin, and API deployments;
5. the person/role that controls **TLS certificate issuance and renewal**;
6. the company-controlled password manager or secret store where domain, DNS, and TLS credentials live (never the repository, never committed `.env` files).
The code will read origins from configuration; it will not embed a domain.
**Consequences:**
- PA-0 can build config-driven origins and local development, but PA-1.4 production verification cannot pass until this ADR is accepted.
- Certificate expiry and DNS hijack become owned operational risks rather than silent assumptions.
- No document claims a domain exists; every example remains `{platform_domain}`.
**Alternatives:** use a temporary staging domain and defer production (allowed for PA-0, not for commercial launch); assume the app will live on a subdomain of an existing site (rejected: owner has not confirmed it).

---

## 2. Decisions and open questions

### 2.1 Resolved decisions

These are decided; implementation must follow them. Changing one requires a superseding ADR.

| # | Decision | Policy | Where enforced |
|---|----------|--------|----------------|
| D-1 | Separate platform admin accounts | Yes from MVP. `platform_admins` is a distinct realm; no link to tenant `users`. (PA-ADR-001) | PA-0 |
| D-2 | Currency | NPR initially. All money columns carry `currency_code`; invoices, payments, and plans store their currency. No FX conversion or cross-currency totals in MVP. Multi-currency is `PL-024`. | PA-1.1/1.3 |
| D-3 | Who can issue refunds | The `billing` role (finance admin) and `superadmin` may request refunds. Every refund records requester, approver, and completer separately, plus the original payment reference and the external refund transaction reference. PA-1 does **not** automate refund execution. The monetary threshold for mandatory second approval is **deferred** until a written financial risk policy exists; while deferred, an authorised admin may approve and complete, flagged `single_admin_approval`. Refunds may be executed outside the product if the runbook states so and the external reference is recorded. | PA-1.3 |
| D-4 | Invoice numbering | `INV-{FY}-{000001}`, e.g. `INV-2082-000123`. `FY` is the Nepali fiscal year label from `fiscal_year_start_month` (default 7 = Shrawan). Sequence is per fiscal year, unique, gapless except for voided invoices which keep their number and are marked `VOID` (numbers are never reused). Generated inside the invoice transaction with a row lock on `platform_invoice_sequences`. | PA-1.3 |
| D-5 | Tenant access vs subscription status | Tenant status is access state (`ACTIVE`/`SUSPENDED`/`CANCELLED`). Trial is a subscription status (`TRIALING`). Never duplicate trial on the tenant. | PA-1.1/1.2 |
| D-6 | Suspension behaviour | Suspension blocks **new** orders (and new sessions/staff writes) but **preserves in-flight operations**: an open table can still place/finish its order, generate a bill, and settle payment for the current visit. The allowlist is exact: `GET` reads for staff already authenticated, order completion/cancel for orders created before suspension, bill generation, payment capture, and auth refresh. Everything else returns `403 TENANT_SUSPENDED`. | PA-1.2 |
| D-7 | Same-origin admin | Not allowed in production. `admin.{platform_domain}` is required before commercial launch; same-origin `/admin` is local-dev only. The domain itself is open in PA-ADR-011. (PA-ADR-003) | PA-0/PA-1.4 |
| D-8 | Trial extension limit | Configurable: `trial_extension_max_days_per_action` (default 30) and `trial_extension_max_days_total` (default 60). Exceeding either requires superadmin step-up MFA plus a mandatory reason; the audit event records both limits and the reason. | PA-1.2 |
| D-9 | SSO | **Not committed to any phase.** MVP and PA-3 are password + TOTP MFA. SSO/OIDC/SAML is a future capability for restaurant chains and enterprise customers (`PL-021`); the auth module is kept clean so it can be added later without rewriting realm isolation. Do not advertise SSO in PA-3 scope or pricing. | Not scheduled |
| D-10 | Tenant data export | Scope: tenant profile, memberships/staff, menu, orders, bills, payments, inventory, loyalty, reviews, and audit events for that tenant only. No platform-internal notes, no other tenants, no secrets. Format: JSON + CSV bundle. Retention: export artefacts deleted after `export_retention_days` (default 30); the audit event is kept permanently. Implemented in PA-2, but the scope and category-specific retention policy must be approved before commercial launch. | PA-2 |
| D-11 | MFA | Required for every platform admin (TOTP). 10 single-use recovery codes, hashed at rest, shown once. Recovery-code use is audited and forces re-enrolment. | PA-0 |
| D-12 | Admin account creation | Invite-only. A superadmin creates an invitation (one-time token, 24–72h expiry, bound to email + role); the invitee sets a password and enrols MFA before first use. No self-signup, no shared accounts, no invented “second admin”. | PA-0/PA-1.1 |
| D-13 | Platform permissions | Code map `PLATFORM_ROLE_PERMISSIONS` with four roles: `support`, `billing` (finance/billing admin), `ops`, `superadmin`; DB-backed editor is PA-3. (PA-ADR-006) | PA-0 |
| D-14 | Audit | `platform_audit_logs` is separate from tenant `audit_events` (which requires `restaurant_id`). Written in the business transaction. (PA-ADR-008) | PA-0 |
| D-15 | Impersonation | Not built in PA-1/PA-2. Reconsidered in PA-3 only with a threat model and tenant-visible notice. (PA-ADR-007) | PA-3 |
| D-16 | Email | No email transport in MVP; copyable one-time links. Email is PA-2. (PA-ADR-004) | PA-2 |
| D-17 | Payment gateways | None in MVP. Manual billing with the controls in PA-ADR-005. Gateways + reconciliation are PA-3. | PA-3 |
| D-18 | Payment evidence | **Optional in PA-1.** A transaction reference + verification record is sufficient. Evidence, when supplied, lives in a private object bucket; PostgreSQL stores only the key/path. Short-lived signed URLs, restricted to the payment and finance/admin roles. Validate content type and size; never trust the filename; never expose a public URL or log the object contents. | PA-1.3 |
| D-19 | Refund execution | Manual and external in PA-1. No provider API call, no automated money movement. Refunds may be handled entirely outside the product if documented; the in-product record still captures amount, reason, original reference, destination, external refund reference, requester, approver, and completer. | PA-1.3 |
| D-20 | Invoice types and Nepal tax | Platform subscription invoices (SaaS company → restaurant) are a different document from restaurant sales invoices (restaurant → its customer). Do not reuse one template/table/series for both. Platform invoice templates are configurable by issuer name/address, PAN, VAT-registration status, and invoice type. A Nepali tax professional must confirm the current requirements before the product claims legal/tax compliance. | PA-1.3 / launch gate |
| D-21 | Data retention | Category-specific, not a blanket “delete after 30 days”. See §2.5. Legal/accounting retention periods require Nepali professional confirmation before launch. | PA-1.4 / PA-2 |

### 2.2 Open questions

Only these remain genuinely undecided. Items marked **Open** block the stated phase; items marked **Deferred** do not block PA-0 but must be closed before the related action is offered as a policy.

| # | Question | Why it matters | Owner | Status / blocking phase |
|---|----------|----------------|-------|-------------------------|
| Q-1 | What is the actual `platform_domain`, and who controls the registrar, DNS provider, hosting account, and TLS issuance/renewal? | PA-ADR-011, PA-ADR-003 deployment, cookies, CORS, HSTS | Ops / company owner | **Open** — blocks PA-1.4 production verification |
| Q-2 | Which private object-storage bucket/path holds optional payment evidence, and what is its access/retention policy? | D-18 evidence handling | Security/ops + finance | **Open** — blocks PA-1.3 evidence upload |
| Q-3 | What financial risk policy determines when a refund needs a second approval, and at what amount? | D-3 refund workflow | Finance | **Deferred** — PA-1 records all participants and flags single approval |
| Q-4 | Who are the real primary Super Admin, secondary Super Admin, and emergency recovery owner, and where are recovery codes/break-glass credentials stored? | PA-ADR-001 launch gate | Company owner / ops | **Open** — blocks commercial launch |
| Q-5 | What Nepal invoice/PAN/VAT requirements apply to platform subscription invoices, and what wording/template is approved? | D-20 invoice compliance | Finance/legal + Nepali tax professional | **Open** — blocks claiming tax compliance and final invoice template |
| Q-6 | What category-specific retention periods apply to subscription invoices, VAT records, audit/security logs, payment evidence, restaurant operational data, exports, and backups? | D-21 retention lifecycle | Legal/accounting + ops | **Open** — blocks the retention policy and deletion workflow |
| Q-7 | Is SSO/OIDC worth adopting later for chains/enterprise, or is TOTP sufficient? | D-9 future capability | Tech lead / product | **Deferred** — not committed to PA-3 |

Questions marked **Open** must be answered before the related phase gate. “We will decide later” is acceptable only for the explicitly deferred items.

### 2.3 Decision tracker (owner-facing)

| Decision | Recommendation | Status |
|----------|----------------|--------|
| Platform domain / DNS / TLS owner | Choose the actual domain and a named owner; keep credentials in a company password manager | **Open** |
| Payment evidence storage | Private object storage; PostgreSQL stores only the object key; evidence optional in PA-1 | Proposed (design), store still open |
| Refund second-approval threshold | Defer until a financial risk policy exists; manual/external refunds in PA-1 | **Deferred** |
| Second Super Admin | Identify two real people plus an emergency recovery owner; no fictional seed | **Open** |
| Nepal tax compliance | Confirm with a Nepali tax professional before claiming compliance | **Open** |
| Data retention | Define category-specific periods and the cancellation → export → restrict → delete → audit lifecycle | **Open** |
| SSO | No commitment; keep as a future capability | **Deferred** |

### 2.4 Execution rule for open decisions

PA-0 may proceed without resolving the open items above. The constraint is sequencing, not paralysis:

| Open decision | Blocks | PA-0 handling |
|---------------|--------|---------------|
| Domain / DNS / TLS owner | PA-1.4 production verification | Config-driven origins only; placeholders such as `{platform_domain}`; never hard-code a real domain |
| Real primary/secondary admins + recovery owner | Commercial launch | Bootstrap one admin; build invites/MFA; no production second-admin seed |
| Private evidence bucket/path + access policy | Evidence **upload** in PA-1.3 | Build invoice/payment/reference/verification/audit first; gate evidence upload behind configuration and defer it if storage is not ready |
| Nepali tax-professional sign-off | Compliance claims and final invoice template | Build configurable issuer/PAN/VAT/invoice-type fields and numbering now; keep `tax_treatment=UNCONFIRMED`; do not ship a template presented as legally compliant |
| Category-specific retention periods | Retention/deletion implementation | Keep append-only financial/audit records; document proposed categories; do not implement a blanket deletion rule |
| Refund second-approval policy | Enabling dual-approval refunds | Record requester/approver/completer and external reference; flag `single_admin_approval`; no invented threshold |

When a dependency is unresolved:

1. Use configuration placeholders or a disabled feature flag, not an invented production value.
2. Defer the dependent capability, not the whole phase.
3. Record the decision in the risk register and keep it linked to its blocking milestone.
4. Do not claim legal, tax, or operational compliance that has not been signed off.

Two sequencing rules are binding:

- **Evidence storage is not a prerequisite for manual payment recording.** Invoice creation, transaction references, manual verification, payment status, and audit history ship first. Evidence upload is an optional capability added when private storage and access policy are configured.
- **Tax sign-off is not a prerequisite for invoice data modeling.** Configurable issuer/PAN/VAT fields, invoice type, and fiscal-year numbering can be built first. The production template and any compliance claim wait for professional review.

### 2.5 Retention policy (category-specific)

There is no blanket “delete all tenant data after 30 days”. Until a Nepali legal/accounting professional confirms the periods, the operating policy is:

| Data category | Proposed policy | Notes |
|---------------|-----------------|-------|
| Subscription invoices and payments | Retain per applicable tax/accounting requirements; never hard-delete in PA-1/PA-2 | Financial records |
| VAT-related records | Use the applicable statutory retention period once confirmed | Do not assume a universal period |
| Audit and security logs | Documented security/legal retention period; proposed 3 years | Append-only |
| Uploaded payment evidence | Retain per financial-record requirements; proposed 7 years | Private object store; signed-URL access |
| Restaurant operational data | Define export and post-cancellation deletion rules per category | No silent deletion |
| Backups | Define expiry and deletion propagation; test that deleted data does not resurrect | Restore drill must cover this |
| Data exports | Short-lived artefact (`export_retention_days`, default 30); audit record kept | Export is audited |

Lifecycle (binding until legal sign-off changes it):

1. Tenant requests cancellation or is cancelled by the platform.
2. Tenant receives a defined **export window**.
3. Tenant data becomes **read-only or access-restricted** according to the cancellation policy.
4. Data is deleted after the documented retention period, **except** records subject to legal retention or a legal hold.
5. Deletion is recorded in an audit log.

The plan must not claim a legally compliant retention period before Q-6 is answered.

---

## 3. Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Trigger / owner |
|----|------|:----------:|:------:|------------|-----------------|
| R-1 | Scope creep from the 32-section spec | High | High | Parking lot + phase freeze + ADR trade rule | Any “while we are here” request / product |
| R-2 | Realm confusion leaks platform access | Medium | Critical | Separate secret/realm, cross-realm tests, code review checklist | Any auth change / tech lead |
| R-3 | Cross-tenant data leak via platform routes | Medium | Critical | Explicit IDs, parent-chain checks, 404 on mismatch, two-tenant tests | Any tenant route / tech lead |
| R-4 | Billing double-charge or wrong period | Medium | High | Idempotency, row locks, single transaction, ledger tests | Billing PR / finance |
| R-5 | MFA lockout of the only superadmin | Medium | High | Two real superadmins, hashed recovery codes, break-glass runbook, tested recovery drill | Admin change / ops |
| R-6 | Migration on a live database | Low–medium | High | Additive-only revision, rollback test, backup before deploy | PA-1 release / ops |
| R-7 | No email means onboarding stalls | Medium | Medium | Copyable invite links, manual follow-up, PA-2 email | First external tenant / product |
| R-8 | No worker means renewals are manual | Medium | Medium | Manual dashboard list of due invoices; PA-2 worker | First renewal / ops |
| R-9 | Tenant-origin XSS reaches the admin session | Low | Critical | Separate admin origin (PA-ADR-003), HttpOnly cookies (PA-ADR-010), strict CSP, no third-party scripts, step-up | Security review / security |
| R-10 | Test DB wipe destroys demo data | Medium | Low | Separate dev DB for manual QA; fixtures create their own data | Test run / eng |
| R-11 | Dashboard queries slow at scale | Medium | Medium | Indexes, p95 target, rollup in PA-2 | 10k tenants / eng |
| R-12 | Payment confirmation fraud or typo | Medium | High | Unique reference, verifier record, optional private evidence, maker–checker, immutable events, no amount edits, reconciliation in PA-3 | Billing ops / finance |
| R-13 | Admin account sharing | Medium | High | Named invite-only accounts, MFA, audit, disable leavers, last-superadmin rule | Ops / security |
| R-14 | Structure test blocks a needed import | Medium | Low | One ADR-009 edge; otherwise service/SQL seam | Any new cross-module need / eng |
| R-15 | Plan price edits confuse existing tenants | Medium | Medium | Price snapshot + UI warning + audit | Plan edit / product |
| R-16 | Admin MFA recovery failure locks the platform | Medium | Critical | ≥2 real superadmins, 10 single-use recovery codes, documented emergency recovery, quarterly recovery drill, break-glass credentials sealed offline | Quarter drill / ops |
| R-17 | Payment confirmation fraud (collusion or fake reference) | Low–medium | Critical | Unique reference enforced by DB index, optional evidence, verifier ≠ invoice creator, reconciliation against bank/eSewa statements, separate SaaS/QR payment records | Monthly reconciliation / finance |
| R-18 | Tenant data export contains another tenant’s rows | Low | Critical | Export query always filtered by `restaurant_id` from the authenticated path, never from a request body; automated two-tenant isolation test; export manifest includes row counts + tenant id hash | PA-2 export PR / eng |
| R-19 | Background job processes the wrong tenant | Medium | High | No background workers in MVP; when added (PA-2) every job takes an explicit `tenant_id`, re-checks it against the job payload, and logs it; cross-tenant job test | First worker PR / eng |
| R-20 | Secrets leaked in logs or error responses | Medium | Critical | Structured logging with a redaction allowlist (`password`, `token`, `cookie`, `authorization`, `csrf`, `secret`), no request-body logging on auth routes, log access restricted and audited | Any auth PR / security |
| R-21 | Backup cannot be restored | Medium | Critical | Automated daily backup + monthly restore test into a scratch DB with row-count and checksum verification; restore runbook | Monthly restore / ops |
| R-22 | Refresh-token theft and replay | Low–medium | High | HttpOnly + Secure + SameSite=Strict, rotation on every use, reuse detection revokes the family, security audit event, “sign out everywhere” | Any auth change / security |
| R-23 | Platform admin account compromise | Medium | Critical | TOTP MFA, step-up for sensitive actions, short access lifetime, session revocation, anomaly alerts on failed logins and role changes, least-privilege roles | Security review / security |
| R-24 | Tenant deletion or archival causes irreversible data loss | Low–medium | Critical | Soft-delete first, retention window, export required before hard delete, explicit typed confirmation + step-up MFA, approval workflow, restore test, audit | Deletion request / ops |
| R-25 | Payment evidence leaks through a public URL, logs, or broad access | Medium | Critical | Private bucket, object key only in PostgreSQL, short-lived signed URLs, payment-scoped authorization, content-type/size validation, no public URLs, no body/URL logging | Any evidence upload/view PR / security |
| R-26 | SaaS subscription payments get mixed with restaurant QR payments | Medium | High | Separate tables, routes, permissions, and storage prefixes; no shared payment/evidence IDs; isolation tests; UI labels distinguish platform billing from restaurant sales | Any billing change / eng |
| R-27 | Domain/DNS account is lost, hijacked, or certificates expire | Low–medium | Critical | PA-ADR-011 names the owner, keeps credentials in a company password manager, enables registrar lock, monitors expiry, and documents renewal | Quarterly ops check / ops |
| R-28 | Platform invoices are treated as legally compliant when they are not | Medium | Critical | Distinguish platform vs restaurant invoices; configurable issuer/PAN/VAT/invoice type; Nepali tax-professional sign-off before any compliance claim; no hard-coded template presented as final | Invoice template release / finance |
| R-29 | Retention/deletion policy violates tax/legal requirements or destroys needed records | Medium | Critical | Category-specific policy, legal/accounting sign-off, legal-hold override, audit every deletion, restore test proves backups expire | Policy approval / legal + ops |
| R-30 | Refund is recorded but the external money movement never happens (or vice versa) | Medium | High | Record external refund reference and completer, reconcile refunds monthly, flag `processed_outside_platform`, no automated refund claims in PA-1 | Monthly reconciliation / finance |

---

## 4. Decision process

1. Any new decision is written here as `PA-ADR-0xx` with status `Proposed`.
2. It is discussed at the next phase boundary, not mid-task.
3. Accepted ADRs are immutable except by a superseding ADR.
4. A decision that changes MVP scope must also update `02-scope-and-priorities.md`, `07-implementation-roadmap.md`, and the estimate.
5. A decision that changes schema must update `04-data-model.md` and the migration plan.
6. A decision that changes an API contract must update `05-api-contracts.md` and the frontend plan.
