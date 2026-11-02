# Architecture Overview — Multi-Tenant SaaS

**Decision:** modular monolith (unchanged from `docs/architecture.md`); no microservices until real fault-isolation evidence exists.

## 1. System topology

```text
Customer phone browser                     Staff devices
  {tenant-slug}.platform.com                 apps/mobile (Expo)
        │                                       │
        └──────────── apps/web (React SPA) ─────┘
                        │  app.platform.com (staff+owner, tenant switcher)
        admin.platform.com (platform team, separate Vite app)
                        │
              FastAPI monolith  /api/v1/*   /api/platform/*   /api/admin
                        │
        ┌───────────────┼────────────────────────┐
   PostgreSQL 16   Object storage             Outbox worker (in-process, cron-style)
   (authoritative) (menu images / receipts)   + SSE/WS fan-out
```

- One API service, one Postgres, one connection pool. Separate *auth realms* (D3), separate *routers*, not separate services.
- Static/CDN: customer web app served with per-tenant branding data injected at runtime (no per-tenant builds).
- Background work: application-level scheduler inside the FastAPI process (asyncio tasks) for the pilot — **not** Celery (D7). Worker responsibilities: outbox dispatch, escalation timers, usage-counter persists, trial/dunning cron, night-ly demo reset.

## 2. Backend module map — bounded contexts, NOT layers (D14)

Note: this file is the structural commitment, not just prose. This layout exists in Phase 0 — before any M1/M2 code is written (00 §3 sequencing rule). Model classes are grouped **inside** their owning module; routes are thin composition layers over module services.

```
backend/app/
  core/                config, security primitives, logging, app assembly
  db/                  session, base, RLS session-var helpers
  shared/              cross-cutting kernel — zero domain logic
    context.py           TenantContext
    errors.py            AppError hierarchy + code registry
    audit.py             record_audit(ctx, action, ...) facade
    events.py            BusEvent base, registry, in-process dispatch hooks
    money.py             Money type
    flags.py             feature-flag evaluation
  modules/
    identity/            users, auth tokens, refresh sessions, password reset
    tenancy/             tenants, branches, memberships, membership_branches, roles
    catalog/             menu categories/items/options, branch overrides, publish
    operations/          tables, dining_sessions, orders, order_items   ← owner of the serving state machine
    kitchen/             kitchen_tickets, kitchen_ticket_items
    billing/             bills, bill_items, discounts
    payments/            payments, payment_events, per-tenant gateway adapters + webhooks
    service_calls/       guest/kitchen service calls, waiter_requests
    notifications/       outbox delivery, SSE topic fan-out, escalation timers
    entitlements/        plans, usage_counters, enforcement helpers
    reports/             read-only aggregations, EOD snapshots
    platform/            platform_admins, platform invoices/billing events, platform audit
    audit/               tenant append-only audit log

  # every module dir:
  #   models.py · schemas.py · repositories.py · services/__init__.py (public iface) · router.py · events.py
  api/
    v1/                  composes routers FROM modules (staff realm) — thin
    qr/                  customer QR (customer realm) — thin
    platform/            super admin (platform realm) — thin
  workers/               scheduler/orchestrator — see §2.5 (NOT a module)
```

## 2.1 Module contract (normative — details in 21 §10)

1. **Table ownership:** every table has exactly one owning module (§2.2 map). Other modules read that data only through the owning module's **public service interface** (`services/__init__.py`, functions without `_` prefix). The kitchen module never imports `orders` tables — it calls `operations.get_order_for_kitchen(ctx, order_id)`.
2. **Service interfaces:** module's public surface = exported functions in `services/__init__.py` with typed signatures taking `(db, ctx, ...)`. Private helpers are `_`-prefixed and unexported.
3. **No cross-module repositories:** a module cannot import another module's repository. Reports query orders via `operations.query_orders_for_report(ctx, window)` or a read-model sync — never via raw `Order` model import.
4. **Cross-module side effects via events only** (§2.3): `operations` does not call `billing.issue_bill` when an order completes; it emits `order.completed` and billing reacts.
5. **Import-linter with teeth (CI-blocking):** layered `api → services → repositories → models` **within** each module; forbidden contracts between modules:
   ```
   [importlinter]
   root_package = app
   [importlinter:contracts]
   name = no cross-module repositories
   type = forbidden
   source_modules = app.modules
   forbidden_modules = app.modules.*.repositories  # each sibling source separately
   name = no cross-module models
   type = forbidden
   name = api is a composition layer
   ...
   ```
   Full config lives in `21 §10.2`; CI job `import-lint` fails the merge on violation.
6. **New module checklist** and **extraction checklist** are in `21 §10.3–10.4`.

## 2.2 Bounded contexts × table ownership

| Module | Owns (tables) | Consumes from others |
|--------|---------------|----------------------|
| identity | users, refresh_tokens, revoked_jti | — |
| tenancy | tenants, branches, memberships, membership_branches, roles, tenant_settings | identity (users) |
| catalog | menu_categories/items/option_groups/options, menu_item_branch_overrides | tenancy (branches) |
| operations | restaurant_tables, dining_sessions, orders, order_items | catalog (menu read), tenancy, entitlements (counter) |
| kitchen | kitchen_tickets, kitchen_ticket_items | operations (order items view) |
| billing | bills, bill_items | operations (completed orders view) |
| payments | payments, payment_events | billing (bill payable view), tenancy (gateway config) |
| service_calls | service_calls, waiter_requests | operations (session/table view) |
| notifications | outbox_events | bus events from all |
| entitlements | plans, usage_counters | tenancy (live subscription status) |
| reports | eod_reports | read-only query interfaces of operations/billing/payments |
| platform | platform_admins, platform_invoices, platform_billing_events, platform_audit_logs | tenancy (tenant status) |
| audit | audit_events | record_audit facade used by all |

## 2.3 Internal event bus (D15)

Same mechanism as the customer-facing outbox — one bus, two audiences:

- **Internal subscribers:** module event handlers (e.g., `kitchen` reacts to `order.accepted`; `billing` reacts to `order.completed`).
- **External fan-out:** SSE/WS/push/email per `13`.
- Events are **typed Pydantic models** in the emitting module's `events.py` (`OrderAccepted(event_version=1, order_id, tenant_id, branch_id, actor_membership_id)`), registered in `shared/events.py`. Consumers bind to the schema model, not the payload dict — fabricating a payload fails type-check.
- Delivery: dispatcher claims outbox rows (`FOR UPDATE SKIP LOCKED`), invokes registered handlers per event type **idempotently** (each handler dedupes on `(event_id, handler_name)`), then marks delivered. Failed internal handler ⇒ retried with backoff; **never rolls back the emitter's transaction** (the outbox row committed with the business change is the guarantee).
- Catalog lives in `13 §2` (now split internal/external there).

## 2.4 Feature flags

- Storage: `platform_config` rows in Postgres — same runtime-config store the migration flags (§17) use. Three axes: `platform` (rollout of a feature to all), `tenant` (override, e.g. beta partner), `plan` (via entitlements — that's `07`, not a flag).
- Evaluation: `shared/flags.py` → `ctx.flags` snapshot per request; deny-closed default for platform flags; `enabled` entitlements are checked separately from flags (07 §1) so "feature exists on plan" vs "flag off for rollout" can't be conflated.
- Clients read evaluated state via `GET /api/v1/tenant` (computed, never raw flags); mobile also via `GET /config/client-versions` (16 §6).

## 2.5 The scheduler is an orchestrator, not a module

Background work runs as asyncio tasks inside the API process (D7/D16). The scheduler touches data from many modules — therefore: **it may call only module public service interfaces; it must not import any module's repositories or models.** It is a de-facto super-module; this rule keeps that power auditable and keeps extraction options open.

Responsibilities: outbox dispatcher (13 §1), escalation timers, entitlement reconciliation (07 §3), subscription/trial lifecycle cron (06), nightly demo reset (24 §4 — must set `app.current_tenant_id` per its transactions or use the audited bypass role, 04 §8), report rollups (25 §6), token/cleanup crons (05).

Per-tenant batches run in their own transactions with the RLS variable set (04 §3). Worker modules get their own `workers/` package at the composition level — thin, like `api/`.

## 2.6 Module extraction playbook

The promise "modular monolith" means extraction is *possible*, not *free*. Difficulty is documented, honestly:

| Module | Dependency surface | Emits / consumes | Extraction | Prereqs |
|--------|--------------------|------------------|------------|---------|
| notifications | lowest — bus + SSE | consumes all | **low** | event bus durable (D15) |
| entitlements | low — plans/counters read-owned | emits overage/usage | **low** | counters API seam (07 §3) |
| audit | low — append-only + facade | consumes audit calls | **low** | facade only |
| kitchen | medium — reads operations order state | order.accepted ← / ticket.* → | **medium** | order read-model interface |
| billing/payments | medium-high — money-critical joins to operations | order.completed ← / payment.succeeded → | **medium-high** | read-model sync; saga for bill finalization |
| operations | highest — the hub (sessions, tables, orders, entitlement calls) | emits most events | **high** (probably never) | read-model for every consumer |

Rule: any design decision that raises an extraction difficulty one level above the "Prereqs" row must be flagged in review (checklist §12).

## 3. Request lifecycle (the contract every endpoint follows)

```text
Request
  → realm middleware (staff JWT / QR session / platform JWT) — sets principal
  → resolve TenantContext{ tenant_id, branch_ids, membership_id, user_id,
                            permissions, entitlements_snapshot, flags, request_id }
      sources: staff JWT (+live membership check) | QR token→table→branch→tenant
               | platform token (+ explicit tenant path param)
  → tenant status gate (suspended/expired handling with graceful rules, D10)
  → entitlement precheck (mutation-only; reads never blocked — D9/§07)
  → service call with ctx (module public service interface — 02 §2.1)
  → repository queries ALWAYS include ctx filters
  → transaction: SET LOCAL app.current_tenant_id (once RLS is on, M5)
  → commit → outbox events → internal handlers + external fan-out (D15)
```

`TenantContext` is a frozen Pydantic object injected by a FastAPI dependency. It is the **only** sanctioned way for services to read tenant/branch/actor (`21-coding-standards.md` makes this a lintable rule).

## 4. The one invariant that governs everything

> A repository function without an explicit `ctx` parameter fails review; a repository query that can return another tenant's row fails the isolation suite.

Enforced in three places: code review, "every repo method takes ctx" unit assertion (`18-testing-strategy.md §3`), and the cross-tenant test matrix run per PR (twice: with RLS off during M3–M4, with RLS on from M5).

## 5. Error handling model

- One exception hierarchy in `core/errors.py` carrying a stable `code` string, HTTP status, and structured `details`.
- Error codes are the API contract for UI behavior (`14-api-contracts.md §4` catalog). The UI switches on code, never message.
- Middleware asserts every serialized tenant-scoped payload matches `ctx.tenant_id` before responding (defense-in-depth; developer mistakes surface as loud 500s in staging, not silent leaks).

## 6. Concurrency and realtime

- SSE as primary transport, WS as upgrade for dashboard screens; polling fallback everywhere (`13-notifications-outbox.md`).
Topics are (`tenant`, `branch`)-scoped; subscribe validates branch membership per topic. Cross-branch event delivery never happens (never auto-fail-over).
- Session mutation conflict: optimistic version column on bill/order aggregates; 409 with `code=CONCURRENT_MODIFICATION` on mismatch. (14 §4 catalog)

## 7. Tech stack (locked)

| Layer | Choice | Why |
|-------|--------|-----|
| API | FastAPI + Pydantic v2 | Established; typed boundaries |
| ORM | SQLAlchemy 2 (async session) | Existing codebase |
| Migrations | Alembic | Existing tooling; CONCURRENTLY-capable with `op.execute` for Postgres |
| DB | PostgreSQL 16 | RLS, JSONB, partial unique indexes |
| Cache | None for pilot (in-process TTL caches only) | D7 — one fewer stateful dependency until load demands |
| Auth | Custom JWT (HS256 family, rotating secrets per realm) + HashiCorp-style env secrets | Existing approach extended |
| Payments | Existing per-tenant gateway adapter (pilot) — platform billing deferred (D6) | De-risk |
| Web | React + Vite + React Query + Zustand | Existing |
| Mobile | Expo (react-navigation via expo-router) | Existing |
| Deploy | Docker Compose (dev), single VM + managed Postgres is acceptable at launch | Complexity budget |

## 8. What is deliberately NOT in the pilot

Microservices · Redis/queues (D7) · API keys for tenants · marketplace · custom domains beyond subdomains · multi-region · per-tenant DB encryption · Celery. Each has a designed-later note in `23-decision-register.md` so their absence is chosen, not accidental.
