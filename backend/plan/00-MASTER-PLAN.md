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
| D13| Role granularity                                                         | One role per membership for the pilot; per-branch differing roles deliberately discouraged (09 §4) |
| D14| Module boundaries                                                        | Backend is structured by **bounded context, not layer** — `modules/<context>/` with table ownership, enforced structurally by import-linter + tests (02 §2), not prose. The restructure happens in **Phase 0**, before any M1/M2 work |
| D15| Internal events                                                          | Cross-module communication is via a typed, versioned internal event bus persisted through the outbox (02 §2.3, 13 §0). Lost events are impossible; handlers are idempotent and never roll back the emitter |
| D16| Background worker                                                         | Scheduler runs in-process (asyncio) during the pilot — orchestrator over module interfaces, not a data-owning module (02 §2.5); no Celery until load demands |

## 3. Phase roadmap (summary — full detail in `22-phase-roadmap.md`)

| Phase | Deliverable | Migrations | Eng. wk |
|-------|-------------|------------|---------|
| 0     | Repo audit, **bounded-context restructure**, Postgres-first env, ADRs, event skeleton, isolation skeleton | — | 2   |
| 1     | Tenancy scaffolding (tenants/branches/memberships/plans tables), TenantContext | M1, M2 | 2.5 |
| 2     | Multi-tenant auth: memberships, JWT with tenant claims, switch-tenant, bus live | — | 3   |
| 3     | Branch model: dual-write M3, read-switch M4, branch CRUD, menu overrides | M3, M4 | 4   |
| 4     | RLS + isolation hardening (1 wk work + 2 wk CI wait, parallelized) | M5 | 1 + 2 wait |
| 5     | Thin super admin app (create/suspend/force-logout tenants) | — | 1.5 |
| 5b    | Onboarding wizard + trial state + demo tenant | — | 2   |
| 6 (optional) | Stripe subscriptions, dunning, invoices | — | 3.5 |
| 7     | Customer subdomain routing + per-tenant branding | — | 1.5 |
| 8     | Waiter request feature | — | 1   |
| 9     | Drop `restaurant_id` (M6) after green period | M6 | 1.5 |
| 10    | Launch hardening: pen-test, load test, restore drill, runbooks | — | 2.5 |

Phases 1–5 (excluding 6) are the minimum viable platform. **Estimate ~16 engineering weeks ⇒ ~19–21 calendar weeks to "first external tenant can onboard"** (a second engineer pulls that toward ~17–19). Full build 0–10 ≈ 26 eng-weeks. See the engineering-vs-calendar assumption note below and `22-phase-roadmap.md Totals`; do not plan stakeholders around 7–10.

**Estimate assumptions (applies to the plan-22 detail too):**
- Unit = engineering weeks for **one senior engineer holding full context**, working on this project primarily.
- Add ~30–40% wall-clock for: context hand-offs, M3-dual-write and RLS debugging (the two historically underestimated items), isolation-suite findings that each cost days to fix, and DNS/cert multi-day lag (D5). The isolation suite *finding twice as many bugs as expected in M3 is the expected case*, not a failure case.
- Phase 4 includes ~2 weeks of *wall-clock waiting* (isolation suite green ×2 consecutive weeks) but is ~1 week of engineering work — work items can advance in parallel.
- **Critical path:** 0 → 1 → 2 → 3 → 5 → 7. Phase 4 (RLS) can start as soon as Phase 3 dual-write stabilizes; 5/5b/7/8 parallelize off the critical path given a second engineer.

**Sequencing rule (highest-leverage change):** the `modules/<bounded_context>/` restructure (D14) happens in **Phase 0**, *before* M1/M2. Building Phase 1 on the flat `services/ repositories/` layout and re-mapping in Phase 3 means doing M1/M2 code twice.

## 4. Document index

| File | Topic |
|------|-------|
| `01-current-state-audit.md` | What the repo actually has; assumption validation; prerequisite findings |
| `02-architecture-overview.md` | Bounded-context module map (D14), module contract, event bus, request lifecycle, tech stack |
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
| `21-coding-standards.md` | Senior-level code conventions: repos, services, errors, typing — plus module-boundary norms (§11) |
| `22-phase-roadmap.md` | Phase-by-phase tasks, estimates, exit criteria |
| `23-decision-register.md` | ADR format, locked decisions, open decisions with owners |
| `24-onboarding-trials.md` | Setup wizard tiers, abandonment, demo tenant, trial conversion |
| `25-reports-analytics.md` | Report inventory, end-of-day, platform metrics |
| `super_admin/00-README.md` | Execution plan for the expanded Super Admin spec (`super_admin_plan.md`): separate admin origin, cookie/CSRF auth, scope, data, API, frontend, roadmap, tests, parking lot |

## 5. How to use these plans

1. Read `00 → 01 → 02 → 03` first; those four define the shape of everything.
2. Before coding any subsystem, read its dedicated file + `03` + `04` + `21`.
3. Every code PR must reference a file number and a task id from `22-phase-roadmap.md`.
4. Discrepancies between `baseplan.md` and these files: these files win.
5. Open questions in `23-decision-register.md` marked **BLOCKING** must be answered before the phase that depends on them.
