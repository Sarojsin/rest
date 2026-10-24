# Backend Engineering Rules — FastAPI

These rules apply to the FastAPI service. Also follow the repository-wide `../AGENTS.md`, `../docs/schema.md`, `../docs/api-contracts.md`, and `../docs/security-and-operations.md`.

## 1. Architecture and package boundaries

Use a modular monolith with explicit domain boundaries. Suggested source layout:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/v1/                 # routers, dependency wiring, HTTP mapping only
│   ├── core/                   # settings, logging, security, error handling
│   ├── db/                     # session, base, migration helpers
│   ├── domain/                 # enums, transitions, domain types/invariants
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic input/output schemas
│   ├── services/               # business workflows and transactions
│   ├── repositories/           # focused persistence queries when useful
│   ├── integrations/           # payment, object storage, notifications
│   ├── workers/                # outbox/jobs
│   └── observability/           # metrics/tracing instrumentation
├── alembic/
├── tests/
├── pyproject.toml
└── alembic.ini
```

Keep module imports one-directional. `api` calls services; services apply policy and coordinate repositories/integrations; repositories handle persistence details. Domain state-transition rules must be testable without an HTTP request. Avoid a generic repository abstraction for every table if it adds no meaningful value.

## 2. HTTP endpoints and Pydantic

- Use FastAPI routers under `/api/v1`; keep route handlers thin and explicit.
- Use Pydantic v2 request/response models with strict-enough validation, bounded strings/collections, explicit enums, and separate input/output schemas.
- Set `extra="forbid"` for security-sensitive commands when practical so unexpected fields are not silently accepted.
- Never accept ORM model payloads directly or return ORM models as API contracts.
- Map domain failures to a stable problem-details error envelope. Do not return raw Python/SQL/provider exceptions.
- Use the correct HTTP status codes and avoid using a successful status for a rejected or not-yet-persisted operation.
- Add pagination caps to every unbounded listing. Whitelist sort fields. Limit nested request sizes.
- Use API dependency injection for session, authenticated actor, active tenant membership, and permission checks. Keep authorization logic shared and testable, not duplicated in every router.
- Use dependency overrides in tests; do not make tests depend on developer credentials or production services.

## 3. Authentication, tenant context, and permissions

- Use a maintained password hashing/authentication mechanism. Never roll your own cryptography.
- For browser login, prefer secure HttpOnly cookie sessions/refresh flow plus CSRF defense if topology supports it. For mobile, use short-lived bearer access tokens and rotated refresh tokens stored on device in platform secure storage. Implement the selected strategy consistently.
- Resolve authenticated user, active membership, `restaurant_id`, and permission in a trusted dependency. Never derive tenant authorization from body/query data.
- Every repository method that accesses tenant-owned data must require tenant context or a tenant-scoped aggregate. Avoid helper methods like `get_order(id)` that can silently query across tenants.
- Return not-found for unauthorized cross-tenant identifiers where exposing existence would leak data.
- Write tests for staff who are disabled/revoked, users with multiple memberships, wrong tenant, insufficient permission, and role changes.

## 4. Database and transaction discipline

- Follow `schema.md` and `../docs/schema.md`. Use SQLAlchemy 2.x typed mappings and Alembic migrations.
- Use `NUMERIC`/integer-minor-unit representations for money/quantities, never float arithmetic.
- Put a business operation's related writes in one service-owned transaction. Avoid committing from a repository/helper.
- Do not hold DB transactions during slow network calls to payment gateways or object stores.
- Use row locks, version checks, unique constraints, or conditional updates for session/order/bill/payment concurrency. In-process locks are not sufficient across API workers.
- Translate expected integrity/concurrency errors into stable domain conflicts. Do not leak constraint names/SQL to clients.
- Use eager loading/selectinload or explicit query DTOs to prevent N+1 behavior. Inspect query counts and plans for kitchen/report endpoints.
- Do not use `create_all()` as a production migration system.

## 5. Business workflows must be domain operations

Implement explicit service methods, not generic arbitrary status patching, for at least:

- `submit_qr_order`: validate QR/table/menu, price/availability, quantity/options, idempotency and limits; create `PENDING_CONFIRMATION` only.
- `accept_qr_order`: check permission/state; attach or create dining session safely; create kitchen ticket/items; record audit and outbox event; commit atomically.
- `reject_qr_order`: preserve order and reason; only allowed from pending state.
- `transition_kitchen_item`: enforce legal state progression and kitchen permissions; record actor/time.
- `issue_bill`: compute server-side totals, persist immutable line/tax/price snapshots, and freeze a bill version for payment.
- `record_cash_payment`: validate current balance, permission, method, and idempotency; atomically update payment/bill settlement.
- `create_online_payment_intent`: validate bill version and outstanding balance; create a durable attempt; handle provider timeouts without duplicate charges.
- `process_payment_webhook`: verify raw-body signature, provider/account/reference, amount/currency and event uniqueness; commit state idempotently.
- `request_refund`: verify remaining refundable balance and permission; retain a durable record and reconcile provider outcome.
- `record_stock_movement`: append a movement and update any stock balance atomically.

No endpoint may mark a QR order accepted without creating the required kitchen workflow atomically. No endpoint may mark an online payment successful from a browser-provided status alone.

## 6. Idempotency, retries, and async work

- Implement an idempotency utility/service with stored request hash and result/reference, or equivalent database constraints for individual domains. Document key scope and retention policy.
- The same key and same request returns the stable prior result. Same key with different request body returns `409`.
- Store provider/payment IDs and webhook event IDs under unique constraints. Assume external callbacks are at-least-once and may be out of order.
- Use a durable job queue/outbox for important notification and reconciliation work. An in-memory background task is not adequate for work that must survive process restart.
- Jobs must be idempotent, retry with bounded exponential backoff/jitter, record last failure safely, and expose dead-letter/manual-retry handling.
- Do not rely on Redis pub/sub delivery for durable state. Use PostgreSQL/outbox as the durable source.

## 7. Integration boundaries

- Place payment gateway calls behind an interface/adapter; normalize provider statuses into domain states.
- Keep secrets in injected settings/secret manager, never in code, DB fixtures, logs, or API responses.
- Set network timeouts and classify retryable vs permanent errors. Do not blindly retry a charge after timeout; first reconcile the provider reference.
- Verify webhook signatures exactly as required by the provider; use the raw request body where required.
- For images, use constrained object-storage upload flows, enforce size/type/signature, and never fetch arbitrary user-supplied URLs server-side (avoid SSRF).
- Treat external providers as unavailable at times; core existing orders and cashier workflows should remain readable when a provider is down.

## 8. Configuration and observability

- Use typed Pydantic Settings; validate required production settings at startup and fail fast if invalid.
- Commit `.env.example` with placeholder names only; `.env` and credentials stay ignored.
- Use structured logs and request IDs. Redact authorization, secrets, status tokens, reset tokens, and sensitive payment payloads.
- Provide liveness/readiness endpoints. Do not expose detailed dependency configuration or exception internals through them.
- Instrument request latency/error rate, DB pool, key workflow timings, pending QR order age, payment unknown state, webhook lag, job/outbox backlog, and reconciliation errors.
- Keep health endpoints and metrics protected or minimized to prevent leaking operational details.

## 9. Tests and quality gates

Use pytest and a real PostgreSQL test service for integration tests. Test at least:

- Domain state transitions and invalid transitions.
- Tenant isolation and permission checks on every sensitive module.
- Database uniqueness, partial indexes, locks, concurrent accepts, and concurrent payments.
- Idempotent duplicate order submission/payment requests.
- Payment webhook signature/replay/out-of-order/amount/currency cases.
- Transaction rollback when a kitchen ticket or audit/outbox write fails.
- Tax/money rounding with representative edge cases.
- Alembic from empty DB and previous supported schema.
- Error response contract and no sensitive information in error/log output.

Required checks: formatter, Ruff lint, type checker (mypy or pyright; choose one), unit tests, integration tests, coverage gate on critical service modules, dependency/security scan, secret scan, migration check. Pin dependencies in a committed lockfile.
