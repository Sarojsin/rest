# Repository-Wide Engineering Rules

These rules apply to every application and service in this repository. More specific `AGENTS.md` files extend them; they do not override security or data-integrity rules in this file.

## 1. Product invariants

1. PostgreSQL is the authoritative record for restaurant, menu, table, order, kitchen, bill, payment, and inventory state.
2. The waiter app, kitchen interface, cashier interface, customer QR website, and manager website must use the same backend records and business rules. Never implement separate competing sources of truth.
3. Customer QR orders enter `PENDING_CONFIRMATION`. Only an authorized staff action may accept them into the kitchen workflow.
4. Online payment is not confirmed by a client redirect or client-side flag. Only a verified server-to-server gateway signal or trusted gateway-status lookup can mark it successful.
5. Order workflow status, kitchen preparation status, bill status, and payment status are separate concepts. Do not combine them into one status field.
6. All restaurant-owned records are tenant-scoped from the first migration, even while only one pilot tenant exists.
7. Price, tax, discount, bill totals, and permissions are calculated/enforced on the backend. Clients display results; they do not establish financial truth.
8. Important actions are auditable. Do not hard-delete financial records, accepted orders, payment attempts, refunds, stock movements, or audit events.

## 2. Engineering approach

- Prefer a well-structured modular monolith over microservices until measured scale or team boundaries justify decomposition.
- Keep business logic in domain/service layers, not React components, FastAPI endpoint functions, ORM event hooks, or UI state reducers.
- Use explicit types, small cohesive modules, readable names, and narrowly scoped interfaces.
- Avoid speculative abstractions and premature event-driven complexity. Add abstractions where they protect a real boundary: payment providers, notification providers, storage, or tenant context.
- Use UTC timestamps in storage and convert to the restaurant's configured timezone for display and business-day reporting.
- Use UUID identifiers for externally referenced and tenant-owned entities. Never expose sequential database IDs as authorization secrets.
- Use decimal-safe/integer-minor-unit money representations, never binary floating point for monetary calculations.
- Prefer explicit status transitions and domain operations over arbitrary status updates.
- Do not silently swallow exceptions, ignore failed promises, or mark operations successful before the authoritative response arrives.

## 3. API and data contracts

- `/api/v1` is the API version prefix. Use request and response schemas and stable error formats.
- Generate or validate frontend API types against FastAPI's OpenAPI schema; do not hand-maintain duplicate DTO definitions when generation is practical.
- Every state-changing API must validate input, authenticate the actor where applicable, authorize the action, validate tenant ownership, and execute the write atomically.
- For retry-prone operations such as order submission and payment initiation, define idempotency semantics before implementation.
- Database changes require Alembic migrations. Never rely on automatic table creation in production.
- Migrations must be reviewed for lock duration, table rewrites, indexes, backfill strategy, compatibility with deployed code, and rollback/forward-recovery plan.

## 4. Security and privacy

- Never commit secrets, private keys, gateway credentials, database URLs, production dumps, customer tokens, or real customer data.
- Validate all input on the server. Treat all client values, URLs, status fields, prices, totals, role names, and tenant identifiers as untrusted.
- Enforce authorization on each API action, not only by hiding buttons or screens.
- Public QR endpoints need rate limiting, opaque high-entropy tokens, strict output minimization, and abuse monitoring.
- Never log passwords, access/refresh tokens, authorization headers, full payment credentials, or unredacted sensitive gateway payloads.
- Use least privilege for user roles, service credentials, database accounts, and deployment permissions.
- Keep dependencies patched and pinned; run static analysis, dependency scanning, tests, and secret scanning in CI.

## 5. Testing and Definition of Done

A feature is not done until applicable items below pass:

- Unit tests for business rules and edge cases.
- API/integration tests for authorization, tenant isolation, transactions, and persistence.
- Contract/type checks between backend and clients.
- Tests for retries, duplicates, concurrency, and failure paths for critical actions.
- UI states for loading, empty, validation error, permission denied, offline/network error, and retry where relevant.
- Accessibility checks for customer and staff interfaces.
- Logs/metrics are useful without leaking secrets or personal information.
- Documentation, migrations, and configuration examples are updated.
- CI is green; lint, formatting, type checks, and security checks pass.
- Acceptance criteria and unresolved limitations are recorded in the pull request.

## 6. Change discipline

- Before changing a data contract or status enum, search all clients, tests, event handlers, reporting queries, and migrations that depend on it.
- Do not make a breaking API change without versioning or a compatibility plan.
- Keep pull requests focused. Explain the business invariant, migration impact, test coverage, and operational impact.
- Do not claim a task is complete when tests have not been run; report exactly what was and was not verified.
