# Current State Audit — what the repo actually has

**Status:** Verified by direct inspection on 2026-11-02. This file replaces every `ASSUMPTION:` in `baseplan.md` with a checked fact.

## 1. Verified stack

| Component | Reality | Plan implication |
|-----------|---------|------------------|
| Backend | FastAPI + SQLAlchemy 2 and postgres + Alembic (`backend/app`, migrations in `backend/alembic/versions/`) | Migration plan M1–M6 is executable with existing Alembic tooling |
| Database | **Default dev DB is SQLite**: `database_url:` sqlite=`sqlite:///./data/restaurant.db` and postgres=`postgresql://user:tara@localhost/restaurant` (`backend/app/core/config.py`). Docker-compose provides Postgres 16 (`docker-compose.yml`) but nothing forces it | **BLOCKING prerequisite:** switch dev to Postgres-first (D12). SQLite cannot run RLS policies, `SET LOCAL`, `CONCURRENTLY` indexes |
| Web app | React + Vite at `apps/web` (customer + staff surfaces in one SPA) | Tenant context and cache-reset rules planned in `15-frontend-web.md` |
| Mobile | Expo ~58 at `apps/mobile` (`expo-router`), exists and builds | Staff-app changes planned in `16-mobile.md` |
| Redis / Celery | **Absent.** Zero usage found | D7 locked: Postgres-based counters; no new queue infra for the pilot |
| Outbox | `outbox_events` table exists in baseline schema | Worker completeness is a Phase 2 exit criterion (`13-notifications-outbox.md`) |
| Tests | `backend/tests/` — pytest with domain/api/serving/tables suites | Extend, don't replace; isolation suite is new (`18-testing-strategy.md`) |

## 2. Verified schema facts (from `backend/alembic/versions/ed02e9ab12e0_baseline_schema.py` and `docs/schema.md`)

| Fact | Consequence for the plan |
|------|--------------------------|
| `restaurants` table exists with settings row (`restaurant_settings`, `restaurant_id` PK/FK) | Split into `tenants` + `branches` per M1; `restaurant_settings` content distributes to tenant/branch configs |
| `restaurant_id` is NOT NULL FK on every tenant-owned table (audit_events, menu_*, orders, order_items, kitchen_*, bills, payments, tables, dining_sessions, service_calls, restaurant_memberships, payment_methods, outbox_events) | M2 column-addition list is exactly these tables. Files `03-data-model.md §4` enumerates them |
| `restaurant_memberships` exists: `(restaurant_id, user_id, role_id, status, invited_by_membership_id, ...)` with unique `(restaurant_id, user_id)` | **Better than baseplan assumed** — the membership model partially exists. M1 renames/upgrades it rather than inventing it |
| `roles` / `role_permissions` are restaurant-scoped with seeded system templates (owner, manager, waiter, kitchen, cashier) | Five-role permission model survives unchanged; plan adds branch scoping in `05-authentication-authorization.md` |
| JWT already binds the tenant: `create_access_token(user_id, membership_id, restaurant_id)` sets claim `"rid"` (`backend/app/core/security.py`) | Phase 2 extends the token (add `tenant_id`, `membership_id`, `branch_ids`, `perms`, `pv`, `jti`) rather than redesigning |
| `table_qr_codes` with `token_hash`, revocation, rotation fields | Customer QR resolution work in Phase 7 is a lookup change only |
| `dining_sessions`, `service_calls` (GUEST/KITCHEN with acknowledge fields) | Operational workflows in `11-operational-workflows.md` build directly on these |
| `outbox_events` keyed by `restaurant_id` | Gains `tenant_id`/`branch_id` in M2/M3 like every other operational table |

## 3. Gaps the plan fills (ranked)

1. **Postgres-first dev environment** (Phase 0 prerequisite; see `20-devops-infrastructure.md §2`).
2. Multi-tenant scoping columns + dual-write/read-switch (M2–M4).
3. Tenant switch in tokens + membership validation per request.
4. Branch layer (schema + operational scoping).
5. Platform-admin realm + thin super admin.
6. Isolation test suite (new `backend/tests/isolation/`).
7. Outbox worker running reliably (deliver WS events, notifications).
8. Entitlements + usage counters (Postgres-based, D7).
9. Onboarding wizard + lifecycle states.
10. Subdomain routing + wildcard TLS (start DNS/TLS work early; irreversible decision D5).

## 4. Corrections issued to `baseplan.md`

| baseplan claim | Correction |
|----------------|-------------|
| "Membership model does not exist" | Partially exists (`restaurant_memberships`). Phase 2 upgrades and renames; re-use exists singularity |
| "Redis counters + Celery persistence" | Removed for pilot (D7). Postgres counters |
| Migration timing "trivial for one restaurant" | Still true, but per-table verification queries in `17-migration-runbook.md` are mandatory regardless |
| One active subscription UNIQUE(tenant_id) | Amended: partial unique index `WHERE status IN ('trialing','active','past_due','paused')` to allow history from day one (`03-data-model.md §5`) |
| Menu draft/publish not in schema | Added to schema in `10-menu-draft-publish.md` — publish signals land in M3, so the draft workflow doesn't retrofit later |

## 5. Phase 0 checklist (verbatim tasks)

- [ ] Perform the `modules/<bounded_context>/` restructure (00 §3 sequencing rule, 02 §2, 21 §10) — **before any M1/M2 code is written**, so migrations aren't built twice.
- [ ] Stand up Postgres 16 in dev: set `DATABASE_URL` to Postgres, run `alembic upgrade head` against it, verify the full test suite passes (`pytest backend/tests`).
- [ ] Delete ad-hoc SQLite artifacts from dev workflow (`backend/data/`, `data/*.db` become dev-throwaway; keep a snapshot only for migration backfill rehearsal).
- [ ] Run the full suite green on Postgres; record any dialect-dependent failures and fix.
- [ ] Produce written sign-off on `02`, `03`, `04`, `05` (the four shape-defining documents).
- [ ] Stand up the isolation test skeleton: `backend/tests/isolation/` with two-tenant fixtures (no assertions yet — prove the harness runs).
- [ ] Start DNS/apex task for wildcard `*.platform.com` (can be internal; D5 cannot change after launch).
- [ ] Answer BLOCKING decisions in `23-decision-register.md` (pilot single/multi-branch; URL suffix; suspension grace details).
