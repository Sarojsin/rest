# Target Data Model — Delta-Only Schema

**Rule:** every existing operational table keeps its columns and its append-only guarantees. This file defines **new tables (M1)**, **column additions (M2)**, and **conventions**. Migration SQL with step ordering and rollback lives in `17-migration-runbook.md`.

DB target: **PostgreSQL 16** (D12). All timestamps `TIMESTAMPTZ`. All IDs UUID v4 + `created_at/updated_at` unless the table is append-only (then only `created_at`).

## 1. Tenancy tables (M1)

```sql
CREATE TABLE tenants (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            TEXT NOT NULL UNIQUE,          -- URL-safe: 'blue-fork'
  legal_name      TEXT NOT NULL,
  display_name    TEXT NOT NULL,
  primary_email   CITEXT NOT NULL,
  primary_phone   TEXT,
  country_code    TEXT NOT NULL,                 -- ISO 3166-1 alpha-2
  default_currency TEXT NOT NULL,                -- ISO 4217
  default_timezone TEXT NOT NULL,                -- IANA
  status          TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','trialing','active','past_due','suspended','cancelled','expired')),
  data_region     TEXT NOT NULL DEFAULT 'default',
  is_demo         BOOLEAN NOT NULL DEFAULT FALSE,   -- demo tenant excluded from analytics/billing
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE branches (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  slug        TEXT NOT NULL,
  name        TEXT NOT NULL,
  address_line1 TEXT, address_line2 TEXT, city TEXT, region TEXT, postal_code TEXT, country_code TEXT,
  timezone    TEXT NOT NULL,
  currency_code TEXT NOT NULL,
  tax_config          JSONB NOT NULL DEFAULT '{}',
  service_charge_config JSONB NOT NULL DEFAULT '{}',
  receipt_config      JSONB NOT NULL DEFAULT '{}',
  hours_config        JSONB NOT NULL DEFAULT '{}',
  status      TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','inactive','archived')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, slug)
);

-- Upgrades existing restaurant_memberships (audit finding §2) — keep history:
CREATE TABLE memberships (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('invited','active','disabled','revoked')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, tenant_id)
);

CREATE TABLE membership_branches (
  membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
  branch_id     UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
  PRIMARY KEY (membership_id, branch_id)
);

-- Roles stay tenant-scoped; permissions catalog stays global (allowlisted in 04 §5)
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  code TEXT NOT NULL,                 -- 'owner','manager','waiter','kitchen','cashier'
  name TEXT NOT NULL,
  is_system BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, code)
);

CREATE TABLE membership_roles (
  membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (membership_id, role_id)
);
-- Decision D13: one role per membership for the pilot; per-branch role overrides deferred.
```

## 2. Platform/billing tables (M1)

```sql
CREATE TABLE plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,          -- 'trial','starter','growth','scale'
  name TEXT NOT NULL,
  description TEXT,
  monthly_price_cents BIGINT,
  annual_price_cents BIGINT,
  currency_code TEXT NOT NULL DEFAULT 'USD',
  entitlements JSONB NOT NULL DEFAULT '{}',   -- schema in 07 §2
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'trialing'
    CHECK (status IN ('trialing','active','past_due','paused','cancelled','expired')),
  current_period_start TIMESTAMPTZ NOT NULL,
  current_period_end   TIMESTAMPTZ NOT NULL,
  trial_ends_at TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
  cancelled_at TIMESTAMPTZ,
  billing_mode TEXT NOT NULL DEFAULT 'manual'      -- 'manual' (D6 MVP) | 'stripe' (Phase 6)
  ,
  gateway_provider TEXT, gateway_customer_id TEXT, gateway_subscription_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- At most one LIVE subscription per tenant; history preserved:
CREATE UNIQUE INDEX uq_subscriptions_live_per_tenant
  ON subscriptions (tenant_id)
  WHERE status IN ('trialing','active','past_due','paused');

CREATE TABLE usage_counters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  metric TEXT NOT NULL,                 -- 'orders_per_month','staff_users','branches','qr_sessions'
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  count BIGINT NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, metric, period_start)
);

CREATE TABLE platform_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
  number TEXT NOT NULL UNIQUE,
  amount_cents BIGINT NOT NULL,
  tax_cents BIGINT NOT NULL DEFAULT 0,
  currency_code TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','open','paid','void','uncollectible')),
  issued_at TIMESTAMPTZ, due_at TIMESTAMPTZ, paid_at TIMESTAMPTZ,
  gateway_invoice_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE platform_billing_events (     -- append-only
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
  invoice_id UUID REFERENCES platform_invoices(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE platform_admins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('support','billing','ops','superadmin')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE platform_audit_logs (   -- append-only
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_platform_admin_id UUID REFERENCES platform_admins(id),
  action TEXT NOT NULL,               -- 'tenant.suspend','plan.update',...
  entity_type TEXT NOT NULL,
  entity_id UUID,
  tenant_id UUID REFERENCES tenants(id),
  before_data JSONB, after_data JSONB,
  reason TEXT,                        -- mandatory for state-changing actions (08 §3)
  request_id TEXT, ip TEXT, user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3. Branch menu overrides (M1) — see `10-menu-draft-publish.md`

```sql
CREATE TABLE menu_item_branch_overrides (
  menu_item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  branch_id    UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  price_override_minor BIGINT,
  is_hidden    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (menu_item_id, branch_id)
);
-- tenant_id is derivable via branch; an RLS-era denormalized tenant_id column is added in M2/M3
-- so every table has a direct tenant discriminator (04 §4).
```

## 4. Column deltas on existing tables (M2, dual-write in M3, read-switch M4)

Every table currently carrying `restaurant_id` gains, staged:

```
Stage A: tenant_id UUID NULL REFERENCES tenants(id);  branch_id UUID NULL REFERENCES branches(id)
Stage B: SET NOT NULL (after backfill verification vs. row counts)
Stage C: reader/writer code flipped (M3 dual-write, M4 gated read switch)
Stage D (M6): DROP restaurant_id; RENAME restaurant_daily_counters → branch_daily_counters
```

Classification (locked):

| Scope | Tables |
|-------|--------|
| Tenant-only (no branch) | memberships(-derived), plans, subscriptions, usage_counters, platform_*, users, refresh_tokens, restaurant_settings (becomes `tenant_settings`) |
| Tenant + required branch | restaurant_tables→`tables`, dining_sessions, orders, order_items, bills, bill_items, payments, payment_events, kitchen_tickets, kitchen_ticket_items, service_calls, outbox_events, idempotency_keys, restaurant_daily_counters |
| Tenant-graph entity (both) | restaurant_memberships (migrated into memberships + membership_branches) |
| Menu: tenant w/ optional branch | menu_categories, menu_items, menu_option_groups, menu_options (`branch_id` NULL = tenant-wide definition) |
| Branch-scoped override | menu_item_branch_overrides (above) |
| Deferred (Phase 8) | waiter_requests (`id, tenant_id, branch_id, dining_session_id, status REQUESTED/CLAIMED/ACKNOWLEDGED, claimed_by_membership_id, created_at, sla_deadline_at`) |

Naming: keep existing table names (`tables` via rename from `restaurant_tables` happens in M6 only, to minimize churn). During M2–M4 both old and new columns coexist; writers set both, readers choose by flag.

## 5. Conventions (append to `docs/schema.md`)

1. **`tenant_id` eschewal of exceptions:** only tables in the "Tenant-only" class and the global allowlist (04 §5) may omit it. The isolation test asserts every not-allowlisted table has `tenant_id` with an index.
2. **Indexes:** every operational table gets `(tenant_id, branch_id)`;
   report-heavy tables get `(tenant_id, branch_id, created_at)`.
   Existing unique constraints keyed on restaurant_id (e.g. `uq_tables_restaurant_code`) re-key to `(branch_id, table_code)` in M4.
3. **JSONB configs** (`tax_config`, `receipt_config`, …) are *schema-validated in Pydantic*, not DB-level; constraint checks live in service code. Rationale: flexibility now, typed validation at the boundary.
4. **Composite FKs** for cross-entity same-tenant integrity (full pattern in 04 §4) added in M4, not before dual-write is stable.
5. **Append-only tables** (`audit_events`, `payment_events`, `platform_billing_events`, `stock_movements`) get no UPDATE/DELETE grants to the app role after M5; immutability enforced by grant, not convention.
6. **Soft delete:** unchanged policy (`status` + `archived_at`) — plus per-tenant erasure cascade designed in Phase 10 (retention: audit/payment events 7 years; platform audit 3 years — pending CONFIRM in 23).
7. **Suite-level invariant:** `alembic upgrade head` is idempotent and each migration has a tested `downgrade()`; CI runs `upgrade → downgrade → upgrade` on ephemeral Postgres (`18-testing-strategy.md §5`).
