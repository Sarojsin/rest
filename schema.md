# Database Schema — Restaurant Management System

PostgreSQL 15+. SQLAlchemy 2.0 + Alembic on the backend. All IDs are UUID v4
(gen_random_uuid). All money is stored as integer minor units (e.g. cents).
All timestamps are `TIMESTAMPTZ` stored in UTC. All tenant-scoped tables carry
`restaurant_id`.

This schema is the source of truth. If code and schema disagree, the schema wins
and code must be migrated.

## Conventions

- Primary key: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Foreign keys: `<entity>_id`
- Tenant scoping: every operational row has `restaurant_id UUID NOT NULL
  REFERENCES restaurants(id) ON DELETE RESTRICT`
- Soft delete only for user-facing mutable entities (menu items, tables,
  users). Financial/operational rows (orders, payments, stock movements) are
  **never** hard-deleted and **never** soft-deleted — use status transitions.
- Audit columns: `created_at`, `updated_at`. Add `created_by_user_id`,
  `updated_by_user_id` on operational tables where attribution matters.
- Enums: use PostgreSQL `ENUM` types or `TEXT` + `CHECK` constraints. Prefer
  `TEXT + CHECK` so Alembic migrations stay simple.
- JSONB only for flexible, low-query config (tax rules, gateway payloads,
  receipt data). Never store queryable business data in JSONB.
- Indexes: every FK column is indexed. Add indexes listed at bottom.
- Naming: `snake_case` everywhere, tables plural.

---

## Enum values (TEXT + CHECK)

| Enum | Values |
|---|---|
| `user_status` | `invited`, `active`, `disabled` |
| `role_code` | `owner`, `manager`, `cashier`, `waiter`, `kitchen` |
| `table_status` | `available`, `occupied`, `needs_cleaning`, `reserved` |
| `order_channel` | `waiter`, `qr`, `manager`, `system` |
| `order_status` | `draft`, `pending_confirmation`, `accepted`, `rejected`, `cancelled`, `completed` |
| `order_item_status` | `pending`, `preparing`, `ready`, `served`, `cancelled` |
| `bill_status` | `open`, `settled`, `voided` |
| `payment_method` | `cash`, `card_terminal`, `online_gateway` |
| `payment_status` | `pending`, `succeeded`, `failed`, `cancelled`, `refunded`, `partially_refunded` |
| `payment_event_type` | `created`, `authorized`, `captured`, `failed`, `cancelled`, `refunded`, `webhook_received`, `reconciled` |
| `stock_movement_type` | `purchase`, `usage`, `waste`, `adjustment`, `return`, `count` |
| `kitchen_ticket_status` | `new`, `preparing`, `ready`, `served`, `cancelled` |
| `dining_session_status` | `open`, `billing`, `closed` |

---

## Domain 1 — Tenancy & Identity

### restaurants
```sql
CREATE TABLE restaurants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  timezone TEXT NOT NULL DEFAULT 'UTC',           -- IANA tz
  currency_code TEXT NOT NULL DEFAULT 'USD',      -- ISO 4217
  locale TEXT NOT NULL DEFAULT 'en',
  tax_config JSONB NOT NULL DEFAULT '{}'::jsonb,  -- { mode, rules[] }
  service_charge_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  receipt_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','inactive','suspended')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

users
Staff accounts. Customer QR users are not users in this table.

sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  email CITEXT,                       -- required for managers/owners
  phone TEXT,
  full_name TEXT NOT NULL,
  password_hash TEXT,                 -- argon2id; required if no pin
  pin_hash TEXT,                      -- argon2id; optional for fast login
  status TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('invited','active','disabled')),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, email)
);
CREATE INDEX users_restaurant_id_idx ON users(restaurant_id);
roles
System roles are seeded per restaurant at provisioning.

sql
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
  code TEXT NOT NULL
    CHECK (code IN ('owner','manager','cashier','waiter','kitchen')),
  name TEXT NOT NULL,
  is_system BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, code)
);
permissions & role_permissions
sql
CREATE TABLE permissions (
  code TEXT PRIMARY KEY,              -- e.g. 'order.accept_qr', 'bill.refund'
  description TEXT NOT NULL
);

CREATE TABLE role_permissions (
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_code TEXT NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_code)
);
user_roles
sql
CREATE TABLE user_roles (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);
refresh_tokens
Rotating refresh tokens. Access tokens are stateless JWTs.

sql
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,    -- sha256 of the raw token
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  replaced_by_id UUID REFERENCES refresh_tokens(id),
  user_agent TEXT,
  ip TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX refresh_tokens_user_id_idx ON refresh_tokens(user_id);
Domain 2 — Tables, QR, Dining Sessions
tables
sql
CREATE TABLE tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  table_number TEXT NOT NULL,          -- human-readable, e.g. "T1"
  name TEXT,
  capacity INT CHECK (capacity > 0),
  zone TEXT,
  status TEXT NOT NULL DEFAULT 'available'
    CHECK (status IN ('available','occupied','needs_cleaning','reserved')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  qr_token TEXT NOT NULL UNIQUE,       -- opaque random, regenerated on rotation
  qr_version INT NOT NULL DEFAULT 1,
  qr_rotated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, table_number)
);
CREATE INDEX tables_restaurant_status_idx ON tables(restaurant_id, status);
dining_sessions
One per table visit. Bills attach to a session, not a single order.

sql
CREATE TABLE dining_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  table_id UUID NOT NULL REFERENCES tables(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','billing','closed')),
  opened_by_user_id UUID REFERENCES users(id),
  closed_by_user_id UUID REFERENCES users(id),
  opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  guest_count INT CHECK (guest_count >= 0),
  notes TEXT
);
CREATE INDEX dining_sessions_table_open_idx
  ON dining_sessions(table_id) WHERE status <> 'closed';
CREATE INDEX dining_sessions_restaurant_idx ON dining_sessions(restaurant_id);
Domain 3 — Menu
menu_categories
sql
CREATE TABLE menu_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  description TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
menu_items
sql
CREATE TABLE menu_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  category_id UUID NOT NULL REFERENCES menu_categories(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  description TEXT,
  image_url TEXT,
  price_cents BIGINT NOT NULL CHECK (price_cents >= 0),
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT NOT NULL DEFAULT 0,
  station TEXT,                        -- optional: 'kitchen'|'bar'|'cold'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX menu_items_restaurant_active_idx
  ON menu_items(restaurant_id, is_active, is_available);
CREATE INDEX menu_items_category_idx ON menu_items(category_id);
menu_item_options & menu_option_values
sql
CREATE TABLE menu_item_options (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  menu_item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  name TEXT NOT NULL,                  -- e.g. "Size", "Extras"
  selection_type TEXT NOT NULL
    CHECK (selection_type IN ('single','multiple')),
  is_required BOOLEAN NOT NULL DEFAULT FALSE,
  min_selections INT NOT NULL DEFAULT 0 CHECK (min_selections >= 0),
  max_selections INT NOT NULL DEFAULT 1 CHECK (max_selections >= 1),
  sort_order INT NOT NULL DEFAULT 0,
  CONSTRAINT min_le_max CHECK (min_selections <= max_selections)
);

CREATE TABLE menu_option_values (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  option_id UUID NOT NULL REFERENCES menu_item_options(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  price_delta_cents BIGINT NOT NULL DEFAULT 0,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT NOT NULL DEFAULT 0
);
Domain 4 — Orders & Kitchen
orders
Orders are the operational unit. QR submissions land here as
pending_confirmation and only become actionable after staff acceptance.

sql
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  dining_session_id UUID NOT NULL REFERENCES dining_sessions(id) ON DELETE RESTRICT,
  table_id UUID NOT NULL REFERENCES tables(id) ON DELETE RESTRICT,
  order_number TEXT NOT NULL,          -- e.g. "2026-10-24-T1-003"
  channel TEXT NOT NULL
    CHECK (channel IN ('waiter','qr','manager','system')),
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','pending_confirmation','accepted',
                      'rejected','cancelled','completed')),
  customer_note TEXT,
  subtotal_cents BIGINT NOT NULL DEFAULT 0,
  submitted_at TIMESTAMPTZ,
  accepted_at TIMESTAMPTZ,
  accepted_by_user_id UUID REFERENCES users(id),
  rejected_at TIMESTAMPTZ,
  rejected_by_user_id UUID REFERENCES users(id),
  rejection_reason TEXT,
  cancelled_at TIMESTAMPTZ,
  cancelled_by_user_id UUID REFERENCES users(id),
  cancellation_reason TEXT,
  idempotency_key TEXT,                -- client-provided, see note below
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, order_number),
  UNIQUE (restaurant_id, idempotency_key)
);
CREATE INDEX orders_session_idx ON orders(dining_session_id);
CREATE INDEX orders_table_status_idx ON orders(table_id, status);
CREATE INDEX orders_restaurant_pending_idx
  ON orders(restaurant_id, submitted_at)
  WHERE status = 'pending_confirmation';
order_items
Snapshot name and unit price so history is stable if the menu changes.

sql
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  menu_item_id UUID REFERENCES menu_items(id) ON DELETE SET NULL,
  name_snapshot TEXT NOT NULL,
  unit_price_cents_snapshot BIGINT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','preparing','ready','served','cancelled')),
  station TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX order_items_order_idx ON order_items(order_id);
CREATE INDEX order_items_kitchen_queue_idx
  ON order_items(restaurant_id, status, created_at)
  WHERE status IN ('pending','preparing');
order_item_options
sql
CREATE TABLE order_item_options (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
  option_value_id UUID REFERENCES menu_option_values(id) ON DELETE SET NULL,
  name_snapshot TEXT NOT NULL,
  price_delta_cents_snapshot BIGINT NOT NULL DEFAULT 0
);
kitchen_tickets
One per station per accepted order. Multiple tickets per order allowed.

sql
CREATE TABLE kitchen_tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
  station TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new','preparing','ready','served','cancelled')),
  started_at TIMESTAMPTZ,
  ready_at TIMESTAMPTZ,
  served_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX kitchen_tickets_status_idx
  ON kitchen_tickets(restaurant_id, status, created_at);
Domain 5 — Bills & Payments
bills
One per dining session. May aggregate multiple orders.

sql
CREATE TABLE bills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  dining_session_id UUID NOT NULL REFERENCES dining_sessions(id) ON DELETE RESTRICT,
  table_id UUID NOT NULL REFERENCES tables(id) ON DELETE RESTRICT,
  bill_number TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','settled','voided')),
  subtotal_cents BIGINT NOT NULL DEFAULT 0,
  discount_cents BIGINT NOT NULL DEFAULT 0,
  service_charge_cents BIGINT NOT NULL DEFAULT 0,
  tax_cents BIGINT NOT NULL DEFAULT 0,
  total_cents BIGINT NOT NULL DEFAULT 0,
  paid_cents BIGINT NOT NULL DEFAULT 0,
  tax_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
  closed_at TIMESTAMPTZ,
  closed_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, bill_number)
);
CREATE INDEX bills_session_idx ON bills(dining_session_id);
CREATE INDEX bills_open_idx ON bills(restaurant_id) WHERE status = 'open';
bill_items
Snapshot of what was billed. A bill line may group order items or reference
them 1:1 — pick 1:1 for traceability.

sql
CREATE TABLE bill_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
  order_item_id UUID REFERENCES order_items(id) ON DELETE SET NULL,
  name_snapshot TEXT NOT NULL,
  unit_price_cents_snapshot BIGINT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  line_total_cents BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','voided'))
);
payments
A bill can have multiple payments (split, partial, retry).

sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE RESTRICT,
  method TEXT NOT NULL
    CHECK (method IN ('cash','card_terminal','online_gateway')),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','succeeded','failed','cancelled',
                      'refunded','partially_refunded')),
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  refunded_cents BIGINT NOT NULL DEFAULT 0,
  gateway_provider TEXT,
  gateway_transaction_id TEXT,
  gateway_reference TEXT,
  idempotency_key TEXT,
  created_by_user_id UUID REFERENCES users(id),
  confirmed_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (gateway_provider, gateway_transaction_id),
  UNIQUE (restaurant_id, idempotency_key)
);
CREATE INDEX payments_bill_idx ON payments(bill_id);
CREATE INDEX payments_pending_idx ON payments(restaurant_id)
  WHERE status = 'pending';
payment_events
Append-only. Every gateway webhook, state change, and reconciliation attempt.

sql
CREATE TABLE payment_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL
    CHECK (event_type IN ('created','authorized','captured','failed',
                          'cancelled','refunded','webhook_received',
                          'reconciled')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX payment_events_payment_idx ON payment_events(payment_id);
Domain 6 — Inventory
ingredients (stock items)
sql
CREATE TABLE ingredients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  unit TEXT NOT NULL,                  -- 'g','ml','pcs','kg','L'
  current_quantity NUMERIC(14,3) NOT NULL DEFAULT 0,
  reorder_level NUMERIC(14,3),
  unit_cost_cents BIGINT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (restaurant_id, name)
);
suppliers & purchases & purchase_items
sql
CREATE TABLE suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  contact_name TEXT,
  phone TEXT,
  email TEXT,
  notes TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
  invoice_number TEXT,
  total_cents BIGINT NOT NULL DEFAULT 0,
  purchased_at TIMESTAMPTZ NOT NULL,
  recorded_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE purchase_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
  ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  quantity NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
  unit_cost_cents BIGINT NOT NULL
);
stock_movements
Append-only ledger. Never update ingredients.current_quantity without a
matching stock movement.

sql
CREATE TABLE stock_movements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  movement_type TEXT NOT NULL
    CHECK (movement_type IN ('purchase','usage','waste','adjustment',
                             'return','count')),
  quantity_delta NUMERIC(14,3) NOT NULL,
  reference_type TEXT,                 -- 'order'|'purchase'|'count'|'manual'
  reference_id UUID,
  notes TEXT,
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX stock_movements_ingredient_idx
  ON stock_movements(ingredient_id, created_at);
recipes
sql
CREATE TABLE recipes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  menu_item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  quantity NUMERIC(14,3) NOT NULL CHECK (quantity > 0),
  UNIQUE (menu_item_id, ingredient_id)
);
Domain 7 — Cross-cutting
audit_logs
Append-only. Written by the backend on every sensitive action.

sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  actor_user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,                -- 'order.accept', 'payment.refund', ...
  entity_type TEXT NOT NULL,
  entity_id UUID,
  before_data JSONB,
  after_data JSONB,
  request_id TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_logs_entity_idx ON audit_logs(entity_type, entity_id);
CREATE INDEX audit_logs_restaurant_time_idx
  ON audit_logs(restaurant_id, created_at DESC);
idempotency_keys
Used by order submission, payment creation, and any POST that must be safe
to retry. Server stores first response and replays it on duplicates.

sql
CREATE TABLE idempotency_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL,                 -- 'order.submit'|'payment.create'
  key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response_status INT,
  response_body JSONB,
  locked_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE (restaurant_id, scope, key)
);
restaurant_daily_counters
Used to generate human-readable order/bill numbers without races.

sql
CREATE TABLE restaurant_daily_counters (
  restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
  business_day DATE NOT NULL,
  order_seq INT NOT NULL DEFAULT 0,
  bill_seq INT NOT NULL DEFAULT 0,
  PRIMARY KEY (restaurant_id, business_day)
);
Integrity rules (must be enforced in the backend even if not in SQL)
orders.restaurant_id must match orders.dining_session_id's restaurant.

orders.table_id must match the session's table.

A QR order (channel = 'qr') can only transition to accepted by a user
with permission order.accept_qr.

A bill can only be marked settled when paid_cents >= total_cents and
every payment row is succeeded or refunded (net).

order_items.status is the kitchen source of truth; kitchen_tickets
aggregate them for display.

order_items and bill_items snapshots must never be mutated after the
order becomes accepted. Use new rows / explicit void + re-add.

Every stock_movements write must also update ingredients.current_quantity
in the same transaction.

Direct UPDATE on audit_logs, payment_events, stock_movements is
forbidden for application roles — append only.

Suggested indexes (applied above, listed for audit)
orders(restaurant_id, status, submitted_at DESC)

order_items(restaurant_id, status, created_at)

payments(restaurant_id, status)

dining_sessions(table_id) WHERE status <> 'closed'

audit_logs(restaurant_id, created_at DESC)

Future (out of scope for pilot but schema-friendly)
restaurant_id on every table already supports RLS and future multi-tenant
isolation. Do not enable RLS until the hosted multi-tenant stage — keep
application-level scoping for the pilot.

Split bills, multi-language menus, reservations — add new tables, do not
overload orders.

text

---

## `rules/shared.md`

```markdown
# Shared Conventions — All Clients and Backend

These rules apply to backend, web frontend, and mobile app. If a conflict
arises, this file wins over the per-app rules.

## Money

- All money is **integer minor units** (`*_cents`) in API requests and
  responses. Never floats. Never strings with currency symbols.
- The backend is the **only** authority on price totals. Clients may display
  optimistic estimates but must always reconcile with the server response.

## Identifiers

- All public IDs are UUIDv4 strings.
- No sequential database IDs are exposed in APIs.

## Time

- All timestamps in APIs are ISO-8601 with `Z` (UTC).
- Business day (`business_day`) is computed on the **restaurant timezone** by
  the backend. Clients do not compute business day.

## Error envelope

Every non-2xx API response uses this shape:

```json
{
  "error": {
    "code": "ORDER_ITEM_UNAVAILABLE",
    "message": "Cappuccino is currently unavailable.",
    "details": { "menu_item_id": "…" },
    "request_id": "req_01H…"
  }
}
code is a stable SCREAMING_SNAKE_CASE identifier.

message is safe to show to end users.

details is optional structured context.

request_id matches the server log entry.

Clients must switch on code, never on message.

Idempotency
Any POST that creates a durable resource (order submit, payment create) must
accept an Idempotency-Key header.

Clients must generate a new UUID per user-intent (not per retry) and reuse
the same key on retries of that intent.

Server must return the stored first response for the same key with the same
request body hash; different body → 409 IDEMPOTENCY_KEY_CONFLICT.

Auth
Access token: short-lived JWT (15 min), sent as Authorization: Bearer ….

Refresh token: rotating, stored in HttpOnly cookie (web) or secure
keychain/keystore (mobile).

The customer QR website does not use user auth. It uses the table QR
token in the URL path and short-lived signed table session tokens issued by
the backend.

Real-time
Server pushes updates via WebSocket (staff) and Server-Sent Events (customer
status). Clients must also poll as a fallback — never trust real-time alone.

Logging
Every request has a request_id returned in the X-Request-Id header and in
error responses. Clients may log it; users may quote it to support.

Clients must not log auth tokens, PINs, or card data.

text

---

## `rules/database.md`

```markdown
# PostgreSQL Rules

You are the schema owner for a FastAPI + SQLAlchemy 2.0 backend. Follow these
rules absolutely. If a change conflicts, propose a migration first, do not
sneak schema changes into application code.

## Migrations

1. Every schema change goes through Alembic (`alembic revision --autogenerate`).
2. **Never** edit an applied migration. Fix it forward with a new migration.
3. **Never** drop a column, table, or enum value in a single migration. Do it
   in three stages: (a) stop writing, (b) deploy readers-tolerant code,
   (c) drop in a later release.
4. **Never** rename a column in place. Add new, backfill, dual-write, cutover,
   drop old.
5. Every migration must have a working `downgrade()` unless explicitly marked
   `reversible=False` with a written justification.
6. Migrations that lock large tables must be online-safe:
   - Use `CREATE INDEX CONCURRENTLY`.
   - Use `ALTER TABLE … ADD COLUMN … NULL` and backfill in batches.
   - Never `ALTER COLUMN TYPE` on a hot table without a migration plan.

## Data types

- IDs: `UUID DEFAULT gen_random_uuid()`.
- Money: `BIGINT` in minor units (cents). Never `FLOAT`/`NUMERIC` for money.
- Quantities: `NUMERIC(14,3)` for inventory. Never float.
- Timestamps: `TIMESTAMPTZ NOT NULL DEFAULT now()`. Never `timestamp without
  time zone`.
- Booleans: `BOOLEAN NOT NULL DEFAULT FALSE` when the concept is default-false.
- Enums: `TEXT` + `CHECK`. No Postgres `ENUM` type — harder to migrate.
- JSONB: only for config and payloads. Never for queryable business data.

## Naming

- Tables: `snake_case`, plural (`order_items`).
- Columns: `snake_case`, singular (`created_at`).
- FK: `<entity>_id`.
- Indexes: `<table>_<columns>_idx`.
- Constraints: `<table>_<rule>_check`, `<table>_<fk>_fkey`.
- Unique indexes: `<table>_<columns>_key`.

## Required columns on operational tables

- `id`, `restaurant_id`, `created_at`, `updated_at`.
- `created_by_user_id` / `updated_by_user_id` on tables where attribution
  matters (orders, bills, payments, stock movements, audit).
- Snapshot columns (`*_snapshot`) are never updated after a resource moves to a
  final-ish state.

## Multi-tenancy

- Every business table carries `restaurant_id`.
- All queries in application code filter by `restaurant_id` derived from the
  authenticated staff user or from the QR table token. There is no "system
  user" that bypasses this.
- Do not enable row-level security yet. Track it as future work.
- Foreign keys between tenant-scoped rows must be validated in code to belong
  to the same `restaurant_id`; FKs alone do not enforce this. Add a DB
  constraint or trigger when convenient.

## Transactions

- Wrap multi-write operations in a single transaction. Examples:
  - Accept order → create kitchen tickets → write audit.
  - Create payment → write payment event → update bill paid amount → audit.
  - Stock movement → update `ingredients.current_quantity` → audit.
- Use `SELECT … FOR UPDATE` when two writers can race on the same row
  (e.g. `bills.total_cents`, `ingredients.current_quantity`,
  `restaurant_daily_counters`).
- Keep transactions short. Never hold one open across a network call to the
  payment gateway. Use an outbox or the payment_events table + worker.

## Performance

- Every FK column is indexed.
- Add indexes when a query pattern is known and hot. Do not pre-add dozens of
  speculative indexes.
- Use partial indexes for "open"/"pending" states (already in `schema.md`).
- EXPLAIN ANALYZE any query touching > 10k rows before shipping.

## Append-only tables

These tables are **append-only** for the application role:

- `audit_logs`
- `payment_events`
- `stock_movements`

Enforce with a role that only has `INSERT`/`SELECT`. Application code must
never `UPDATE` or `DELETE` these rows. Corrections are new rows.

## Backups

- Daily full backup + WAL archiving in production.
- Restore drill at least once before pilot go-live and once per quarter.

## Testing

- Every migration has a test that runs `upgrade head` then `downgrade -1` then
  `upgrade head` against a throwaway DB.
- Integration tests run against a real Postgres container (not SQLite).