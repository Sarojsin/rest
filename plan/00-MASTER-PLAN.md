# Master Plan — Multi-Tenant Restaurant SaaS

**Status:** Approved direction. Plans 01–26 are the implementation contract. No code changes until Phase 0 sign-off.
**Supersedes:** `plan/baseplan.md` (kept as source document; discrepancies resolved in favor of files 01–26).
**Source of truth for the current repo:** `docs/schema.md`, `backend/alembic/versions/*.py`, `plan/01-current-state-audit.md`.

---

## 1. What we are building

Evolve the existing single-tenant restaurant system (FastAPI + SQLAlchemy + React web + Expo mobile) into a multi-tenant SaaS:

```
Tenant (restaurant business — billing, plans, users)
  └── Branch (physical location — tables, kitchen, branch menu overrides)
        └── Dining session (a table visit)
              └── Orders / Bills / Payments
```

Key principle: **widen, don't rewrite.** Every operational table keeps its current shape and gains scoping columns; nothing is replaced wholesale.

## 2. Canonical decisions (locked — see 23 for ADR register)

| #  | Decision                                                                 | Locked value |
|----|--------------------------------------------------------------------------|--------------|
| D1 | Tenancy model                                                            | Shared DB, shared schema, `tenant_id` + `branch_id` discriminator columns, RLS as defense-in-depth enabled at M5 |
| D2 | Tenant resolution                                                        | Verified token / QR token / DB record only. Never from URL, body, or query on tenant-scoped routes |
| D3 | Auth realms                                                              | Three separate realms: staff, customer (QR), platform admin. Tokens are not usable across realms |
| D4 | Identity model                                                           | One global identity per person; memberships per tenant; role per membership |
| D5 | Customer URL                                                             | Subdomain per tenant `{tenant-slug}.platform.com` + wildcard TLS. The decision is irreversible once launched; DNS/TLS work starts in Phase 0 |
| D6 | Platform billing gateway                                                 | **Deferred.** Manual/invoiced billing for the first tenants; Stripe is optional Phase 6, schema reserves columns |
| D7 | Usage enforcement infrastructure                                         | Postgres-based counters + in-process caching for the pilot. No Redis, no Celery until load demands it |
| D8 | RLS timing                                                               | Enable at M5, only after the cross-tenant isolation suite is green for 2 weeks |
| D9 | Order quota behavior                                                     | Soft (overage + notify) mid-service; hard limits on branch/staff creation only |
| D10| Suspension behavior                                                      | Graceful: in-flight sessions finish, new sessions blocked, exports always allowed |
| D11| Pilot migration path                                                     | Migrate the existing pilot restaurant through the same migration + registration door as everyone else (Path 1) |
| D12| Dev database                                                             | Postgres-first from Phase 0. SQLite support is dropped from the migration path |

## 3. Phase roadmap (summary — full detail in `22-phase-roadmap.md`)

| Phase | Deliverable | Migrations | Est.   |
|-------|-------------|------------|--------|
| 0     | Repo audit, Postgres-first env, ADRs, isolation test skeleton | — | 1 wk   |
| 1     | Tenancy scaffolding (tenants/branches/memberships/plans tables), TenantContext | M1, M2 | 2 wk   |
| 2     | Multi-tenant auth: memberships, JWT with tenant claims, switch-tenant | — | 2 wk   |
| 3     | Branch model: dual-write M3, read-switch M4, branch CRUD, menu overrides | M3, M4 | 3 wk   |
| 4     | RLS + isolation hardening (isolation suite green ×2 weeks) | M5 | 2 wk   |
| 5     | Thin super admin app (create/suspend/force-logout tenants) | — | 1 wk   |
| 5b    | Onboarding wizard + trial state + demo tenant | — | 1.5 wk |
| 6 (optional) | Stripe subscriptions, dunning, invoices | — | 3 wk   |
| 7     | Customer subdomain routing + per-tenant branding | — | 1 wk   |
| 8     | Waiter request feature | — | 0.5 wk |
| 9     | Drop `restaurant_id` (M6) after green period | M6 | 1 wk   |
| 10    | Launch hardening: pen-test, load test, restore drill, runbooks | — | 2 wk   |

Phases 1–5 (excluding 6) are the minimum viable platform. **7–10 weeks of focused work to "first external tenant can onboard."**

## 4. Document index

| File | Topic |
|------|-------|
| `01-current-state-audit.md` | What the repo actually has; assumption validation; prerequisite findings |
| `02-architecture-overview.md` | System architecture, module map, request lifecycle, tech stack |
| `03-data-model.md` | Full target schema: new tables + column deltas + conventions |
| `04-tenant-isolation.md` | Six defense layers, RLS design, composite FKs, global-table allowlist |
| `05-authentication-authorization.md` | Three realms, JWT design, permission versioning, tenant switching |
| `06-billing-subscriptions.md` | Subscription lifecycle, manual-billing MVP, Stripe phase spec, dunning |
| `07-entitlements-enforcement.md` | Entitlement service design, enforcement points, counters |
| `08-super-admin.md` | Platform admin realm, thin app scope, audit |
| `09-branch-model.md` | Branch scoping, staff membership across branches, archival |
| `10-menu-draft-publish.md` | Menu inheritance model, overrides, availability, publish workflow |
| `11-operational-workflows.md` | Serving state machine, bills, service calls, amendments — in multi-tenant |
| `12-customer-qr-flow.md` | QR entry, sessions, order flow, payment flow |
| `13-notifications-outbox.md` | Outbox worker, event catalog, WS/SSE topics, escalation timers |
| `14-api-contracts.md` | Full endpoint map, error-code catalog, versioning, deprecation policy |
| `15-frontend-web.md` | Dashboard, TenantContext, cache discipline, super admin app |
| `16-mobile.md` | Expo staff app changes, secure storage, tenant switcher |
| `17-migration-runbook.md` | M1–M6 SQL, verification, feature flags, rollback procedures |
| `18-testing-strategy.md` | Isolation suite, CI gates, fixtures, RLS double-run |
| `19-security-threat-model.md` | Threat actors, T1–T25 mitigations, secure defaults |
| `20-devops-infrastructure.md` | Environments, config, CI/CD, observability, backups, DNS/TLS |
| `21-coding-standards.md` | Senior-level code conventions: repos, services, errors, typing |
| `22-phase-roadmap.md` | Phase-by-phase tasks, estimates, exit criteria |
| `23-decision-register.md` | ADR format, locked decisions, open decisions with owners |
| `24-onboarding-trials.md` | Setup wizard tiers, abandonment, demo tenant, trial conversion |
| `25-reports-analytics.md` | Report inventory, end-of-day, platform metrics |

## 5. How to use these plans

1. Read `00 → 01 → 02 → 03` first; those four define the shape of everything.
2. Before coding any subsystem, read its dedicated file + `03` + `04` + `21`.
3. Every code PR must reference a file number and a task id from `22-phase-roadmap.md`.
4. Discrepancies between `baseplan.md` and these files: these files win.
5. Open questions in `23-decision-register.md` marked **BLOCKING** must be answered before the phase that depends on them.
