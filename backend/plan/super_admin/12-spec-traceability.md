# 12 — Spec Traceability and Scope Guard

**Purpose:** answer “where is section N?” without reopening scope.

Each section of `super_admin_plan.md` gets a disposition:
- **P1** — in the commercial MVP (PA-1)
- **P2** — operational maturity (PA-2)
- **P3** — advanced platform (PA-3)
- **NO** — not planned; requires a new ADR
- **SPLIT** — part is P1, the rest is later

---

## 1. Section map

| Spec § | Topic | Disposition | Phase / plan file | Notes |
|:------:|-------|-------------|-------------------|-------|
| 1 | Super Admin dashboard | SPLIT | PA-1.1 + PA-2 | Launch KPI set only; cohorts/advanced charts in PA-2 |
| 2 | Restaurant / tenant management | P1 | PA-1.1/1.2 | List/search/detail/create/suspend/reactivate/force-logout |
| 3 | Subscription and plan management | SPLIT | PA-1.1/1.2 + PA-2 | Plans CRUD in PA-1; centralized entitlement enforcement in PA-2 |
| 4 | Subscription lifecycle | P1 (manual) | PA-1.2 | Automatic dunning/expiry in PA-2, `PL-002` |
| 5 | Payment and transaction management | SPLIT | PA-1.3 + PA-3 | Manual payments with unique transaction reference, optional private evidence, verifier, immutable events in PA-1; gateway/webhooks in PA-3, `PL-001`. SaaS payments separate from restaurant QR payments. |
| 6 | Invoice and financial management | P1 | PA-1.3 | Manual platform invoices, fiscal-year numbering, void, manual refund recording with external reference; Nepal PAN/VAT template pending professional sign-off |
| 7 | Branch management | P2 | `PL-012` | PA-1 shows counts only; no branch editing from platform |
| 8 | User and staff management | SPLIT | PA-1.4 + PA-2 | Platform users/roles in PA-1; tenant staff read-only in PA-2 |
| 9 | Support and complaint management | P2 | `PL-004` | Audit + diagnostics cover early support |
| 10 | Notifications and announcements | P2 | `PL-003`, `PL-005` | No email/delivery infra in MVP |
| 11 | Platform configuration and settings | P1 (allowlist) | PA-1.4 | Small allowlisted key/value set |
| 12 | Platform analytics and reports | SPLIT | PA-1.1 + PA-2 | Metric dictionary in PA-1; advanced reports/exports in PA-2 |
| 13 | Platform audit logs | P1 | PA-0/PA-1.2 | Append-only, reason, before/after |
| 14 | Security and access management | P1 | PA-0 | Separate realm + origin, MFA, HttpOnly cookies, CSRF, roles, step-up, revocation |
| 15 | Tenant diagnostics and support access | SPLIT | PA-1.1 + PA-3 | Read-only diagnostics in PA-1; impersonation is NO/`PL-013` |
| 16 | System health and monitoring | SPLIT | PA-1.1 + PA-2 | API/DB/migration health in PA-1; infra dashboards in PA-2 |
| 17 | Integration management | P2 | `PL-008` | No integrations yet |
| 18 | Feature flags and product rollout | P2 | `PL-007` | Entitlements JSON covers plan-level features in MVP |
| 19 | Restaurant onboarding management | P2 | `PL-006` | MVP creates the tenant + owner invite manually |
| 20 | Promotions, discounts, coupons | P3 | `PL-014` | Manual invoice discounts cover early deals |
| 21 | Platform content and CMS | P3 | `PL-015` | Separate product |
| 22 | API and developer management | P3 | `PL-016` | No external demand yet |
| 23 | Data management, backups, retention | SPLIT | PA-1 docs + PA-2 + PA-3 | Category-specific retention policy in PA-1; export/retention workflow + backup restore in PA-2; hard-deletion console in PA-3. Periods require Nepali legal/accounting sign-off. |
| 24 | Incident and maintenance management | P2 | `PL-009`, `PL-026` | Process before tool |
| 25 | Legal, compliance, privacy | P3 | `PL-017` | MVP records retention and audit only; no compliance claim before professional sign-off |
| 26 | Super Admin profile and personal settings | P1 | PA-1.4 | Name, password, MFA, own sessions |
| 27 | Super Admin navigation structure | P1 | `06-frontend-plan.md` | Permission-gated admin-origin nav |
| 28 | Important Super Admin workflows | SPLIT | PA-1/PA-2/PA-3 | Each workflow follows its feature disposition |
| 29 | Recommended database modules | P1 (subset) | `04-data-model.md` | Only the modules required by P1; no speculative tables |
| 30 | Critical security rules | P1 | `03-architecture-and-security.md` | Realm/origin isolation, cookies, CSRF, MFA, tenant isolation, audit, payments are gates |
| 31 | What should you build first? | P1/P2/P3 | `07-implementation-roadmap.md` | The spec’s own priority tiers are honored |
| 32 | Final recommendation | P1 | `00-README.md` | Three levels of responsibility, owner operates the restaurant |

## 2. Workflow disposition (§28)

| Workflow | Disposition | Where |
|----------|-------------|-------|
| Super Admin logs in | P1 | PA-0 |
| Tenant registration/verification | SPLIT | PA-1.2 create shell + invite; PA-2 self-serve onboarding |
| Create plan → tenant subscribes → entitlement granted | SPLIT | PA-1 plan + subscription; entitlement enforcement PA-2 |
| Renewal reminder → payment → verify → extend → invoice | SPLIT | PA-1 manual invoice/payment/extension with transaction reference + optional evidence + verifier; reminders PA-2; gateway PA-3. Invoice becomes PAID only after verification, never from an upload. |
| Suspend/reactivate/force logout | P1 | PA-1.2 |
| Support ticket investigation | P2 | PA-2 (`PL-004`) |
| Incident detection/recovery | P2 | PA-2 (`PL-009`) |
| Feature rollout by tenant | P2 | PA-2 (`PL-007`) |
| Backup/restore | P2 | PA-2 (`PL-010`) + runbook |
| Impersonation/support access | NO | `PL-013`; diagnostics only in P1 |

## 3. Scope guard: answers to common requests

Use these answers verbatim when a request tries to pull a parked item into the active phase.

| Request | Answer |
|---------|--------|
| “Add Stripe while we are in billing.” | Out of scope. Gateway is `PL-001`/PA-3. PA-1 is manual billing by design (D6, PA-ADR-005). |
| “Send an email when a tenant is suspended.” | Out of scope. Email is `PL-003`/PA-2. PA-1 writes the audit row and the operator notifies manually (PA-ADR-004). |
| “Let support log in as the tenant.” | Not approved. Impersonation is `PL-013`/PA-3 and needs a dedicated security review (PA-ADR-007). |
| “Add support tickets.” | Out of scope. `PL-004`/PA-2; PA-1 diagnostics + audit answer the first cases. |
| “Show branch details across all tenants.” | Out of scope. `PL-012`/PA-2; tenant detail shows counts only. |
| “Add feature flags for the new menu.” | Out of scope. `PL-007`/PA-2; use plan entitlements only when enforcement lands. |
| “Let the platform edit tenant staff.” | Not planned. `PL-020`; owners operate their restaurants (spec §32). |
| “Add coupons/discount codes.” | Out of scope. `PL-014`/PA-3; use an invoice discount line for a one-off deal. |
| “Build a developer API.” | Out of scope. `PL-016`/PA-3. |
| “Delete a tenant completely.” | Not in MVP. Archive only; deletion workflow is `PL-017`/PA-3. |
| “Add a second dashboard chart.” | Only if it is in the PA-1.1 metric dictionary; otherwise `PL-011`/PA-2. |
| “Add a mobile admin app.” | Not planned. `PL-025`; responsive web covers emergencies. |
| “Use the existing subscription tables.” | Rejected. See PA-ADR-002; new `platform_*` tables. |
| “Skip MFA for local testing.” | Allowed only when `APP_ENV != production` **and** `PLATFORM_REQUIRE_MFA=false`; never in production. Tests must still cover the MFA-on path. |
| “Serve `/admin` from the tenant origin for launch.” | Rejected. Production needs `admin.{platform_domain}`. A same-origin launch needs written security acceptance and a risk-register entry (PA-ADR-003). |
| “Store the access token in `sessionStorage` so reloads work.” | Rejected. The admin session is HttpOnly cookies + CSRF. No JS-readable credentials (PA-ADR-010). |
| “Let me edit the payment amount; it was a typo.” | Rejected. Void the payment with a reason and record a new one; confirmed amounts are immutable (PA-ADR-005). |
| “Approve my own refund; I’m the only admin online.” | Allowed while the second-approval policy is deferred, but flagged `single_admin_approval` and fully audited. A future financial risk policy may require a different approver. |
| “Merge this one small endpoint.” | It needs a `PL-xxx`, an ADR, and a scope trade. If nothing leaves the phase, it waits. |

## 4. Coverage check

| Priority | Spec sections | Status |
|----------|---------------|--------|
| P1 | 1 (subset), 2, 3 (subset), 4 (manual), 5 (manual), 6, 8 (platform users), 11, 12 (subset), 13, 14, 15 (read-only), 16 (subset), 26, 27, 29 (subset), 30, 31, 32 | Covered by PA-0/PA-1 |
| P2 | 1 (advanced), 7, 8 (tenant staff read-only), 9, 10, 12 (advanced), 16 (infra), 17, 18, 19, 23 (export/retention/backup), 24 | Covered by PA-2 |
| P3 | 5 (gateway), 15 (impersonation), 20, 21, 22, 23 (governance), 25, 28 (advanced) | Covered by PA-3 |
| NO | Platform editing tenant staff/branches, mobile admin app, AI assistant | Rejected for now; may be revisited with a new ADR |

**No spec section is silently dropped.** Every section has a disposition, a phase, or a parking-lot ID.

## 5. Traceability maintenance

When an item is promoted from the parking lot:

1. Change its disposition in this file.
2. Add the task ID in `07-implementation-roadmap.md`.
3. Add the endpoint/table in `04`/`05`.
4. Add the acceptance case in `08`.
5. Record the ADR in `09`.
6. Note the scope trade in `02`.

If those six do not move together, the plan has drifted.
