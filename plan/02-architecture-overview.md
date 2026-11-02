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

## 2. Backend module map

```
backend/app/
  core/           config, security, errors, logging, request context
  db/             session, base, RLS session-var helpers
  models/         SQLAlchemy models (tenancy/ identity/ menu/ ops/ billing/ platform/)
  schemas/        Pydantic v2 DTOs
  services/       domain services (one module per bounded capability)
  repositories/   tenant-scoped query layer — EVERY query goes through here
  api/
    v1/           staff + customer routes         (staff realm)
    qr/           customer QR routes              (customer realm)
    platform/     super admin routes              (platform realm)
  workers/        outbox dispatcher, escalation, counters, lifecycle cron
```

Module dependency rules (enforced by import-lint in CI, `18-testing-strategy.md`):

- `api → services → repositories → models`. Never repository → service, never api → repositories directly.
- `services` may not import `api` or request objects; they receive a `TenantContext` + a `Session`.
- `platform` services must never import restaurant-domain services except through the audit facade.

## 3. Request lifecycle (the contract every endpoint follows)

```text
Request
  → realm middleware (staff JWT / QR session / platform JWT) — sets principal
  → resolve TenantContext{ tenant_id, branch_ids, membership_id, user_id,
                            permissions, entitlements_snapshot, request_id }
      sources: staff JWT (+live membership check) | QR token→table→branch→tenant
               | platform token (+ explicit tenant path param)
  → tenant status gate (suspended/expired handling with graceful rules, D10)
  → entitlement precheck (mutation-only; reads never blocked — D9/§07)
  → service call with ctx
  → repository queries ALWAYS include ctx filters
  → transaction: SET LOCAL app.current_tenant_id (once RLS is on, M5)
  → commit → outbox events → (worker) SSE/WS/notification delivery
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
