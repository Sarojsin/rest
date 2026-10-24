rules/backend.md
markdown
# FastAPI Backend Rules

You are contributing to the FastAPI backend of a restaurant management system.
Follow these rules for every change. If they conflict with your instinct,
follow the rules and note the trade-off in the PR description.

## Stack (fixed for the pilot)

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (async)
- Alembic
- Pydantic v2
- PostgreSQL 15+
- `uv` for dependency management
- `ruff` for lint + format, `mypy --strict` for types
- `pytest` + `pytest-asyncio` + `httpx.AsyncClient` + `testcontainers`
- `structlog` for JSON logging
- `argon2-cffi` for password/PIN hashing
- `pyjwt` for JWTs
- Gateway SDKs per provider (do not hand-roll crypto)

## Project layout
backend/
app/
main.py # FastAPI app factory
core/
config.py # pydantic-settings Settings
security.py # JWT, password hashing, current_user deps
errors.py # AppError + exception handlers
logging.py # structlog config
permissions.py # permission codes + role defaults
db/
session.py # async engine + session factory
base.py # DeclarativeBase
models/ # SQLAlchemy models, one file per domain
migrations/ # alembic
api/
deps.py # shared dependencies (db, current_user, restaurant)
v1/
auth.py
menu.py
tables.py
orders.py
kitchen.py
bills.py
payments.py
inventory.py
reports.py
qr.py # public QR endpoints
webhooks.py # payment gateway webhooks
services/ # business logic; no HTTP here
repositories/ # query layer; no business logic here
schemas/ # Pydantic request/response models
workers/ # background jobs (payment reconcile, alerts)
tests/
unit/
integration/
e2e/

text

- **Routes** are thin: parse request, call a service, return response.
- **Services** own transactions and business rules.
- **Repositories** own queries. Never leak ORM objects to the API layer.
- **Schemas** are Pydantic and live next to nothing else.

## Async rules

- All DB and network calls are `async`.
- Never call blocking libraries from async code. Use `run_in_threadpool` for
  unavoidable sync SDKs, or pick an async SDK.
- Never hold a DB transaction open during a network call.
- Long-running work (payment reconciliation, notifications, receipts) goes to
  a background worker, not the request path.

## Configuration

- All configuration via `pydantic-settings` from environment variables.
- No secrets in code or in `settings.py` defaults. Fail fast if a required
  secret is missing at startup.
- `Settings` is cached and injected; never re-read env in request handlers.

## Authentication

- Staff auth: email + password **or** PIN (scoped to restaurant). Both hash with
  argon2id. PINs are 4–6 digits and rate-limited.
- JWT: `HS256` with a strong secret from env; rotate on a documented schedule.
- Access token TTL: 15 minutes. Refresh token TTL: 7 days, rotating, stored
  hashed in `refresh_tokens`.
- Customer QR flow: no user auth. The QR URL contains `qr_token`; the backend
  exchanges it for a short-lived (e.g. 30 min) signed session token bound to
  the table + dining_session. Session token goes in a cookie or `Authorization`
  header for subsequent customer calls.
- Reject tokens whose `restaurant_id` or `user_id` no longer matches an active
  record on every request via the `current_user` dependency.

## Authorization

- Use a `require_permission("order.accept_qr")` dependency on every
  state-changing route.
- Never check `if user.role == "manager"` inline. Use permission codes.
- Permissions live in `permissions.py` and the DB. Add new permissions through
  a migration + seed, not inline strings.
- Every admin/financial action writes an `audit_logs` row inside the same
  transaction.

## Validation & schemas

- Pydantic v2 models for every request and response.
- Input validation via Pydantic only. Do not manually parse JSON.
- Response models are explicit and versioned under `/api/v1`.
- Never return raw ORM objects or SQLAlchemy `Row` objects.
- Use `model_config = ConfigDict(from_attributes=True)` only on output schemas
  that need it.

## Errors

- Define `AppError(code: str, http_status: int, message: str, details=None)`.
- Register global exception handlers that convert `AppError`,
  `RequestValidationError`, and unhandled exceptions into the shared error
  envelope from `rules/shared.md`.
- Never `raise HTTPException` from a service. Services raise `AppError`.
- Log every 5xx with the request ID, traceback, and safe context. Never log
  tokens, PINs, or gateway payloads that contain card data.

## Database usage

- One `AsyncSession` per request, injected via dependency.
- `session.begin()` around write operations. Commit in the service, not in the
  route.
- No lazy loading. Use explicit `selectinload`/`joinedload` in repositories.
- Never build raw SQL strings from user input. Use `text()` only with bound
  parameters.
- Money and quantities are `Decimal` only when reading `NUMERIC`; convert to
  int cents at the boundary.

## Idempotency

- For `POST /orders` and `POST /payments`, read `Idempotency-Key` header.
- Look up in `idempotency_keys`. If found with same request hash, replay the
  stored response. If found with different hash, return
  `409 IDEMPOTENCY_KEY_CONFLICT`.
- Otherwise, `INSERT … ON CONFLICT DO NOTHING` to lock the key, perform the
  action, store the response, then return.

## Payment integration

- Online payments go through the provider's hosted checkout or its
  server-to-server intent API. Never collect raw card data.
- Every gateway webhook endpoint:
  1. Verifies signature using the provider's SDK.
  2. Is idempotent — inserts a `payment_events` row keyed by the gateway's
     event ID (use a unique partial index on payload→event id or store it in
     a dedicated column; do not rely on timestamps).
  3. Updates `payments.status` from gateway truth only.
  4. Never marks a payment `succeeded` from a browser redirect alone.
- A reconciliation job periodically fetches gateway truth for payments stuck in
  `pending` > 5 minutes and emits `payment_events` `reconciled`.
- Payment amounts in requests are validated against server-computed bill totals.

## QR order flow

- `POST /api/v1/qr/{qr_token}/orders`:
  - Resolves table + dining session from `qr_token`. Rejects rotated tokens.
  - Validates menu availability and current prices server-side.
  - Creates an order with `channel='qr'`, `status='pending_confirmation'`.
  - Emits a notification to the staff pending-queue channel.
  - Returns the pending order and a customer-facing status URL.
- `POST /api/v1/orders/{id}/accept`:
  - Requires `order.accept_qr`.
  - Transitions `pending_confirmation → accepted`.
  - Creates `kitchen_tickets` per station.
  - Writes audit log.
- `POST /api/v1/orders/{id}/reject`:
  - Requires `order.reject_qr`, mandatory `rejection_reason`.
  - Writes audit log.

## Background workers

- Use a simple in-process worker first (`asyncio.create_task` **only** for
  non-critical fire-and-forget) and a durable queue (e.g. Postgres-backed or
  Redis) for anything that must not be lost.
- Required workers by Stage 2/3: notification fan-out, payment reconciliation,
  receipt generation, delayed-ticket alerts.
- Workers must be idempotent and log with `request_id`/job ID.

## Logging & observability

- Structured JSON via `structlog`. Every log line includes `request_id`,
  `restaurant_id`, `user_id` (when known), `route`.
- Emit request duration and status code.
- Expose `/healthz` (liveness) and `/readyz` (DB reachable) endpoints.
- Expose Prometheus metrics at `/metrics` (do not publicly expose in prod;
  network-restrict).

## Security

- Enforce HTTPS-only in production. HSTS.
- CORS: explicit allow-list per environment. No `*` with credentials.
- Rate-limit auth endpoints and QR order submission (per IP and per token).
- Set `SameSite=Lax` on refresh cookies; use `Secure` in prod.
- Validate file uploads (menu images) with content-type + size limits; store
  in object storage, never serve from the app filesystem.
- Run dependency vulnerability scan in CI.

## Testing

- Every service function has unit tests.
- Every route has at least one integration test against a real Postgres
  container.
- Payment webhook tests simulate provider signatures; verify idempotency.
- QR flow tests: valid token, rotated token, double submit with same
  idempotency key, rejected order, accept-to-kitchen transition.
- Coverage target: 80% lines for `services/` and `repositories/`. Do not
  chase coverage on route wiring.

## Code style

- `ruff check` and `ruff format` are mandatory and enforced in CI.
- `mypy --strict` on `app/`. No `Any` in public functions without comment.
- No commented-out code, no dead branches, no `TODO` without an issue link.
- No global mutable state.