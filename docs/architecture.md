# System Architecture

**Status:** Proposed baseline for requirements and implementation planning.

## 1. High-level architecture

```text
Customer phone browser
  └── React customer QR website

Waiter / kitchen / cashier devices
  └── React Native staff app

Owner / manager browser
  └── React management website (or protected area of the web app)

All clients
  └── HTTPS JSON API: FastAPI (/api/v1)
        ├── Authentication and authorization
        ├── Tenant-scoped application services
        ├── Domain rules and transactional workflows
        ├── Payment-provider adapters and verified webhooks
        ├── PostgreSQL (authoritative state)
        ├── Object storage (menu images and permitted documents)
        ├── Redis (optional: rate limits, caches, ephemeral coordination)
        └── Durable background jobs / transactional outbox
```

### Architectural recommendation

Use a **modular monolith** for the pilot. Keep domain modules separate in code, but deploy one API service until actual traffic, team ownership, fault isolation, or operational evidence justifies splitting it. Microservices add distributed transactions, deployment coordination, service-to-service security, and observability costs that are not justified by the current requirements.

## 2. Suggested backend modules

- `identity`: users, memberships, roles, login, refresh sessions, password recovery.
- `restaurants`: tenant profile, configuration, timezone, currency, tax configuration references.
- `tables`: restaurant tables, opaque QR credentials, dining sessions.
- `menu`: categories, items, modifiers/options, publishing, availability.
- `orders`: source channel, submission idempotency, confirmation/rejection, amendments, cancellation.
- `kitchen`: tickets, item preparation states, readiness events.
- `billing`: bills, immutable line snapshots, totals, discounts and taxes.
- `payments`: payment attempts, gateway adapters, webhooks, refunds, reconciliation.
- `inventory`: ingredients, recipes, stock movement ledger, suppliers and purchasing (phase-gated).
- `reports`: authorized operational and financial reports derived from persisted facts.
- `audit`: immutable business audit records.
- `platform`: health, configuration, request IDs, outbox dispatcher, rate-limit integration.

Module dependencies should be intentional. For example, `payments` may reference `billing` identifiers and totals, but frontend code must never own payment settlement logic. Avoid circular module imports; use narrow service interfaces and domain events where needed.

## 3. Primary data ownership

- PostgreSQL owns all durable business state.
- Redis is disposable infrastructure. Losing Redis must not erase accepted orders, payments, bills, or stock movements.
- The frontend may cache display data but must revalidate data before critical changes and must not treat stale cached information as authoritative.
- Object storage holds images/documents. Store object keys and metadata in PostgreSQL; do not store large binary blobs in ordinary business tables unless there is a specific reason.
- Audit records and payment/provider references must be persisted transactionally with the relevant business change where possible.

## 4. Transaction boundaries

Use one database transaction for each state-changing business operation. At a minimum:

### Accept customer QR order

1. Load order with tenant scoping and row lock/optimistic concurrency check.
2. Verify current status is `PENDING_CONFIRMATION`.
3. Verify the actor has the permission to confirm QR orders.
4. Revalidate item availability and the stored price/tax snapshot policy.
5. Attach to an active dining session or create one under the table's session concurrency constraint.
6. Transition order to `ACCEPTED` and create the kitchen ticket/items.
7. Write audit/outbox events.
8. Commit once; only then tell the client that acceptance succeeded.

If any required step fails, roll back the whole operation. A retry must not create a second session or kitchen ticket.

### Initiate online payment

1. Check the bill is payable, its version/total is stable, and no conflicting payment attempt is active.
2. Create a durable pending payment intent with a unique idempotency key and provider reference before or as part of the provider interaction according to the adapter's safe retry design.
3. Do not mark it successful based on the browser return URL.
4. Verify signed webhook messages or query the provider securely; enforce provider event/payment uniqueness.
5. Atomically record settlement state and any audit/outbox event.

Do not hold a database transaction open while waiting on a slow external payment API. Design for timeouts where the external result is unknown and reconcile using provider identifiers.

### Record cashier payment

Validate bill access, cashier permission, currency, amount, current outstanding balance, and idempotency. Insert payment and update settlement/bill state atomically. A duplicate request must not record the same tender twice.

### Record inventory movement

Insert an append-only stock movement and update any materialized stock balance in the same transaction. Adjustments require a reason and actor. Reconciliation can recompute the balance from movements.

## 5. Concurrency controls

- Enforce at most one active dining session per table with a PostgreSQL partial unique index or equivalent transactional guarantee.
- Use row locks or optimistic version columns when two waiters/cashiers may edit the same session, bill, order, or stock balance.
- Use idempotency keys for order submissions, online payment initiation, and other externally retried writes.
- Enforce unique provider payment IDs and webhook event IDs at the database level.
- Use atomic transitions such as `UPDATE ... WHERE status = expected_status`; do not read a status then blindly overwrite it.
- Do not depend on an in-process Python lock for correctness when multiple API workers/instances may run.

## 6. Real-time updates

Kitchen and waiter screens need timely updates, but real-time transport is not durable storage.

- The initial release may use polling or Server-Sent Events; WebSockets are an option after validating connection counts and deployment needs.
- Every client reconnect must be able to fetch the authoritative current state from the API.
- If Redis pub/sub is used to fan out updates, treat it as a notification path, not the source of truth. Clients must recover from missed events by refetching.
- Use a transactional outbox when a committed business change must reliably trigger a background notification. The dispatcher must handle retries and duplicate delivery.
- Display stale/disconnected state clearly; do not show a notification as proof that an order or payment was committed.

## 7. Tenant model

The pilot starts with one restaurant, but every tenant-owned record should carry `restaurant_id` or be reached only through a tenant-owned parent and verified composite relationship. Resolve the tenant from authenticated membership or from a validated public QR token—not from an arbitrary client-provided tenant ID.

- All staff queries must be scoped by the membership's restaurant.
- Public QR routes must resolve the tenant through the opaque token and expose only the menu/table context needed for ordering.
- Add automated tests that attempt cross-tenant reads, updates, exports, IDs, bill access, QR status access, and webhooks.
- The database should enforce tenant-consistent relationships where practical, using composite foreign keys and unique constraints.

Tenant groundwork does not mean multi-branch operations are in scope. Branch accounting, central menus, cross-branch inventory, and chain-wide reports remain deferred.

## 8. Deployment topology (proposed)

- HTTPS ingress/load balancer or managed application ingress.
- Horizontally scalable stateless FastAPI instances.
- Managed PostgreSQL with automated backups and point-in-time recovery where available.
- Optional managed Redis for rate limiting, ephemeral coordination, or cache.
- Object storage for media, fronted by a CDN when useful.
- Separate worker process for durable background jobs/outbox processing.
- React web deployment on a static host/CDN or an appropriate web platform.
- React Native builds distributed through the selected mobile release channel.
- Separate staging and production environments with independent credentials and data.

Keep API instances stateless. Sessions, authorization data, order state, and payment state must not rely on Python process memory.

## 9. API contract rules

- Base prefix: `/api/v1`.
- JSON request/response formats, UTF-8, TLS required outside local development.
- Use OpenAPI as the backend contract source; generate TS DTO/client types or add a CI check that schemas remain aligned.
- Include a request/correlation ID in logs and error responses.
- Use a consistent error envelope; do not return stack traces or database details.
- Paginate all collection endpoints that can grow.
- Add filters and sort options only when requirements are clear; whitelist sortable fields.
- Use optimistic concurrency (`version`/ETag) for editable bills or shared records when stale writes could cause financial errors.

## 10. Proposed development phases

1. **Foundation:** repo/CI, environments, auth/tenant membership, restaurant settings, migrations, audit framework, error conventions.
2. **Core dine-in flow:** tables/sessions, menu, waiter order entry, QR submission, staff confirmation, kitchen tickets/status.
3. **Billing:** bill generation, cashier tender, online payment adapter, verified webhook flow, receipts and reconciliation.
4. **Operational visibility:** reports, owner/manager UI, outbox notifications, audit search, support tooling.
5. **Inventory:** stock ledger, ingredients, recipes, suppliers/purchases, wastage and reconciliation after requirements validation.
6. **Pilot hardening:** peak-hour/load tests, recovery drills, staff training, backups restore test, security review, real baseline and acceptance metrics.
7. **Commercialization:** repeatable tenant provisioning, onboarding, support model, pricing, data export/deletion policy, and more customer pilots.
