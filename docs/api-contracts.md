# API Contract and Workflow Specification

**Base path:** `/api/v1`  
**Format:** JSON over HTTPS, except provider webhooks which follow the provider's defined format  
**Contract source:** FastAPI OpenAPI schema; generate TypeScript types/client where practical.

This is a logical endpoint proposal, not a final OpenAPI document. Final routes and fields should be confirmed while implementation tickets are written.

## 1. Contract conventions

### 1.1 Authentication

- Staff endpoints require authenticated identity, active restaurant membership, and the specific permission.
- Public QR endpoints resolve a table through a valid QR code token and return only public menu/order-status data.
- Public order-status access requires a separate high-entropy, read-only order-status credential; the physical table QR token must not grant access to previous orders or bills.
- Payment webhooks use provider signature verification and provider-specific replay protection; they do not use normal user login.
- Do not assume a valid authentication token implies access to every restaurant. Resolve membership and tenant context for each request.

### 1.2 Request IDs, idempotency, pagination

- Accept/propagate a request correlation ID and include one in response headers/log context.
- Require an `Idempotency-Key` header for retry-prone writes, including order submission, payment initiation, and cashier payment recording. Scope keys by tenant, actor/public flow, endpoint, and a request-body hash. Reusing a key with a different body must produce a conflict.
- Collections use bounded cursor or limit/offset pagination. Enforce a maximum page size. Use stable ordering and opaque cursors when changing data during paging could skip/duplicate records.
- Use a `version` field or ETag/`If-Match` on shared editable resources such as bills and orders when a stale update could overwrite a newer action.

### 1.3 Error shape

Use an RFC 9457/7807-compatible problem-details response (choose and standardize one exact format), with stable fields such as:

```json
{
  "type": "https://api.example.invalid/problems/order-state-conflict",
  "title": "Order state conflict",
  "status": 409,
  "code": "ORDER_NOT_PENDING_CONFIRMATION",
  "detail": "This order can no longer be accepted.",
  "request_id": "opaque-correlation-id"
}
```

The example domain is reserved for documentation. Production errors must not expose stack traces, SQL, secrets, internal provider payloads, or whether another tenant's protected object exists.

Recommended status semantics:

- `400`: malformed request/validation when not using `422` for schema validation.
- `401`: missing/invalid authentication.
- `403`: authenticated but not permitted (or consistently use `404` for protected-object concealment where appropriate).
- `404`: not found in the caller's authorized scope.
- `409`: state/concurrency/idempotency conflict.
- `422`: syntactically valid but semantically invalid request.
- `429`: rate limited, with `Retry-After` where appropriate.
- `502/503`: temporary upstream/provider/service failure with safe retry semantics.

## 2. Proposed endpoint inventory

### 2.1 Authentication and current context

- `POST /auth/login` — staff login; apply rate limiting and generic failure messages.
- `POST /auth/refresh` — rotate refresh token/session; detect reuse.
- `POST /auth/logout` — revoke current refresh session/family as defined.
- `POST /auth/password/forgot` and `POST /auth/password/reset` — only if password auth is selected; use one-time hashed reset tokens and neutral responses.
- `GET /me` — current user and minimal profile.
- `GET /me/restaurants` — active memberships and role labels, without exposing secrets.
- `POST /me/active-restaurant` — only if the client must choose among memberships; verify membership on the server.

### 2.2 Public customer QR website

- `GET /public/qr/{qr_token}/menu` — resolve active QR token; return restaurant name, table display label, published categories/items/options (including display-only `ingredients_text`), current menu version, and only public settings.
- `POST /public/qr/{qr_token}/orders` — submit a pending QR order; require an idempotency key; backend validates table/token, menu publication, quantities, options, availability, and prices; return `PENDING_CONFIRMATION` plus a one-time/read-only status credential or safe status URL.
- `POST /public/qr/{qr_token}/service-calls` — guest presses "Call waiter". Deduplicated server-side: while a `REQUESTED` call is open for the table, repeated taps return the existing call (`deduplicated: true`) instead of creating duplicates. No customer identity is recorded.
- `GET /public/qr/{qr_token}/service-calls/latest` — read-only, QR-token-scoped status so the guest can see whether the waiter acknowledged the request. Discloses only the latest call's status/timestamps for that table.
- `POST /public/order-status-sessions` — exchange a one-time order-status credential for a short-lived, limited session if this safer pattern is selected.
- `GET /public/orders/{status_token}` — minimal read-only status, permitted items/summary, and safe status timestamps; never expose staff notes, other orders, internal audit, or broad bill details.
- `POST /public/orders/{status_token}/cancel-request` — optional only if customer cancellation is supported; it requests cancellation and does not bypass staff/kitchen rules.
- `POST /public/bills/{checkout_token}/payment-intents` — optional customer checkout endpoint after payment timing and public-bill access rules are finalized. Must not reveal bills by table ID alone.

Public endpoints require per-IP/token/table rate limits, abuse monitoring, strict request size limits, no cache of private order status, and generic error behavior that does not enumerate tables or orders.

### 2.3 Restaurant settings and users (staff only)

- `GET /restaurant` — current tenant's safe settings/profile.
- `PATCH /restaurant/settings` — require settings permission and audit sensitive changes.
- `GET /staff` / `POST /staff/invitations` / `PATCH /staff/{membership_id}` — staff administration and activation/revocation.
- `GET /roles` / `POST /roles` / `PATCH /roles/{id}` — if custom role editing is required; permission catalog remains code-managed.
- `GET /audit-events` — permissioned, tenant-scoped, paginated audit search.

### 2.4 Tables and dining sessions

- `GET /tables` — list tables and computed/current state.
- `POST /tables` / `PATCH /tables/{id}` — manager permissions.
- `POST /tables/{id}/qr/rotate` — revoke old code and generate replacement; never return stored raw old tokens.
- `POST /tables/{id}/sessions` — open a table session, if explicit staff opening is chosen.
- `GET /sessions/{id}` — order/session summary within tenant.
- `POST /sessions/{id}/checkout` — request/freeze bill for checkout under the approved bill policy.
- `POST /sessions/{id}/close` — only when the bill/session closure invariants are satisfied.
- `POST /sessions/{id}/transfer` — deferred unless table transfer is approved; must lock both tables/sessions and preserve history.

### 2.5 Menu

- `GET /menu` — staff view including drafts/unavailable items where permitted, and each item's `ingredients_text`.
- `POST /menu/categories`, `PATCH /menu/categories/{id}`.
- `POST /menu/items`, `PATCH /menu/items/{id}`, `POST /menu/items/{id}/availability`.
- `POST /menu/publish` — publish a consistent menu revision.
- `POST /menu/items/{id}/image-upload` — issue constrained upload instructions or handle validated upload; never accept arbitrary remote URLs as trusted images.

All write routes require menu permissions. Customer menu responses show only currently public items, their display-only `ingredients_text`, and do not reveal internal cost, stock, or notes.

### 2.5b Service calls (waiter assistance)

- `GET /service-calls?status=REQUESTED` — tenant-scoped list; read permission `orders.read`; includes `table_display_name` so staff can find the table. Polling is acceptable (the architecture keeps real-time transport out of durable storage).
- `POST /service-calls/{id}/acknowledge` — waiter confirms they are attending; permission `tables.manage`; idempotent (`ACKNOWLEDGED` re-acknowledge returns the same state). Requires the append-only audit trail like other staff actions.

### 2.6 Orders and kitchen

- `POST /orders` — authorized waiter order; may create a draft or be explicitly submitted to kitchen according to the chosen UI flow.
- `GET /orders` — filtered, tenant-scoped list with cursor/limit.
- `GET /orders/{id}` — authorized order details.
- `POST /orders/{id}/accept` — authorized staff confirmation of a pending QR order; atomically assigns session, creates kitchen ticket, records audit/outbox event.
- `POST /orders/{id}/reject` — authorized rejection with reason code/note.
- `POST /orders/{id}/cancel` — policy-controlled cancellation; accepted orders may require manager confirmation or a separate kitchen action.
- `POST /orders/{id}/amendments` — explicit post-submission amendment flow if supported; preserve original values and kitchen visibility.
- `GET /kitchen/tickets` — kitchen-scoped queue/status view.
- `POST /kitchen/tickets/{id}/call-waiter` — kitchen signals a ticket is done: forces open items to `READY` and raises a `KITCHEN` service call (idempotent while a `REQUESTED` call is open for the ticket); requires `kitchen.update`.
- `POST /kitchen/ticket-items/{id}/status` — item-level preparation updates, if required by service workflow.

Use domain operations, not generic `PATCH {status: ...}`. The server validates allowed current-to-next transitions and permission for each transition.

### 2.7 Bills, cashier payments, and online payments

- `GET /sessions/{id}/bill` — authorized current bill/preview.
- `POST /sessions/{id}/bill/issue` — calculate and persist bill snapshot; return version and totals.
- `POST /bills/{id}/cash-payments` — record cashier tender with amount/method/reference; require cashier permission and idempotency.
- `POST /bills/{id}/online-payment-intents` — create provider-specific checkout intent for a stable bill version; require payment eligibility and idempotency.
- `GET /bills/{id}/payments` — authorized payment list; redact provider secrets.
- `POST /payments/{id}/refunds` — permissioned refund request, approval policy, provider call, idempotency, reconciliation.
- `POST /webhooks/payments/{provider}` — raw body verification using the provider's signature method, replay protection, minimal safe acknowledgement. Do not parse/normalize the body in a way that invalidates signature verification.
- `GET /reports/payment-reconciliation` — permissioned comparison between internal records and provider settlement exports where available.

If bill splitting is not in MVP, do not expose split/transfer endpoints by accident. Do not accept arbitrary client totals; the backend computes the payable amount and validates the bill version.

### 2.8 Inventory (phase-gated)

- `GET /inventory/ingredients`, `POST /inventory/ingredients`, `PATCH /inventory/ingredients/{id}`.
- `GET /inventory/stock`, `POST /inventory/adjustments` with reason and permission.
- `GET /inventory/movements` — append-only movement history.
- `POST /inventory/suppliers`, `POST /inventory/purchase-orders`, `POST /inventory/purchase-orders/{id}/receipts`.
- `POST /inventory/recipes`, `PATCH /inventory/recipes/{id}` — recipe changes create a new version/effective record.

Purchase orders do not add stock until goods are received. Stock adjustment endpoints create ledger events; they do not simply overwrite a quantity.

### 2.9 Reports

Initial candidate reports:

- `GET /reports/sales?from=...&to=...`
- `GET /reports/menu-performance?from=...&to=...`
- `GET /reports/discounts-cancellations?from=...&to=...`
- `GET /reports/payment-summary?business_date=...`
- `GET /reports/kitchen-times?from=...&to=...`
- inventory reports after inventory is implemented.

All reports must define timezone/business-day boundaries, included/excluded statuses, refund treatment, tax treatment, currency, and rounding. Reuse a canonical financial definition across UI exports and dashboard summaries.

## 3. Status and workflow contract

### Order workflow

`PENDING_CONFIRMATION -> ACCEPTED | REJECTED | CANCELLED`  
`ACCEPTED -> CANCELLED | COMPLETED` under policy; completed should be reached only when the dining/order workflow is done. State transitions must be server-enforced. No transitions out of terminal rejection/cancellation without an explicit audited correction process.

### Kitchen item workflow

`NEW -> PREPARING -> READY -> SERVED`  
`NEW/PREPARING/READY -> CANCELLED` only where the staff policy allows it. Skipping states, reversing a served item, or cancelling after preparation may require a manager path and a reason.

### Bill workflow

`OPEN -> ISSUED -> PARTIALLY_PAID -> PAID` with `ISSUED -> PAID` allowed for full settlement. `OPEN/ISSUED -> VOID` only by authorized action and according to payment-attempt state. Avoid changing bill totals while an online payment outcome is unknown.

### Payment workflow

`INITIATED -> PENDING -> SUCCEEDED | FAILED | CANCELLED` with refund states tracked separately or as derived settlement state. Provider callbacks may arrive out of order; apply a monotonic/validated transition policy and reconcile ambiguous states with the provider.

## 4. API contract tests

At minimum test:

- QR order always returns `PENDING_CONFIRMATION` and creates no kitchen ticket before acceptance.
- A customer status token cannot read another order, the full table bill, or staff-only fields.
- Invalid/revoked QR credentials cannot submit orders.
- Duplicate `Idempotency-Key` with same body returns the original result; same key with a different body returns conflict.
- Two staff members attempting accept/reject concurrently cannot both succeed.
- Cross-tenant identifiers cannot be read or mutated.
- Client-supplied price/total/tax is ignored or rejected.
- Browser payment return without verified provider settlement leaves payment pending.
- Webhook signatures, duplicated events, invalid amounts/currencies, and late/out-of-order events are handled safely.
- Collection pagination caps, sort whitelists, and authorization are enforced.
