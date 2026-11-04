# Super Admin Workstream — Execution Plan

**Status:** PLANNING ONLY. No implementation has started.
**Planning date:** 2026-11-04
**Revision:** 2026-11-04b — separate admin origin, HttpOnly cookie auth, optional private payment evidence, manual external refunds with no fixed threshold, real two-superadmin gate, open domain decision, Nepal tax and category-specific retention launch gates, no SSO commitment.
**Product source:** `backend/plan/super_admin_plan.md` (32-section wishlist)
**Execution contract:** this folder + `backend/plan/00-MASTER-PLAN.md` + `backend/plan/08-super-admin.md`

---

## 1. Why this folder exists

`super_admin_plan.md` is a strong **product backlog**: it describes 32 modules and three priority tiers. It is not an implementation plan. It mixes MVP, next-release, and multi-quarter ideas in one document, and it assumes infrastructure the repo does not have yet (email delivery, background workers, a payment gateway, monitoring).

This folder turns that document into a sequence that can be executed without letting later ideas pull the current phase apart.

It is deliberately **subordinate** to the existing plan set. Where the two disagree, the hierarchy below wins.

## 2. Source-of-truth hierarchy

| Rank | Document | Role |
|------|----------|------|
| 1 | `backend/plan/super_admin/02-scope-and-priorities.md` | What is in the current phase and what is explicitly out |
| 2 | `backend/plan/super_admin/07-implementation-roadmap.md` | Task order, exit criteria, estimates |
| 3 | `backend/plan/super_admin/04-data-model.md` + `05-api-contracts.md` | Shape of the implementation |
| 4 | `backend/plan/08-super-admin.md` | Security philosophy, realm rules, break-glass |
| 5 | `backend/plan/00-MASTER-PLAN.md` + `05`/`06`/`07`/`14`/`18`/`19`/`22` | Locked platform decisions and conventions |
| 6 | `backend/plan/super_admin_plan.md` | Product wishlist; never an implementation contract |

If a request conflicts with ranks 1–5, it goes to `10-parking-lot.md`, not into the active phase.

## 3. Document map

| File | Contents |
|------|----------|
| `00-README.md` | This file: rules, map, phase summary |
| `01-assessment.md` | Verdict on the spec, current-repo baseline, gap analysis, effort |
| `02-scope-and-priorities.md` | MVP / P2 / P3, non-goals, product acceptance |
| `03-architecture-and-security.md` | Realm split, auth/MFA, permissions, audit, tenant isolation |
| `04-data-model.md` | New platform tables, existing-table changes, migrations, seed data |
| `05-api-contracts.md` | Endpoint catalog, permission matrix, errors, payload shapes |
| `06-frontend-plan.md` | Separate admin app, route tree, pages, components, no-JS-token auth |
| `07-implementation-roadmap.md` | PA-0 → PA-3 phases, tasks, estimates, exit criteria, DoD |
| `08-testing-and-acceptance.md` | Test matrix, security tests, acceptance checklist, CI gates |
| `09-risks-and-decisions.md` | ADRs, resolved decisions, remaining questions, risk register |
| `10-parking-lot.md` | Intake rules and all deferred ideas |
| `11-operations-runbook.md` | Bootstrap, two-admin recovery, break-glass, payments, backups, cookies |
| `12-spec-traceability.md` | All 32 spec sections mapped to disposition + phase |

## 4. Phase summary

| Phase | Deliverable | Estimate | Gate to start |
|-------|-------------|----------|---------------|
| **PA-0** | Architecture and security foundation: separate admin origin/build, HttpOnly cookies + CSRF, MFA, permissions, audit, bootstrap | 3–3.5 eng weeks | ADRs approved (PA-ADR-011 may remain open until PA-1.4); current suites green |
| **PA-1** | Commercial MVP: dashboard, tenants, plans, subscriptions, manual invoices/payments with anti-fraud controls, platform users, audit viewer, settings, diagnostics, launch gates | 9–10 eng weeks | PA-0 exit criteria met |
| **PA-2** | Operational maturity: email, reminders/worker, export/retention, support, analytics, monitoring/backups, admin-origin completion if excepted, integrations | 8–10 eng weeks | ≥10 paying tenants or documented support load |
| **PA-3** | Advanced platform: gateways/reconciliation, promotions, CMS, developer API, role editor, controlled impersonation. SSO is **not** promised; it is a future capability only if a separate business case exists | 8–12 eng weeks | PA-2 stable for one quarter; separate business case |

**MVP total:** ~12–13.5 engineering weeks for one senior engineer with full context. Calendar ≈ 16–19 weeks after the 30–40% overhead from the master plan. A second engineer working in parallel on frontend during PA-1 can pull the calendar toward ~12–14 weeks. These are planning estimates, not commitments.

## 5. Non-negotiable rules for this workstream

1. **One active phase.** PA-0, PA-1, PA-2, PA-3 are sequential. No PA-2 work starts while PA-1 is open.
2. **No code without a task ID.** Every PR references `PA-x.y` from `07-implementation-roadmap.md` and the plan file it implements.
3. **New idea ⇒ parking lot.** A new feature request gets a `PL-xxx` entry in `10-parking-lot.md`. It cannot enter the active phase without an ADR in `09-risks-and-decisions.md` and an explicit trade: something of equal size leaves the phase.
4. **The spec is not the contract.** `super_admin_plan.md` sections marked P2/P3 in `12-spec-traceability.md` are not “missing MVP work”.
5. **Realm and origin isolation are not optional.** A restaurant owner session must never authorize a `/api/platform` route, and the admin app is served from `admin.{platform_domain}`, not the tenant origin. Tested on every phase gate.
6. **No credential is readable by JavaScript.** Admin auth uses HttpOnly access + refresh cookies, CSRF protection, and no `localStorage`/`sessionStorage` tokens.
7. **Every mutation is audited.** No state change without an actor, target, reason, timestamp, and before/after snapshot. Audit rows are written in the same transaction as the change.
8. **No silent impersonation.** Not built in the pilot. Support access is read-only diagnostics in PA-1; time-limited impersonation is `PL-013` and needs its own ADR.
9. **Money is backend-verified and fraud-resistant.** No endpoint activates or renews a subscription based on client input. Manual payments need a unique transaction reference, a verifier, idempotency, and an append-only event ledger. Evidence is optional and, when present, private with signed-URL access. Confirmed amounts are immutable; refunds are manual, record requester/approver/completer and the external reference, and have no fixed dual-approval threshold until a financial risk policy exists.
10. **No destructive action without step-up.** Delete/demote/suspend/refund require the right role, a reason, typed confirmation, and fresh MFA.
11. **At least two real superadmins before commercial launch.** Named primary, secondary, and emergency recovery owner; MFA, recovery codes, session revocation, lockout protection, and a tested break-glass procedure are launch gates. No fictional second admin.
12. **Migrations are the source of schema truth in production.** Dev may keep `create_all`; production uses Alembic. Every new table ships with a revision.
13. **No cross-module imports without an ADR.** The structure test in `tests/structure/test_boundaries.py` is a gate; if a new edge is unavoidable, add it to `couplings_baseline.txt` only with an ADR.
14. **No invented operational or legal facts.** The domain/DNS owner (PA-ADR-011), Nepal invoice requirements, and retention periods are open decisions requiring the owner and a qualified professional. The code may support configurable templates; it must not claim compliance.
15. **Every phase ends with docs, tests, and a demo.** A phase that “works locally” but has no test, no audit trail, and no runbook note is not done.

## 6. Current decision

**PA-0 is approved to proceed** under the execution rule in `09-risks-and-decisions.md` §2.4. The open items do **not** block PA-0; they block only their dependent milestones.

1. Implement PA-0 with configuration placeholders and no invented production values.
2. Do not implement evidence upload until the private store/access policy is configured.
3. Do not finalize the production invoice template or claim tax compliance until Nepali professional sign-off.
4. Resolve each open decision before its blocking milestone (PA-1.4 launch verification for the domain; commercial launch for the real admin roster; PA-1.3.4b for evidence storage).
5. Keep the existing staff application frozen except for bug fixes.

PA-0 scope remains the architecture/security foundation only; no tenant, invoice, or payment UI is part of PA-0.
