Multi-Tenant SaaS Architecture Plan
Status: Planning only. No code changes yet. Waiting for your approval.

Caveat up front: I have not inspected the actual repository. This document is built from (a) the plan we've been evolving in this conversation, (b) your brief above, and (c) standard patterns for evolving a single-tenant operational app into multi-tenant SaaS. Where I make an assumption about the existing codebase, I flag it with ASSUMPTION:. Any of those that are wrong will change the plan; call them out before we approve.

1. Current architecture assessment
1.1 What I'm assuming exists today
ASSUMPTION: The current codebase matches the plan we built earlier in this conversation:

Single tenant, single restaurant, or at best a single restaurant per deployment.

Tables carry restaurant_id (already plural-friendly), but there is exactly one restaurant row.

Auth issues JWTs bound to one restaurant.

All API routes resolve tenant implicitly from the authenticated user's restaurant_id.

Customer QR flow resolves table → restaurant.

No concept of a "tenant" (business) versus a "branch" (location).

No subscription, plan, entitlement, or super-admin surface.

Payments are for customer bills only; there is no platform billing.

One React web app (customer + staff), one Expo app (staff), one FastAPI service, one Postgres, Redis optional.

1.2 What will need to change conceptually
The key insight: restaurant today means two different things that must be split:

Today	Tomorrow
restaurant = a business + a physical location combined	tenant = a restaurant business (billing, plans, users)
branch = a physical location (tables, kitchen, menu overrides)
restaurant may still exist as an alias or be removed
If your current restaurant row holds both identity (name, tax settings, subscription) and operations (tables, menu), that record needs to split into tenants + branches + restaurant_settings (or similar), and every operational table needs a branch_id in addition to tenant_id.

1.3 Real architectural problems in the current model
Problem	Why it blocks SaaS	Fix complexity
restaurant_id semantics are overloaded	Cannot represent multi-branch tenants	High — touches every table
Tenant resolved from user, not from request + verified	Fine for one tenant; unsafe when a user can belong to many	Medium
No super-admin realm	Impossible to provision/suspend a tenant	Medium
Menu is per-restaurant, no branch overrides	Branch 2 can't have different prices	Medium
Auth JWT binds one restaurant	Cannot switch between tenants without re-login	Medium
No entitlements layer	Enforcing plan limits (branches, users, orders/month) has no home	Medium
No platform billing	No revenue mechanism	High (new subsystem)
No cross-tenant tests	Regressions will leak data	Medium (but must exist)
Audit log scoped only to restaurant	Super-admin actions invisible	Low
QR URL embeds table token only	Fine, but table must be traceable to tenant AND branch	Low
Customer checkout uses restaurant-level settings	Branch overrides need to be honored	Medium
Payment webhooks resolve tenant from payload	Must verify against DB records, not trust payload	Medium
1.4 What we should preserve
The operational schema for orders, kitchen, bills, payments, inventory — this is correct and should survive.

The service/repository/route pattern from rules/backend.md.

The design system and page inventory from build_plan.md.

The append-only tables (audit_logs, payment_events, stock_movements).

The QR → pending_confirmation → accept workflow.

The multi-tenant change is a widening, not a rewrite. That is the single most important discipline in this migration.

2. Multi-tenant architecture proposal
2.1 Tenancy model
Three-level domain:

text
Tenant (restaurant business / company)
  └── Branch (physical location)
        └── Dining session (a table visit)
              └── Order / Bill / Payment
Plus one more axis:

text
Tenant (business)
  └── User membership (a user may belong to multiple tenants)
        └── Role(s) per tenant (or per branch)
2.2 Shared-schema with tenant_id + branch_id
Chosen model: shared database, shared schema, discriminator columns + RLS.

Justification:

Operationally simplest, cheapest for a commercial SaaS at pilot-to-early scale.

Migrations stay single-track (no tenant_x schemas to run them against).

Cross-tenant reporting for the platform operator is easy.

RLS provides defense-in-depth without requiring separate schemas.

Row counts: a pilot restaurant generates thousands of rows per day. Even at 200 tenants × 5 branches × 1000 orders/day = 1M orders/day, still fine for a single Postgres with proper indexing and partitioning on orders/order_items by month.

Alternatives considered:

Model	Pros	Cons	Verdict
Schema-per-tenant	Strong isolation, simple mental model, easy per-tenant backup	Migration fan-out, connection pool explosion, hard cross-tenant analytics, painful backup/restore per tenant	Reject
Database-per-tenant	Strongest isolation	Very high operational cost; cross-tenant features impossible	Reject
Shared schema + RLS (chosen)	Simple migrations, one connection pool, strong isolation with RLS, cheap	Requires discipline (every query scoped), RLS must be enabled per table	Adopt
2.3 RLS evaluation (explicit, as requested)
Recommendation: enable RLS in Stage 4, not Stage 1.

Why not in Stage 1:

RLS is a wall, not a plan. It catches leaks after the fact; it does not fix the design.

Application-layer scoping must be correct first — RLS will hide bugs during development that should fail loudly in tests.

RLS interacts badly with background workers unless you set the session variable carefully.

It adds significant operational complexity for the first few tenants.

Why eventually yes:

Defense-in-depth: an un-scoped query in application code will return zero rows instead of another tenant's data.

Compliance posture for a commercial SaaS is much stronger with RLS.

Design (to be enabled in Stage 4):

sql
-- Every tenant-scoped table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY orders_tenant_isolation ON orders
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
Application connects with a role that is not the table owner (owners bypass RLS unless FORCE ROW LEVEL SECURITY).

Every request sets SET LOCAL app.current_tenant_id = '<uuid>' at the start of the transaction.

Background workers set the session variable per tenant they process.

Super-admin routes connect with a role that bypasses RLS (explicit, logged, minimal surface).

RLS is tested by a dedicated "RLS isolation" test suite that runs with RLS on, using two tenants and asserting every read returns only own rows.

Do not enable RLS before the application layer is reliably tenant-scoped and the cross-tenant test suite is green. RLS hides bugs; tests must catch them.

2.4 Tenant resolution at the edge
Every request resolves tenant from one source of truth:

Request type	Tenant source
Staff API (authenticated)	current_user.membership.current_tenant_id (from JWT claim, verified against DB) + membership lookup
Customer QR	Table token → branch → tenant, resolved server-side
Webhook	Payment/intent record in DB, never from payload
Super-admin API	Explicit X-Platform-Auth header (separate realm), acting-on-tenant parameter validated against tenants table
Public health / metadata	No tenant
Never accept tenant_id from URL or body on tenant-scoped resources. If a URL carries a tenant slug (e.g. /t/blue-fork), it must match the authenticated user's accessible tenants.

2.5 Request lifecycle
text
Request → auth (JWT or QR token or platform key)
       → resolve tenant_id + branch_id from trusted source
       → set request context (tenant_id, branch_id, user, permissions, request_id)
       → BEGIN transaction; SET LOCAL app.current_tenant_id
       → service layer (always uses ctx.tenant_id / ctx.branch_id)
       → COMMIT; emit side effects (WS, audit)
The context object is injected via FastAPI dependency and is the only sanctioned way for services to read tenant/branch.

3. Database schema and migration strategy
3.1 Target schema (deltas only; full operational schema preserved)
3.1.1 New tables
sql
-- Tenants (restaurant businesses)
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,            -- URL-safe, e.g. "blue-fork"
  legal_name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  primary_email CITEXT NOT NULL,
  primary_phone TEXT,
  country_code TEXT NOT NULL,           -- ISO 3166-1 alpha-2
  default_currency TEXT NOT NULL,       -- ISO 4217
  default_timezone TEXT NOT NULL,       -- IANA
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','trialing','active','past_due',
                      'suspended','cancelled')),
  data_region TEXT NOT NULL DEFAULT 'default',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Branches (physical locations)
CREATE TABLE branches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  region TEXT,
  postal_code TEXT,
  country_code TEXT,
  timezone TEXT NOT NULL,
  currency_code TEXT NOT NULL,
  tax_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  service_charge_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  receipt_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','inactive','archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, slug)
);

-- Membership: a user can belong to many tenants
CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('invited','active','disabled','revoked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, tenant_id)
);

-- Branch-scoped role assignment
CREATE TABLE membership_branches (
  membership_id UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
  branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
  PRIMARY KEY (membership_id, branch_id)
);

-- Roles are now tenant-scoped (seeded per tenant)
-- permissions table stays global
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  code TEXT NOT NULL,   -- 'owner','manager','cashier','waiter','kitchen'
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

-- Plans
CREATE TABLE plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,            -- 'starter','growth','scale'
  name TEXT NOT NULL,
  description TEXT,
  monthly_price_cents BIGINT,
  annual_price_cents BIGINT,
  currency_code TEXT NOT NULL DEFAULT 'USD',
  entitlements JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- e.g. {"branches": 1, "staff_users": 10, "orders_per_month": 5000,
  --       "online_payments": false, "inventory": false}
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Subscriptions
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'trialing'
    CHECK (status IN ('trialing','active','past_due','paused',
                      'cancelled','expired')),
  current_period_start TIMESTAMPTZ NOT NULL,
  current_period_end TIMESTAMPTZ NOT NULL,
  trial_ends_at TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
  cancelled_at TIMESTAMPTZ,
  gateway_provider TEXT,                -- e.g. 'stripe'
  gateway_customer_id TEXT,
  gateway_subscription_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id)                    -- one active subscription per tenant in pilot
);

-- Usage counters (Redis is source of truth for real-time; this is the ledger)
CREATE TABLE usage_counters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  metric TEXT NOT NULL,                 -- 'orders_per_month','staff_users', 'branches'
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  count BIGINT NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, metric, period_start)
);

-- Platform invoices
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
  issued_at TIMESTAMPTZ,
  due_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  gateway_invoice_id TEXT,
  pdf_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Platform billing events (append-only, mirror of payment_events)
CREATE TABLE platform_billing_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
  invoice_id UUID REFERENCES platform_invoices(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Super admin accounts (separate realm; not memberships)
CREATE TABLE platform_admins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('support','billing','ops','superadmin')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','disabled')),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE platform_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_platform_admin_id UUID REFERENCES platform_admins(id),
  action TEXT NOT NULL,                 -- 'tenant.suspend','plan.update'
  entity_type TEXT NOT NULL,
  entity_id UUID,
  tenant_id UUID REFERENCES tenants(id),-- when acting on a tenant
  before_data JSONB,
  after_data JSONB,
  request_id TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
3.1.2 Column additions to existing tables
For every operational table currently carrying restaurant_id:

sql
-- Stage A (nullable, deploy here)
ALTER TABLE orders ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE orders ADD COLUMN branch_id UUID REFERENCES branches(id);

-- ... backfill ...
-- Stage B (NOT NULL, deploy here)
ALTER TABLE orders ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE orders ALTER COLUMN branch_id SET NOT NULL;

-- Stage C (drop old column, later release)
ALTER TABLE orders DROP COLUMN restaurant_id;
Tables affected (from schema.md):

users (split: identity global, membership per tenant), roles, permissions (stays global), user_roles → membership_roles, tables, dining_sessions, menu_categories, menu_items, menu_item_options, menu_option_values, orders, order_items, order_item_options, kitchen_tickets, bills, bill_items, payments, payment_events, ingredients, suppliers, purchases, purchase_items, stock_movements, recipes, audit_logs, idempotency_keys, restaurant_daily_counters → branch_daily_counters.

Menu-level split:

menu_categories, menu_items, menu_item_options, menu_option_values — replace restaurant_id with tenant_id. Add optional branch_id (nullable = tenant-wide; set = branch-specific override).

Query resolution: branch_item = branch_override ?? tenant_item.

Availability is almost always per-branch; availability belongs on a new menu_item_branch_availability table, not on menu_items.

New menu_item_branch_availability:

sql
CREATE TABLE menu_item_branch_availability (
  menu_item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  price_override_cents BIGINT,
  PRIMARY KEY (menu_item_id, branch_id)
);
tables, dining_sessions, kitchen_tickets, bills, payments, orders, order_items — all get both tenant_id and branch_id.

restaurant_daily_counters becomes branch_daily_counters (order/bill numbers are per branch, not per tenant).

3.2 Migration strategy
Six-stage rolling migration. No stage breaks existing functionality.

Stage	Change	Rollback-safe?
M1	Add tenants, branches, memberships, membership_roles, plans, subscriptions, usage_counters, platform_admins, platform_audit_logs, menu_item_branch_availability. No existing table touched.	Yes — new tables only
M2	For each existing tenant-scoped table: ADD COLUMN tenant_id UUID NULL, ADD COLUMN branch_id UUID NULL. Backfill from current restaurant_id → one tenant + one branch. Add indexes on (tenant_id, branch_id). Existing code keeps working (uses restaurant_id).	Yes
M3	Dual-write: application writes both restaurant_id and tenant_id/branch_id on every insert/update. Reads still prefer restaurant_id. Deploy.	Yes — old code still reads restaurant_id
M4	Switch reads to tenant_id/branch_id. Keep dual-write. Add NOT NULL constraints after backfill verification. RLS policies created but not enabled.	Yes — flip a feature flag to revert reads
M5	Enable RLS on operational tables (Stage 4 of the rollout — see §10). Remove restaurant_id column references from code.	Mostly — RLS off is a config change
M6	Drop restaurant_id columns and the restaurants table. Rename restaurant_daily_counters → branch_daily_counters.	No — plan this for a later release with a full backup
Backfill logic (M2):

sql
INSERT INTO tenants (id, slug, legal_name, display_name, ...)
  SELECT gen_random_uuid(), <slug-from-existing>, ... FROM restaurants;

INSERT INTO branches (tenant_id, slug, name, ...)
  SELECT t.id, 'main', r.name, ... FROM restaurants r JOIN tenants t ON ...;

UPDATE orders o SET tenant_id = b.tenant_id, branch_id = b.id
  FROM branches b WHERE b.<old_restaurant_id> = o.restaurant_id;
For the pilot, this is trivial (one restaurant). For existing customers with multiple deployments, run this per deployment.

Non-negotiables for this migration:

Every migration has a tested downgrade.

Every migration that touches a large table uses CONCURRENTLY indexes or batched backfill.

No stage requires two simultaneous deployments.

Feature flag USE_TENANT_COLUMNS gates read path in M3–M4.

Cross-tenant isolation test suite runs in CI from M2 onward.

3.3 Partitioning (deferred)
At >10M orders/month, consider partitioning orders, order_items, payments, payment_events, audit_logs by month. Not needed for pilot-to-first-100-tenants. Mentioning it now so schema.md reserves composite primary keys (id, created_at) in a later migration if partitioning is adopted. Do not partition in this migration.

4. Authentication and authorization design
4.1 Three auth realms
Realm	Who	Token	Storage	Surface
Staff	Waiter, kitchen, cashier, manager, owner	JWT access (15m) + rotating refresh (7d)	Web: HttpOnly cookie. Mobile: keychain	/api/v1/*
Customer	QR diners	Short-lived session token (30m) bound to table + dining session	Cookie (web)	/api/v1/qr/*
Platform admin	SaaS super admin	JWT access (30m) + rotating refresh (12h)	HttpOnly cookie on admin subdomain	/api/platform/*
Customer and staff share no auth code paths. Platform admin is a separate FastAPI router, separate secret, separate middleware. A staff JWT must be unusable against /api/platform/* and vice versa.

4.2 Multi-tenant JWT
Access token claims:

json
{
  "sub": "<user_id>",
  "realm": "staff",
  "tenant_id": "<current_tenant_id>",
  "membership_id": "<membership_id>",
  "branch_ids": ["<branch>", "..."],
  "perms": ["order.accept_qr", "..."],
  "pv": 3,
  "iat": ..., "exp": ..., "jti": "<uuid>"
}
tenant_id is the active tenant (switcher changes it via a token exchange).

branch_ids restricts what the user can access inside the tenant; a user can be tenant-wide (all branches) or branch-scoped.

perms is a cached snapshot; pv is permission version. On any role/permission change, pv is bumped for the user — every request validates pv against the DB, so stale tokens lose access immediately.

jti is used for revocation (logout, forced rotation).

Permission source of truth is the DB. The JWT's perms is an optimization; every request re-resolves effective permissions from membership_roles + role_permissions, then compares pv. If pv mismatch → 401 → client must refresh.

4.3 Tenant switching
Flow:

User logs in. If they belong to one tenant → direct to that tenant. If many → show a tenant picker after login.

Picker calls POST /auth/switch-tenant { tenant_id } → backend verifies membership → issues new access + refresh tokens for that tenant.

Refresh token is bound to (user_id, tenant_id). Storing refresh tokens per tenant prevents cross-tenant replay.

On any request, backend re-verifies membership.status = 'active'. If the membership is revoked after token issue, request fails within one access-token lifetime (15 min) — and immediately on permission version bump.

4.4 Authorization model
Permission codes are global strings (order.accept_qr). Roles are per tenant. membership_roles + role_permissions + permissions produce the effective set.

Branch scoping: each permission check receives the target resource. If the resource has branch_id, the check requires branch_id ∈ ctx.branch_ids unless the user has branch.unrestricted (owner/manager default). Waiter on Branch A cannot accept a QR order on Branch B.

Resource ownership check happens in the service layer, not the route. Every repository query must include tenant_id = ctx.tenant_id and (when scoped) branch_id IN ctx.branch_ids. There is no "admin override" that silently bypasses this.

@require_permission("...") dependency remains, but now also takes an optional branch_scoped=True flag to require branch membership.

Super admin uses a different dependency @require_platform_role("..."). It must never be usable by staff JWTs.

4.5 Session invalidation
Logout revokes the refresh token and increments users.token_version.

Suspending a tenant increments every member's token_version and marks the tenant status. Requests to a suspended tenant's endpoints return TENANT_SUSPENDED (403) regardless of token validity. Read-only endpoints may remain available depending on plan (e.g. data export during a past-due grace period).

Password change invalidates all refresh tokens for that user.

Role change bumps the user's pv.

5. Tenant isolation strategy
5.1 Layers of defense
Layer	Mechanism	Enforced where
L1 — Auth context	ctx.tenant_id, ctx.branch_ids derived only from verified token + DB membership	Middleware / dependency
L2 — Repository discipline	Every query filters tenant_id = ctx.tenant_id; branch filter when scoped	Repository layer
L3 — Resource ownership	Service layer re-verifies the loaded row's tenant_id matches ctx.tenant_id before mutating	Service layer
L4 — Database FKs	Every reference is FK-constrained; a cross-tenant reference would violate a composite check constraint where possible	DB schema
L5 — RLS (Stage 4)	current_setting('app.current_tenant_id') policy on every operational table	Postgres
L6 — Cross-tenant tests	CI test suite that proves one tenant cannot read/write another's rows on every endpoint	Test suite
5.2 Defense-in-depth details
Composite foreign keys for cross-entity integrity:

Where two tables must belong to the same tenant, use composite FKs:

sql
ALTER TABLE orders
  ADD CONSTRAINT orders_session_tenant_fk
  FOREIGN KEY (dining_session_id, tenant_id)
  REFERENCES dining_sessions(id, tenant_id);

-- Requires a UNIQUE(id, tenant_id) on dining_sessions for this to work:
ALTER TABLE dining_sessions ADD CONSTRAINT dining_sessions_id_tenant_unique
  UNIQUE (id, tenant_id);
This makes it impossible at the database level to link an order to a session in a different tenant. Apply this pattern to every parent-child pair that must share a tenant.

Branch-scope FK:

sql
ALTER TABLE tables ADD CONSTRAINT tables_branch_fk
  FOREIGN KEY (branch_id, tenant_id)
  REFERENCES branches(id, tenant_id);
No client-supplied tenant anywhere:

Staff endpoints: tenant_id never read from URL/body/query.

Customer QR: qr_token is the only input; server resolves table → branch → tenant.

Webhooks: payment_id / intent_id resolves the tenant, and the resolved tenant must match the payment row's tenant_id; otherwise reject.

Super admin: tenant_id in path is accepted, but only in /api/platform/* and only with a platform-admin token.

Cross-tenant tests (mandatory):

For every protected endpoint, generate a test with two tenants and two users, and assert:

Tenant A user cannot GET, PUT, DELETE Tenant B's resources → 404 (not 403; do not leak existence).

Tenant A user cannot mutate Tenant B's resources even with a guessed valid UUID.

Customer QR session for Branch A cannot access Branch B's order/bill.

Platform admin can act on both (as expected).

Idempotency keys are scoped by (tenant_id, scope, key) — a key from Tenant A cannot replay into Tenant B.

WS/SSE subscriptions only deliver events scoped to ctx.tenant_id and ctx.branch_ids.

Audit log entries from Tenant A never appear in Tenant B's audit view.

The test suite lives in backend/tests/isolation/ and runs on every PR. It runs a second time with RLS enabled (Stage 4+) to prove RLS didn't accidentally widen access.

Shared resources audit: Some tables are intentionally global (permissions, plans, platform_admins). These must not carry tenant_id. An explicit allowlist exists in a config file; the isolation test asserts no tenant-scoped endpoint returns global data it shouldn't, and no tenant-scoped table lacks tenant_id.

5.3 What "strict isolation" means concretely
A staff request cannot read a row where row.tenant_id != ctx.tenant_id, even with a valid UUID and correct permissions.

A customer QR request cannot read a row outside its dining session's tenant + branch.

A background worker processing Tenant A never loads Tenant B's rows in the same transaction; each tenant's batch runs in its own transaction with SET LOCAL app.current_tenant_id.

A super-admin action is explicitly logged in platform_audit_logs with tenant_id recorded; it is the only sanctioned cross-tenant read/write path.

6. Subscription and billing architecture
6.1 Entitlements model
A plan is a bundle of entitlement keys with limits:

json
{
  "branches": { "limit": 1 },
  "staff_users": { "limit": 10 },
  "orders_per_month": { "limit": 5000 },
  "online_payments": { "enabled": true },
  "inventory": { "enabled": false },
  "custom_reports": { "enabled": false },
  "api_access": { "enabled": false }
}
Rules:

limit — numeric ceiling.

enabled — boolean feature flag.

Entitlements are defined on plans.entitlements (JSONB). The effective entitlement set for a tenant is plan.entitlements merged with any tenant-level overrides in a future tenant_entitlement_overrides table. Ship the merge function now, ship the override table when needed.

6.2 Enforcement points
Server-side, always. Client never sees enforcement as a gate; it only sees what the API allows.

Entitlement	Enforced at
branches.limit	POST /branches — count existing branches; reject with ENTITLEMENT_EXCEEDED
staff_users.limit	POST /memberships — count active memberships; reject
orders_per_month.limit	Before order creation — check Redis counter; reject or downgrade feature (config)
online_payments.enabled	POST /bills/{id}/online-payment — reject if disabled
inventory.enabled	GET /inventory/*, POST /inventory/* — reject if disabled
custom_reports.enabled	Reports endpoints tagged with feature = 'custom_reports'
api_access.enabled	API key middleware
Rejection error code: ENTITLEMENT_EXCEEDED with details.entitlement, details.limit, details.current. The UI shows an upgrade prompt.

Redis usage counters:

Key: usage:{tenant_id}:{metric}:{period_start_iso}.

Incremented atomically (INCR) at the enforcement point.

Persisted to usage_counters by a Celery task every 5 minutes and on month rollover.

Source of truth for enforcement is Redis (fast); Postgres is the audit trail.

If Redis is down: fail open for order creation but log loudly and alert. The plan's "operational reliability first" principle wins over strict plan enforcement when infrastructure fails.

6.3 Subscription lifecycle
text
trialing ──(payment succeeds)──► active
active ──(payment fails, dunning)──► past_due
past_due ──(grace ends)──► suspended
active ──(cancel at period end)──► cancelled (at end)
cancelled ──(period end)──► expired
trialing: full features of the selected plan for N days.

past_due: features enabled but a prominent banner in dashboard; dunning emails.

suspended: read-only; staff cannot create orders; customer QR shows a "temporarily unavailable" message.

cancelled: full access until current_period_end, then expired.

expired: data retained for X days (configurable); then per retention policy.

Tenant status mirrors subscription status for fast endpoint checks. A middleware checks tenant.status and blocks writes when suspended or expired.

6.4 Platform billing gateway
Recommendation: Stripe for platform subscription billing (subscriptions, invoices, dunning, tax). Alternatives: Paddle (merchant of record, takes tax burden), Chargebee (heavier, more expensive), Lemon Squeezy (lighter). Stripe is the default choice for a SaaS at this scale.

Customer-facing restaurant payments stay on the payment gateway you already selected for the pilot (Stripe, Adyen, or a regional provider). Platform billing and restaurant payments are separate concerns — do not co-mingle.

Webhook endpoint: POST /api/platform/webhooks/stripe — separate router, separate signing secret, separate idempotency table (reuse idempotency_keys with a new scope).

Events handled: invoice.paid, invoice.payment_failed, customer.subscription.updated, customer.subscription.deleted, customer.subscription.trial_will_end.

Every event written to platform_billing_events before processing; processing is idempotent on event.id.

6.5 Dunning
past_due → 3 retry attempts over 7 days via Stripe's dunning.

Email sequence: day 1, 3, 7.

Day 7: tenant goes suspended; dashboard read-only; customer QR blocked.

Day 30: expired; data retention policy starts.

6.6 Refunds and credits
Platform refunds handled in super-admin with billing.refund permission.

Credits (one-time adjustments) recorded as a negative line on the next invoice; not as a Stripe credit unless a refund is issued.

Every billing action logged in platform_audit_logs.

7. API endpoint changes
7.1 URL structure
Keep /api/v1/* for staff and customer. Add /api/platform/* for super admin. Do not put tenant_id in the staff URL — it comes from the token.

text
/api/v1/auth/...                     — login, refresh, switch-tenant, logout
/api/v1/tenant                       — current tenant profile + entitlements
/api/v1/branches                     — list, create, update, archive
/api/v1/menu/...                     — tenant-wide menu, with ?branch_id= filter
/api/v1/tables?...branch_id=...      — operational tables per branch
/api/v1/orders/...                   — operational orders (ctx scoped)
/api/v1/kitchen/...
/api/v1/bills/...
/api/v1/payments/...
/api/v1/inventory/...
/api/v1/reports/...
/api/v1/users, /api/v1/memberships   — tenant staff management
/api/v1/qr/...                       — customer QR (unauthenticated, token-bound)
/api/v1/webhooks/payments/{provider} — customer payment webhooks

/api/platform/auth/...               — super admin login/refresh
/api/platform/tenants                — list, create, suspend, reactivate
/api/platform/tenants/{id}           — details, plan change, entitlements override
/api/platform/plans                  — list, create, update
/api/platform/subscriptions          — list, inspect, override
/api/platform/invoices               — list, void, refund
/api/platform/analytics              — platform metrics
/api/platform/audit-logs             — platform audit trail
/api/platform/webhooks/stripe        — platform billing webhook
7.2 Endpoint changes for the existing staff/customer APIs
Existing	Change
POST /auth/login	Returns user + tenants[] + a default-tenant token, or a needs_tenant_selection response
POST /auth/refresh	Rotates per (user, tenant)
new POST /auth/switch-tenant	Exchanges for token bound to another tenant
GET /restaurant/settings → GET /tenant and GET /branches/{id}	Split concerns: tenant-level (plans, entitlements) vs branch-level (tax, receipt)
GET /tables	Requires branch_id in query; ctx.branch_ids must include it
POST /orders	branch_id derived from dining_session; never client-supplied
POST /qr/sessions	Resolves branch + tenant from qr_token
POST /qr/{session}/orders	Same; order creation checks orders_per_month entitlement
POST /bills/{id}/online-payment	Rejects if online_payments entitlement disabled
All menu endpoints	Return tenant-wide items merged with branch overrides; availability from menu_item_branch_availability
All inventory endpoints	Reject if inventory entitlement disabled
All reports	Scope by branch(es) in ctx.branch_ids; some reports allowed tenant-wide if user has report.tenant_wide
7.3 Endpoint additions for super admin
Listed in §7.1. Every super-admin endpoint:

Uses platform_admins auth, never staff auth.

Logs to platform_audit_logs for any state-changing action.

Requires an explicit platform role (support, billing, ops, superadmin).

Returns tenant_id and tenant_status in responses so the operator knows context.

7.4 Breaking changes and deprecation
No breaking changes in Stage 1–3. Existing /api/v1/* endpoints keep working with implicit tenant.

Stage 4 adds new endpoints (/branches, /tenant); old /restaurant/* still works but emits a Deprecation header and logs usage.

Stage 5 removes deprecated endpoints. Only for internal clients we can update in the same release.

Customer QR remains backward-compatible: the URL shape t/:qrToken is preserved; qrToken continues to resolve to a tables row, whose branch_id and tenant_id are now visible to the backend.

7.5 OpenAPI versioning
/api/v1 and /api/platform have separate OpenAPI schemas.

Generated clients regenerate on every merge to main.

API contract changes require an ADR if they are breaking.

8. Frontend and mobile application changes
8.1 Application surface split
App	Who	Hosted at	Notes
Customer web	Diners	order.{tenant-slug}.{platform-domain} or {platform-domain}/r/{tenant-slug}	Tenant resolved from URL slug + QR token. No auth.
Restaurant dashboard	Staff	app.{platform-domain}	Multi-tenant; tenant switcher in header.
Super admin	Platform team	admin.{platform-domain}	Separate app; separate auth; separate deploy.
Staff mobile	Waiters, kitchen	Native app stores	Tenant switcher inside app; add after first tenant ships.
8.2 URL and hostname strategy
Option A (chosen): subdomain per tenant for the customer web, e.g. blue-fork.platform.com.

Pros: clean links, per-tenant SSL via wildcard cert, straightforward tenant resolution, easier white-labeling later.

Cons: DNS management, wildcard cert, cookie scoping if shared.

Option B (rejected): path prefix platform.com/r/blue-fork.

Pros: simpler ops.

Cons: harder to white-label, weaker branding per tenant.

Restaurant dashboard: single host app.platform.com with tenant switcher. Per-tenant subdomains for staff can be added later if white-labeling is demanded.

8.3 Auth changes
Web (staff):

Login → if multiple tenants, show tenant picker → POST /auth/switch-tenant → store tokens (refresh in HttpOnly cookie scoped to app.platform.com; access in memory).

Header: tenant name, branch switcher (if user has multiple branches), user menu.

Tenant switch: call /auth/switch-tenant, then invalidate all React Query caches (critical: queryClient.clear()), then redirect to the tenant's default page.

On 401: refresh; if refresh fails, sign out.

On 403 with TENANT_SUSPENDED / ENTITLEMENT_EXCEEDED: show a dedicated page, not a generic error.

Mobile (staff):

Same flow. Store refresh token in expo-secure-store keyed by (user, tenant).

Tenant switch: clear React Query cache, reconnect WS with new token.

Customer web:

No login. Tenant context from hostname + qrToken. No change to the customer journey other than honoring branch-level overrides (tax, service charge) that come from the backend.

Super admin:

Separate app; separate login at admin.platform.com. Never share cookies with app.platform.com or tenant subdomains.

Different design language (denser, more utilitarian) to prevent accidental context confusion.

8.4 Tenant-aware state
Add TenantContext (React context) holding { tenant, branches, currentBranch, entitlements }.

The current branch is part of the URL: ?branch=<slug> for deep-linkable state, defaulting to the user's first allowed branch.

On tenant switch, clear every React Query cache and Zustand store that contains server-derived data. This is the single most common cross-tenant leak in React SaaS apps — make it explicit in rules/frontend.md.

Permission checks in UI come from entitlements + perms in the token. Use <Can permission="..."> and <Feature flag="online_payments"> components.

8.5 Menu changes for branches
Menu screen gains a branch selector at the top (defaults to current branch).

Items show tenant-wide definition; per-branch overrides (availability, price) are editable.

Public menu shows only available items for that branch.

8.6 QR and customer flow
URL: https://{tenant-slug}.platform.com/t/{qrToken} (no tenant_id in the URL — the hostname provides it and the token validates it).

Customer screen gains: "Request waiter" button (new feature surfaced by your brief) → POST /qr/{session}/waiter-request.

Restaurant name shown on customer app comes from tenant; branch name shown as a subtitle.

8.7 Super admin app
Separate Vite app in apps/admin with:

Tenant list + filters (status, plan, trial).

Tenant detail: plan, subscription, branches, users count, usage, invoices, suspend/reactivate, entitlement overrides.

Plans management.

Platform analytics.

Platform audit log.

Platform admins management (superadmin only).

Reuse packages/ui for components; do not reuse dashboard layouts.

8.8 Migration sequencing for clients
Stage 1–2: ship dashboards with tenant switcher hidden (single tenant). No visible change to end users.

Stage 3: turn on the tenant switcher for internal pilot tenants.

Stage 4: launch super admin app.

Stage 5: launch customer subdomain rollout.

9. Security threat model
9.1 Threat actors
Malicious diner: guesses or shares a QR code, tries to access other tables/bills, attempts to mark payments paid.

Malicious staff: tries to access another tenant's data, escalate permissions, refund themselves.

Compromised staff device: stolen phone, leaked refresh token.

Tenant admin abusing scope: tries to access another tenant's data via API.

Platform admin mistake or malice: over-broad actions without audit.

External attacker: credential stuffing, webhook forgery, API enumeration, SQL injection, SSRF via webhooks.

Supply chain: compromised dependency.

9.2 Threats and mitigations
#	Threat	Mitigation
T1	Cross-tenant read via guessed UUID	L2/L3 scoping; 404 not 403; RLS in Stage 4; isolation tests
T2	Cross-tenant write via supplied tenant_id	Never read tenant from client; composite FKs enforce same-tenant relationships
T3	QR token reuse / sharing	Rotatable table tokens, short customer session (30m), staff accept/reject gate, per-token rate limits
T4	Payment webhook forgery	Signature verification with provider SDK; event idempotency; server-side reconciliation
T5	Replay of webhooks	Unique constraint on (provider, event_id) in payment_events; store payment_events payloads and match
T6	Customer marks own payment as paid	Never; payments.status mutated only by backend on trusted confirmation
T7	Stolen refresh token	Rotation on use, hashed storage, user_agent/ip recording, revoke on reuse detection, token_version bump on logout
T8	Privilege escalation via role edit	Role changes require user.manage + audit; pv bump invalidates live tokens; owner-only for granting owner
T9	Stale JWT after deactivation	pv checked every request; user status checked every request
T10	Platform admin abuse	Separate realm, per-action audit, IP allowlist for superadmin, no read access to customer PII beyond necessary
T11	Tenant enumeration	Slug is public (by design for customer subdomain) but no list endpoint without auth; login page reveals no tenant existence
T12	Brute-force login	Rate limit by IP + by account; argon2id; uniform response timing
T13	SQL injection	Parameterized queries only; no string concatenation; mypy + ruff enforce
T14	SSRF via user URLs (menu images)	Upload via controlled object storage; no server-side fetch of arbitrary URLs
T15	CSRF on cookie-auth web	SameSite=Lax for refresh; short access in memory; same-origin API; CSRF token for state-changing forms if cross-site policy weakens
T16	XSS in menu content	Sanitize rich-text if introduced; default render as text
T17	Entitlement bypass	Enforcement server-side; client flags are display-only
T18	Suspended tenant continues to operate	Middleware blocks writes on suspended/expired; token version bump on suspension
T19	Webhook DoS	Rate limit, signature check first, queue processing
T20	Cross-tenant WS/SSE leakage	Subscribe endpoints validate tenant_id + branch_id per topic; no broadcast across tenants
T21	Sensitive data in logs	Structured logging with PII redaction list; no tokens, PINs, card data
T22	Overly broad DB role	App role is not owner; append-only tables get a restricted role
T23	Secret leakage in CI/logs	Secrets only in env/secret manager; scan commits; rotate on incident
T24	Data exfiltration by tenant	Export allowed per plan; every export audited; rate-limited
T25	Backup data crossing tenants	Backups encrypted; restore drills verify isolation; no per-tenant selective restore until schema-per-tenant (not planned)
9.3 Secure defaults
Deny by default on every route: require_permission is mandatory on any non-public endpoint (a route without it fails a lint/test).

Every read and write goes through repositories that take ctx. A repository function without ctx fails code review and is caught by a unit test that asserts every repo method signature.

Every response from a tenant-scoped resource includes a tenant_id field internally; a middleware asserts it matches ctx.tenant_id before serializing (defense-in-depth, catches developer mistakes early).

All admin actions require re-auth if last_auth_at > 1 hour (super admin only).

9.4 Privacy and compliance posture
Data residency: tenants.data_region reserved; actual multi-region deployment deferred.

GDPR-style concerns: right of deletion must cascade per tenant; soft-delete policy in rules/database.md must be updated to include a data-erasure workflow.

PII inventory: user PII is minimal (name, email, phone); customer PII is none (QR flow is anonymous by default).

Retention: audit_logs and payment_events retained for 7 years (configurable); operational data per plan retention.

Platform-level DPAs are a commercial task, out of scope for this plan.

10. Phased implementation roadmap
Numbering follows the build plan's phase structure, extended for SaaS.

Phase 0 — Foundation review (1 week)
Inspect the actual repository; validate §1 assumptions.

Produce ADRs for: shared-schema vs schema-per-tenant, RLS stance, tenant resolution, billing gateway.

Stand up the isolation test harness skeleton.

Exit: written sign-off on §1–§3 of this document.

Phase 1 — Tenancy scaffolding (2 weeks)
Migrations M1 + M2 (new tables, nullable columns).

Backfill script for existing single-tenant data.

TenantContext, tenant middleware, @require_permission extended for branch scoping.

/api/v1/tenant returns the current tenant.

Do not remove restaurant_id yet.

Exit: existing app still works; new tables exist; isolation test skeleton green.

Phase 2 — Multi-tenant auth (2 weeks)
Membership model.

JWT with tenant_id, pv, branch_ids.

/auth/login, /auth/refresh, /auth/switch-tenant.

Tenant switcher UI (web + mobile).

Query cache clear on tenant switch.

Exit: one user can belong to two tenants and switch; tokens are rejected across realms; all existing endpoints still pass tests.

Phase 3 — Branch model (2 weeks)
Migration M3 (dual-write) + M4 (read from new columns).

branches CRUD, branch switcher UI.

Per-branch menu overrides + availability.

Branch-scoped tables.

Exit: a tenant can have two branches with different menus and separate tables; isolation tests cover both axes.

Phase 4 — RLS and isolation hardening (2 weeks)
Enable RLS on operational tables; policies + role separation; set app.current_tenant_id per transaction.

Full cross-tenant test suite (two tenants × all endpoints) with and without RLS.

Composite FKs enforcement.

Exit: every cross-tenant test passes; a deliberate un-scoped query returns zero rows instead of leaking (verified by test).

Phase 5 — Super admin and plans (2 weeks)
platform_admins realm + apps/admin app.

Plans table + entitlements service.

Tenant list/detail, suspend/reactivate.

Exit: super admin can register a new tenant with a plan and the tenant can log in and operate within its entitlement limits.

Phase 6 — Subscriptions and platform billing (3 weeks)
Stripe integration (subscriptions, invoices, dunning, webhooks).

usage_counters + Redis enforcement.

Entitlement enforcement on branches, staff users, orders/month, feature flags.

Upgrade/downgrade flow.

Exit: trial → active → past_due → suspended lifecycle works end-to-end in Stripe test mode; entitlement rejections produce correct error codes.

Phase 7 — Customer QR tenant routing (1 week)
Wildcard subdomain + wildcard TLS.

qr_token → branch → tenant resolution across all QR endpoints.

Customer app branding per tenant.

Exit: blue-fork.platform.com/t/{token} works; the same token against a wrong-tenant hostname fails safely.

Phase 8 — Waiter request feature (1 week, per brief)
New waiter_requests table + endpoint + UI in customer app and dashboard.

Rate-limited; tied to dining_session.

Phase 9 — Migration M6 (drop restaurant_id) (1 week)
After all reads and writes use tenant_id/branch_id and the isolation suite has been green for 2 weeks.

Requires full backup and a rollback plan.

Phase 10 — Commercial launch hardening
Penetration test of tenant isolation.

Load test: 100 tenants, 500 concurrent staff, 10k QR orders/hour.

Restore drill including per-tenant data verification.

Support runbook + on-call.

Deferred from this roadmap (explicitly)
Per-tenant database encryption.

Multi-region hosting.

API keys for tenant-facing programmatic access.

Marketplace / app integrations.

White-label per-tenant custom domains (wildcard subdomains only for now).

11. Backward-compatibility concerns (consolidated)
Concern	Strategy
Existing single-tenant deployments	M1/M2 add nullable columns; M3 dual-write; M4 flag-gated read switch; M5 RLS off by default; M6 drop columns only after two weeks of green
Existing tokens	Rotation window: old tokens (without tenant_id) accepted for 1 access-token lifetime after deploy; then rejected
Existing QR URLs	t/:qrToken unchanged; resolution gains branch/tenant from token lookup
Existing webhooks	Signature and payload unchanged; add tenant resolution from DB
Existing mobile app versions	Old binaries fall back to single-tenant behavior until they update; enforce minimum version after 90 days
Existing customer web deep links	Redirect old platform.com/t/{token} to {tenant}.platform.com/t/{token}
Existing DB row counts	Backfill verified by row-count parity per table before M4
12. Key design decisions and alternatives
Decision	Chosen	Alternative considered	Reason
Tenancy model	Shared schema + tenant_id + RLS (later)	Schema-per-tenant	Simpler migrations, one pool, cross-tenant analytics; RLS covers isolation
Tenant resolution	From verified token / QR token / webhook record	Client-supplied tenant_id	Never trust client for security boundaries
RLS timing	Stage 4, not Stage 1	RLS from day one	Application discipline must be correct first; RLS hides bugs
Auth realms	Three separate realms	One realm with roles	Separation prevents privilege mistakes and blast radius
Tenant switch	Re-issue token	Multi-tenant claim in one token	Cleaner revocation, per-tenant session, simpler refresh
Subscription gateway	Stripe (recommended)	Paddle (MoR), Chargebee, Lemon Squeezy	Mature, flexible, best tooling; MoR reconsidered if tax burden is significant
Customer URL	Subdomain per tenant	Path prefix	Branding, per-tenant SSL, easier white-label later
Branch model	Added now (Stage 3)	Add later when first multi-branch tenant appears	Cheap now, expensive to retrofit; brief requires it
Worker context	Explicit per-tenant transactions	One transaction across tenants	Eliminates accidental cross-tenant reads
Audit realms	audit_logs (tenant) + platform_audit_logs (platform)	One table	Separate retention, separate access controls, prevents platform actions leaking into tenant audit views
13. What I need from you before any code
Please confirm or correct the following. Each answer changes the plan in the sections listed.

ASSUMPTION review (§1.1). Is the current codebase materially the single-tenant plan we developed earlier, or is there a real repo with different structure? If it's a real repo, I need a short summary or access before Stage M2 begins.

Branches required now or later? The brief says yes. Confirm we are adding branches in Phase 3, not deferring.

RLS timing. Confirm Stage 4, not Stage 1. If compliance requires earlier, we accept the added complexity and move it to Phase 2.

Customer URL scheme. Confirm subdomain-per-tenant ({tenant}.platform.com). If path prefix is preferred for cost, say so now — the migration from one to the other is painful later.

Platform billing gateway. Stripe? Or is there a preferred gateway in your region (regional VAT/MoR considerations may override).

Plans and entitlements — concrete shape. Give me the three (or four) plans you want to sell, with limits and features. I will not guess pricing.

Super-admin scope. Who logs in, from where (IP allowlist?), and what can each platform role do? Default proposal is in §8.7 and §9.2; confirm or amend.

Customer-facing payment gateway. Same as the pilot's restaurant payments, or changed for SaaS? Any country-specific constraints?

Suspension behavior. Confirm that suspended means read-only dashboard + customer QR disabled. Some SaaS products keep QR working and only block the dashboard.

Migration tolerance. Confirm there are no existing paying customers on the current single-tenant deployment. If there are, M3–M6 need a maintenance window plan and a rollback runbook.

Data retention. Confirm retention periods for audit_logs, payment_events, platform_audit_logs. Default proposal: 7 years for audit, 7 years for payment events, 3 years for platform audit.

Deletion/erasure. Confirm we implement per-tenant deletion (data export + cascade soft-delete + PII erasure) in Phase 5 or later.

Once I have those answers, the next artifact is a revised schema.md and a migration runbook for Phase 1. I will not write code until you approve §1–§10 and answer §13.

14. Summary of my recommendation
Go shared-schema with tenant_id + branch_id, and add RLS in Stage 4 as defense-in-depth, not as the primary mechanism.

Split restaurant into tenants + branches + (per-branch settings), and keep all existing operational tables — widen, don't rewrite.

Three separate auth realms; JWTs bound to (user, tenant); tenant switching is a token exchange, not a claim.

Enforce tenant at the server edge, repository, service, FK, and test layers; never trust a client-supplied tenant.

Subscription entitlements are centralized, enforced server-side, mirrored by Redis counters and persisted to Postgres.

Platform billing and restaurant payments are separate systems.

Customer URL: subdomain per tenant.

Six-stage rolling migration; nothing broken until the final column drop.

Isolation tests run on every PR and are the gate for merging.

Workflow discussion — multi-tenant SaaS
Good call. Architecture can wait. Workflow is where you actually find out whether the product makes sense. Let me walk through what I think the real workflows become once this is multi-tenant, and flag where the interesting decisions live. Push back or redirect wherever you want — nothing here is settled.

1. The new tenant onboarding workflow
Right now onboarding is an engineering task: someone deploys, someone seeds a restaurant row, someone hands out logins. In SaaS that becomes a product surface, and the first real decision is: self-serve or sales-assisted?

My instinct for your stage: sales-assisted self-serve. Meaning:

The restaurant owner fills out a form on the marketing site.

They land in a short setup wizard: business name, first branch, timezone, currency, tax mode, menu (upload or skip), staff invites.

They land on a trial dashboard with a default plan.

A human (you) gets notified to call them within 24 hours.

The first 30 minutes matter more than the next 30 days. If a restaurant can't see their own menu on a tablet by minute 30, they don't come back.

The workflow questions I'd want us to answer:

Does a tenant exist before the first user logs in, or does the first user's signup create it?

Can one person own two separate restaurant businesses under two separate tenants, or is that always a single tenant with two branches? I'd say two tenants — different brands, different billing.

What's the minimum viable setup to enter the operational dashboard? I'd argue: name, timezone, currency, one branch, one table, one menu item, one staff user. Everything else can be wizard-skipped and prompted later by banner.

What happens if a tenant abandons mid-wizard? The tenant row exists in pending; after 7 days it's cleaned up. No half-configured tenants floating forever.

2. Tenant lifecycle workflow
I proposed trial → active → past_due → suspended → cancelled → expired. That's the mechanical view. The workflow view is: what does each state actually feel like to the people inside the tenant?

Trial. Full features. A persistent banner: "23 days left in trial." Owner sees a "Choose a plan" CTA. Staff sees nothing — they shouldn't have to know the business model.

Active. Silent. No banner. Billing emails go to the owner only.

Past due. Banner for owner and manager: "We couldn't process your last payment. Update billing." Staff sees nothing yet. Customer QR still works. Grace period is real.

Suspended. Now everyone knows: owner sees a blocked dashboard with a "Restore access" button. Staff sees "Account suspended — contact your manager." Customer QR shows "This restaurant is temporarily unavailable." No orders can be created. Data is preserved.

Cancelled. Access until period end, then expired. Banner: "Your subscription ends on {date}. Export your data."

Expired. Read-only dashboard for owner (export, invoices). Staff and customers blocked.

The interesting workflow questions here:

Who can trigger a state change? A failed payment is automated. A suspension is also automated after dunning. But a manual suspension is a super-admin action with a mandatory reason. These two paths should never share code.

Does suspension stop everything at once, or is it graceful? My proposal: graceful. First 2 hours = read-write but banner escalates. Then write-lock. Then customer QR blocked. Because if you cut a restaurant off mid-dinner service, you'll never win them back.

What happens to an in-flight dining session when a tenant is suspended? This is the worst-case scenario. My take: let existing sessions finish. New sessions can't start. So a bill opened 10 minutes before suspension can still be paid and closed. This needs explicit design or it becomes an operational horror story.

Can a suspended tenant still export their data? Yes. Always. Blocking exports makes customers angry and creates legal risk.

3. User membership workflow
This is the workflow I think is most under-discussed in most SaaS architecture. Three distinct flows:

Flow A — Invite. Manager invites a person by email. That person gets a magic link. They set a password, join the tenant with a role assigned. They might already have an account on the platform — in which case the invite adds a membership to their existing account, not a new account.

Flow B — Role change. Manager changes a user's role. Tokens are version-bumped, so the change is effective immediately, not at next login. If the change is a demotion, any open sessions should show a "your permissions changed" notice within seconds — not silently stop working.

Flow C — Removal. User is removed from a tenant. Their historical audit entries remain attributed to them. Their account still exists if they belong to another tenant. If they belong to no tenant, the account goes dormant but isn't deleted (they might be re-invited later).

Now the workflow questions that matter:

A user switching between two tenants: do they need a separate login for each, or one login? My strong opinion: one login, tenant switcher after login. Separate logins will confuse real users and double your support load.

Email change: one person, one global email identity. Changing email is a global action, not a per-tenant one.

What happens to a user's open orders when they switch tenants? Nothing — they're still running. But the app should probably warn "You have 3 pending orders in Blue Fork" if they switch away mid-shift. Soft friction, not a block.

Do staff accounts cost money per seat, or per active seat? If per-seat, the workflow of "invite a temp waiter for a weekend" becomes a billing event. That's a user-hostile workflow if it's not handled well. Worth deciding early.

4. Tenant switching — the daily workflow
This is the workflow that will define the SaaS feel more than any other. A regional manager of 3 restaurants logs in every morning and needs to hop between them.

My proposal:

Login goes to the last-used tenant, not a picker every time. Picker only appears for new users or after an explicit "switch" action.

The switcher is one click, in the header. Named, not iconic, so the current context is unambiguous. A subtle border or color strip on the page edges shows which tenant you're in (helps prevent the "I just edited the wrong restaurant's menu" problem).

Switching tenants drops all in-progress state: open modals, unsaved forms, dirty carts. It asks for confirmation if anything is dirty. Then it refetches everything from scratch — no cached data carries over. This is the single most common source of cross-tenant UX bugs, so it must be handled deliberately, not accidentally.

Deep links carry tenant context. A URL like /orders/123 should either fail clearly on the wrong tenant or include the tenant in the URL (/t/blue-fork/orders/123). I lean tenant-scoped URLs because it makes copy-pasted links safe.

Browser tabs can hold different tenants. If I open Blue Fork in one tab and Red Fork in another, both should work. This means the current tenant must live in the URL/session, not just in a cookie. The cookie holds the auth; the URL holds the context.

The interesting workflow questions:

Do notifications carry tenant context? A "new pending order" push notification should deep-link to that specific tenant, not the last-used one.

Does the tenant switcher show branch counts and roles? Yes — "Blue Fork (3 branches) — Manager" is much safer than just "Blue Fork."

What if I'm removed from a tenant while I'm in it? Graceful ejection on next request, with a clear message. Not a silent 401.

5. Branch workflow inside a tenant
This is where the multi-branch story becomes concrete. Let me walk through a real day for a 3-branch tenant.

Menu workflow:

A menu item is created once at tenant level: name, description, default price, category.

Each branch can override: availability, price, or hide entirely.

Important workflow decision: does the branch inherit changes automatically when the tenant-level item is edited? My proposal: yes for description and options; no for price. Price changes at tenant level should propagate only to branches that haven't overridden. Branches that overrode keep their price.

A "publish" action makes changes visible to the customer QR. This should be explicit — a manager can edit draft prices for tomorrow without the customer seeing them.

Staff workflow:

A staff member can be tenant-wide (regional manager) or branch-scoped (branch waiter).

The tenant-wide user sees a branch picker inside the tenant. Branch-scoped users don't — they only ever see their branch.

When a branch-scoped waiter tries to open a table in another branch, the failure should be invisible — the table doesn't appear in their list at all, rather than a 403.

Operational workflow:

Kitchen display is per branch, not per tenant. Each branch has its own screen, its own queue.

Cashier is per branch. One cash drawer per branch. End-of-day is per branch, not per tenant.

Reports are per branch by default, with an optional "all branches" rollup for tenant-wide users.

Inventory is per branch, not per tenant. Stock doesn't teleport. Purchases happen at a branch.

The interesting workflow question: what does a tenant-level "owner" actually do day-to-day? Probably they see the rollup dashboards and never touch operational screens. Their workflow is entirely different from a cashier's. This might mean the dashboard needs an owner view that's distinct from the manager view — not just a permission difference.

6. The customer QR workflow — what changes
The customer's workflow is mostly unchanged, but two things do shift.

First, how does a diner get to the right tenant?

Subdomain blue-fork.platform.com resolves tenant.

QR token resolves table → branch → tenant, and must match the subdomain. If it doesn't, error: "This QR code doesn't belong to this restaurant. Please ask a staff member."

If a diner scans a Blue Fork QR but types red-fork.platform.com in the browser, they get a "not found" not a redirect. Redirects across tenants would be a data leak vector.

Second, what changes for the diner?

They see the restaurant's brand, not the platform's brand. (White-labeling is probably worth doing from day one on this surface, even if internal dashboards aren't white-labeled.)

The "Request waiter" button (from your brief) is a new workflow: diner taps, a notification goes to the branch's waiter queue, a waiter acknowledges within X seconds, and the diner sees "A waiter is on the way" or "Please wait, we're busy." The acknowledgment workflow is what makes this feature feel real, not the button.

Workflow questions:

Waiter requests should be per-branch, obviously. But which waiter gets it? All on shift? The one assigned to that zone? The floor manager? My take: a shared queue + the ability to claim, not auto-assignment. Auto-assignment always fails when someone's in the bathroom.

What happens if nobody claims within 60 seconds? Escalate to manager, then to a broader waiter pool. If still unclaimed, the diner sees "We're experiencing a delay — please flag down a staff member." Honest, not silent.

7. Super admin workflow
This needs to feel like a different product, not a power-user mode of the dashboard. A support agent should never accidentally be one click away from a live restaurant's kitchen screen.

Support workflow:

Search a tenant by name, email, or slug.

View tenant status, plan, subscription, usage.

View recent platform audit events for that tenant.

Impersonate read-only if necessary, with the tenant being notified via email ("a support agent viewed your account" — many SaaS products do this).

Never edit tenant operational data from the super admin. That's what the tenant's own dashboard is for.

Billing workflow:

View invoices, issue refunds, apply credits.

Change a plan (upgrade, downgrade, override).

Extend a trial.

All actions require a reason, and the reason is logged and emailed to the tenant's owner.

Ops workflow:

Suspend / reactivate.

Extend dunning grace.

Force-logout all sessions of a tenant.

All require reason + are logged.

Superadmin workflow:

Everything above, plus managing platform admins, plans, and feature flags.

IP allowlist + re-authentication for any destructive action.

Workflow questions:

Do support agents have a separate identity, or use their platform admin identity? Separate login at admin.platform.com, no shared cookies. This is non-negotiable for a commercial SaaS.

Does impersonation exist in the pilot? My recommendation: not initially. It's the most dangerous feature you can build. Ship it later, read-only, logged, and notified.

8. Entitlement enforcement workflow
The customer-facing workflow of hitting a limit needs to be smooth. Two cases:

Case A — Blocking limit. Tenant on Starter plan (1 branch, 10 users). Manager clicks "Add branch." Backend rejects. UI should not show a generic error. It should show:

"Your Starter plan includes 1 branch. Upgrade to Growth to add more branches."

With a direct upgrade link. And it should happen at the start of the workflow, not after they've filled in branch details. Disable the "Add branch" button when the limit is reached, with a tooltip. Letting them fill out a form and then rejecting at submit is user-hostile.

Case B — Soft limit. Orders per month. If they're at 95% of their quota, show a banner: "You've used 4,750 of 5,000 orders this month. Consider upgrading." At 100%, block new orders with a clear message. But be careful — you're blocking a restaurant's dinner service. That's a serious decision. My take: soft-limit orders, hard-limit branches/users. Orders should never be blocked mid-service; instead, overage billing or auto-upgrade-with-notification. A restaurant losing an order is a much bigger problem than a SaaS collecting an overage.

Workflow questions:

What triggers the entitlement check? Every request, or only at mutation? My take: at mutation. Reads should never be blocked by entitlements. If a tenant exceeds their order quota, they can still see their existing orders; they just can't create new ones.

Does enforcement happen before or after the resource is created? Before. Never roll back a resource after creation due to entitlement. Check first, then create.

9. Migration workflow — the human side
This is the part most SaaS plans get wrong. The technical migration is well-understood. The human migration is what breaks.

For each existing single-tenant deployment:

Tenant creation → their current restaurant becomes a tenant, and their current settings become branch #1.

User migration → each existing staff user becomes a membership in the new tenant. Their login doesn't change. Their password doesn't change.

URL migration → if they were on platform.com/t/{token}, they move to {tenant}.platform.com/t/{token}. Old URLs redirect for 90 days.

QR reprint → table QR codes stay the same token, but now resolve to the tenant. No QR reprint needed unless the URL format changes.

Support handoff → someone calls the owner: "Your account moved to the new platform. Nothing changed except the URL. Here's your invoice for this month." This call matters.

For the pilot restaurant specifically, there are two paths:

Path 1: migrate them as the first multi-tenant tenant. Higher risk to them, but forces the migration to be real. My recommendation.

Path 2: keep them on the single-tenant system indefinitely, onboard new customers multi-tenant from day one. Lower risk to them, but you now maintain two codebases — the exact thing you said you wanted to avoid.

I strongly prefer Path 1, with the pilot owner knowing this is a co-development situation and having an explicit rollback option for the first 60 days.

10. Support and incident workflow
Who can do what to a tenant during an incident?

Tenant's own staff can fix their own operational data within their permissions.

Platform support can view, not edit. If they need to edit, they impersonate read-only or the tenant's own manager does it.

Platform ops can suspend, reactivate, force-logout, extend billing grace.

Only superadmin can change plans, add tenant overrides, delete data.

Every platform action gets a reason, gets logged, and gets a notification to the tenant's owner (except read-only support views, which are logged but often not notified — depends on your disclosure policy).

The workflow question: when a tenant reports a bug, who triages? For the pilot, you do. As you scale, you'll need a support tier that can do lightweight investigation without full superadmin access. Define that tier now.

11. What I'd want to nail down first
Out of everything above, the workflow decisions I'd want to settle before architecture are:

Self-serve or sales-assisted onboarding — determines the entire signup workflow.

One global identity per person, or per-tenant identities — determines whether switching tenants is a core UX or an edge case.

Branch-scoped vs tenant-wide staff — determines the entire dashboard's default view.

Whether a trial-limited tenant can complete a service — the difference between a graceful SaaS and one that ambushes a restaurant at dinner.

Whether we migrate the pilot restaurant in the first release or run parallel — biggest operational risk decision.

Whether the customer QR surface is white-labeled from day one — determines the subdomain decision irreversibly.

Whether orders are ever blocked by entitlement — determines the failure mode of your billing enforcement.

Everything else — RLS timing, schema shape, migration staging — is downstream of those seven.

Feature inventory and workflows
Let me walk through every feature, grouped by app, and for each one describe three things: what's included, who does what, and what happens from trigger to resolution. I'll flag decisions we still need to make inline, and where features depend on each other.

This is the map I'd use to slice work. If we agree on it, we can then take any single feature and design its workflow in detail.

1. Quick feature map
There are really four layers of features, and it's important not to mix them:

Platform layer (one instance, shared by all tenants)

Identity & membership

Tenant provisioning

Subscription & billing

Entitlements

Audit & observability

Notifications & search

SaaS Super Admin app (platform team only)

Tenant management

Plan & subscription management

Platform analytics

Platform billing & invoices

Platform audit

Admin & feature-flag management

Restaurant Dashboard (per tenant, per branch)

Branch management

Menu management

Tables & dining sessions

Waiter ordering

QR order review

Kitchen operations

Billing & cashier

Payments (cash, online)

Staff & permissions

Inventory & purchasing

Expenses

Reports & end-of-day

Settings

Customer Ordering (per tenant, per table)

QR entry

Menu browsing

Cart & order submission

Order tracking

Waiter request

Bill & pay

The platform layer is harder than it looks because it's the one everyone forgets until it hurts. The restaurant layer is the most familiar. The customer layer is the smallest surface with the highest stakes.

2. Platform layer features
These features exist once and serve every tenant. They must be designed before the tenant features, because every tenant feature depends on them.

2.1 Identity & membership
What's included: one global identity per person; memberships to one or more tenants; roles scoped per tenant (and per branch inside a tenant); account lifecycle (invite → active → disabled); password reset, PIN, biometric on mobile.

Workflow: A person has exactly one login. Their email is their identity. When a manager invites them to a second tenant, that becomes a new membership, not a new account. The person logs in once and switches between tenants. Their permissions are the union of what their roles in the current tenant allow — never cross-tenant, never additive across tenants.

Deactivation is per-membership, not per-account: if I'm removed from Blue Fork but still an employee at Red Fork, my account continues. If I'm removed from every tenant, my account goes dormant but isn't deleted — I can be re-invited later.

Key open decision: are staff charged per account or per membership? This affects how inviting a temp waiter feels. My preference: per active membership, but with a grace period for very short memberships.

2.2 Tenant provisioning
What's included: the whole flow from "someone expresses interest" to "a functioning tenant exists with an owner, one branch, and a working dashboard."

Workflow: Three possible entry points:

Self-serve signup (owner fills out the form, gets a trial tenant).

Sales-assisted (you create the tenant after a call, then send the owner an invite).

Migrated existing restaurant (script creates the tenant, migrates data, sends credentials).

All three converge on the same intermediate state: tenant exists in pending (or trialing) with one branch, an owner membership, and a setup checklist. The setup wizard guides the owner through: timezone, currency, tax mode, menu import or manual entry, table setup, staff invites, QR generation. The dashboard works with partial setup — banners prompt what's missing. A tenant is never blocked from operating because they haven't configured something optional.

Open decision: what's the minimum state to be considered "onboarded"? I proposed name, timezone, currency, one branch, one table, one menu item, one staff user. Should verify with actual user interviews before committing.

2.3 Tenant switching
What's included: the flow for a user who belongs to multiple tenants to switch their active working context.

Workflow: Login goes to the last-used tenant, not a picker every time. The picker appears (a) for new users, (b) when they explicitly click "switch," (c) if their last-used tenant is no longer accessible. Switching clears all cached data, cancels in-flight requests, and reloads. The URL includes the tenant slug so deep links are safe. Notifications carry the tenant context and deep-link to the correct tenant, not the last-used one.

Open decision: do we support multi-tab multi-tenant (Blue Fork in one browser tab, Red Fork in another)? I think yes, and it means tenant lives in the URL, not in a cookie.

2.4 Subscription lifecycle
What's included: trial → active → past_due → suspended → cancelled → expired, plus upgrades, downgrades, and overrides.

Workflow: Every transition is either automated (payment succeeded, trial ended, dunning failed) or manual (super admin override) — but they use different code paths. The state is visible everywhere: banner on the dashboard, badge on the super admin tenant list, block on new resource creation when suspended. Transition timing matters: a downgrade mid-period keeps current entitlements until period end; an upgrade takes effect immediately with prorated billing.

Open decision: the grace period length between past_due and suspended. My proposal: 7 days of retries, then suspend. But for a restaurant, suspending mid-dinner-service is a business-ending event. Perhaps suspend writes but keep reads and customer QR working for 24 hours — a last-ditch "please call us" window.

2.5 Entitlements
What's included: the mechanism that translates a plan into enforced limits and feature flags.

Workflow: Every plan defines a set of entitlement keys. Every enforcement point (creating a branch, inviting a staff member, creating an order, accessing inventory) checks the tenant's effective entitlement before proceeding. If allowed, proceed; if blocked, return ENTITLEMENT_EXCEEDED with a structured error that the UI turns into an upgrade prompt.

Key design principle: entitlements are enforced server-side at mutation time, never at read time, and never in the client. Blocking reads is user-hostile. Blocking at submit after the user filled out a form is even worse — the client should disable the button and show the reason before the user starts.

Open decision: are order counts hard-blocked or soft-overage? I argued earlier for soft (overage billing or auto-upgrade), because blocking a restaurant's dinner service is a support catastrophe.

2.6 Audit & observability
What's included: every meaningful action logged with who, what, when, and context. Two audit trails: tenant audit_logs (for operational and financial actions within a tenant) and platform_audit_logs (for super admin actions affecting tenants).

Workflow: Audit writes happen in the same transaction as the action they describe. If the transaction rolls back, so does the audit entry — no phantom entries. Every audit entry is immutable. Tenants can view their own audit log through the dashboard (owner/manager). Platform admins can view the platform audit log through the super admin. Never does a tenant see another tenant's audit log; never does a tenant see platform audit entries that reference them (unless the action is a user-visible action like an impersonation notice, which is communicated separately).

3. Customer Ordering features
Smallest surface, highest stakes. Every one of these must work on a mid-range Android over flaky Wi-Fi.

3.1 QR entry
What's included: the first 2 seconds of the diner's experience. Scan the QR, land on the menu.

Workflow: QR encodes a URL like https://blue-fork.platform.com/t/{qrToken}. On load, the app validates the token, establishes a short-lived session, and shows the menu. Failure modes must be gentle — the QR was replaced, the restaurant is inactive, the token is expired. Each gets its own screen with an actionable message, not a generic error. A copied/shared QR from another table still works (same table, same session) — that's actually fine; the staff approval gate protects against abuse.

Open decision: does the QR itself expire, or does only the session expire? I think QR is permanent (rotatable by the restaurant, not time-limited), and session is short (30 minutes). Permanent QR is more user-friendly; the session expiry handles privacy.

3.2 Menu browsing
What's included: categories, items, images, descriptions, prices, options, availability. The menu the diner sees is tenant-wide definition merged with branch-level overrides — so Blue Fork's branch 2 might show a different price or hide an item entirely.

Workflow: The menu is fetched once on session start, cached, and refreshed when the diner comes back to the app. If an item becomes unavailable mid-session (staff marked it unavailable), it's visually flagged on next interaction, and the cart blocks submission for that item. Never is a diner allowed to submit an order for an unavailable item — the server validates this again.

3.3 Cart & order submission
What's included: add items with options, edit quantity, remove, add notes, submit.

Workflow: The cart lives client-side until submission. Prices in the cart are estimates (the diner sees current menu prices); the final prices are server-computed on submit. If a price changed since the diner added the item to the cart, the server returns a PRICE_CHANGED error with new totals, and the diner must confirm the new price before proceeding. This is important — silently charging a different price destroys trust.

On submit, the order becomes pending_confirmation — it is not yet a kitchen order. The diner sees "Your order is with the restaurant — we'll confirm shortly." The staff confirms it, after which it becomes a real order in the kitchen. This staff confirmation is non-negotiable — it's the anti-abuse layer and the anti-mistake layer.

Open decision: does the diner get to submit multiple orders per visit (adding courses, drinks later), or is it one order per session? I lean multiple orders per session (real diners order appetizers, then mains, then dessert), but this means the "bill" accumulates across orders and needs to be clear in the UI.

3.4 Order tracking
What's included: the diner watching their order progress: submitted → awaiting confirmation → accepted → preparing → ready → served.

Workflow: Real-time updates (SSE), with polling fallback. Each status transition is triggered by staff action or kitchen action, never by the diner. Rejected orders show the reason. No status is ever shown to the diner before it's true on the server — the UI must never fake "preparing" for a pending order.

3.5 Waiter request
What's included: the diner can ask for a waiter without flagging one down.

Workflow: Diner taps "Request a waiter" → a request appears in the branch's waiter queue → a waiter claims it → the diner sees "A waiter is on the way." If no waiter claims within X seconds, the request escalates (to the floor manager, then to a broader pool). If still unclaimed after Y seconds, the diner sees an honest message: "We're experiencing a delay — please flag down a staff member."

Key design point: the workflow must include claiming and acknowledgment. A silent button that fires into a void is worse than no button at all.

3.6 Bill & payment
What's included: the diner viewing their bill, paying online if enabled, or flagging they'll pay at the counter.

Workflow: The bill aggregates all orders in the dining session. Diner taps "View bill" → sees itemized bill + totals. If online payment is enabled and the tenant's plan supports it, a "Pay now" button appears. The diner completes payment in the gateway's hosted checkout, returns to the platform, and sees "Verifying payment…" until the backend confirms. Never is payment considered complete from the browser alone.

Open decision: is online payment available always (pay when you order) or only at bill time? I strongly recommend at bill time for the pilot — pay-per-item-on-order is a much more complex workflow for restaurants to accept.

4. Restaurant dashboard features
The operational heart. Most of these are recognizable from single-tenant POS systems, but each is subtly changed by multi-tenancy and by multi-branch.

4.1 Branch management
What's included: creating branches, editing them, archiving them, and switching between them.

Workflow: A branch is created by a tenant owner or manager with branch.manage. Each branch has its own timezone, currency, tax settings, service charge, and receipt configuration. Branches cannot be deleted while they have open sessions or unsettled bills — archive them instead. Archiving disables new sessions but preserves historical data.

Key workflow question: does a manager configure branches from a central "settings" screen, or is each branch a separate context they enter? I lean one dashboard, branch selector at the top — otherwise managers who work across branches will do a lot of navigating.

4.2 Menu management
What's included: categories, items, options, images, prices, availability — with branch-level overrides for price and availability.

Workflow: Items are created at tenant level. Each branch can:

Override price (Blue Fork's branch 2 charges 10% more during tourist season).

Toggle availability (Blue Fork's branch 1 is out of salmon today).

Hide the item entirely.

The default state is inherit: new items appear on all branches until a branch overrides. When the tenant-level item's description is updated, branches that didn't override it see the change. When price changes at tenant level, branches that did override keep their override — otherwise every branch-local price change would be silently overwritten.

Publishing: menu changes go through a "publish" action before becoming visible to the customer. Draft state lets a manager prep tomorrow's menu without breaking today's.

Open decision: do we allow scheduled menus (breakfast/lunch/dinner) in the pilot? I'd say no — defer to Phase 2 of the product. It complicates every workflow.

4.3 Tables & dining sessions
What's included: tables per branch, opening a dining session, viewing what's happening, closing when settled.

Workflow: A table has one active dining session at a time. Opening a session happens when the waiter seats a party (or automatically, when the first QR order is accepted — need to decide). All orders during that visit attach to the session. Bills also attach to the session, so a party can have 3 orders and 1 bill. Closing the session requires the bill to be settled (or requires a manager override with a reason).

Key workflow question: does the session auto-close when the bill is paid, or does the waiter explicitly close it? I lean explicit close with a prompt — the waiter knows the guests are gone; the payment alone doesn't tell us that.

4.4 Waiter ordering
What's included: the waiter interface for creating orders, adding items, submitting to the kitchen.

Workflow: Waiter selects a table (or opens one), browses menu, adds items, submits. Waiter orders are immediately accepted — the waiter is the confirmation. Kitchen tickets are created synchronously. Waiter can amend an order after it's been accepted; amendments create new items and cancel removed items (never delete). Kitchen is notified of the amendment.

The subtle workflow: what happens when a waiter wants to add a dish to an order after the kitchen has already started preparing the original dishes? The safe behavior is a separate amendment, not a mutation — the kitchen sees "ADDITIONAL ITEMS" on the ticket, not "modified items."

4.5 QR order review
What's included: the queue of QR orders awaiting staff confirmation.

Workflow: Every QR order lands in a queue visible to waiters (with order.accept_qr permission). The queue shows: table, items, submission time (color-coded by age), total estimate. Staff can Accept, Reject (with reason), or Open (to view details and then accept/reject).

Anti-bottleneck workflows:

Age-color coding: green under 1 minute, amber 1-3 minutes, red over 3 minutes.

Browser/mobile notification when a new pending order arrives.

Optional audible alert on the kitchen display.

Assignment: either a shared queue (any waiter can accept) or claimed by a specific waiter. I'd go shared for simplicity, with the accepting waiter's name recorded.

Open decision: what happens if no one accepts within X minutes? Auto-reject? Auto-accept? Just escalate? My instinct: escalate to manager, never auto-reject. Rejecting a diner's order because staff were busy is the worst possible failure mode.

4.6 Kitchen operations
What's included: the kitchen display, ticket management, preparation status.

Workflow: When an order is accepted (waiter or QR), kitchen tickets are created — one per station per order (if stations are configured), one per order otherwise. The kitchen sees tickets in New, Preparing, Ready. Each transition is a tap. "Ready" notifies the waiter. Delayed tickets are visually flagged and float to the top.

Open decision: do kitchens have stations in the pilot? My recommendation: no stations initially — single kitchen view — but design the schema to support stations. Most small-to-medium restaurants have one or two stations; complexity isn't justified until multi-station tenants exist.

4.7 Billing & cashier
What's included: viewing open bills, recording payments, closing bills, printing receipts, applying discounts, voiding items.

Workflow: A bill is auto-generated per dining session as orders accumulate. The cashier sees open bills, can open one, record payments (cash, card terminal), close when settled. Discounts and voids require permission and are logged. A bill can have multiple payments (split bill), but split-bill UI is deferred — only multiple payment entries, not fancy splitting.

Key workflow question: does the bill auto-generate the moment the first order is placed, or only when the diner/cashier asks for it? I lean auto-generate at first order — the bill exists from the start, so partial-payment and pre-payment workflows work naturally.

4.8 Online payment
What's included: initiating online payment, webhook handling, reconciliation, refunds.

Workflow: When the diner initiates payment on the customer app, the backend creates a gateway intent. Diner completes hosted checkout. Gateway webhook arrives, backend updates the payment. Cashier's bill view updates in real-time. Failed payments show as failed with retry option. Refunds are initiated from the cashier (or super admin for platform billing) and are idempotent — a double-click on "refund" doesn't send two refunds.

Key workflow question: when the diner pays online, does the bill close automatically, or does the cashier need to manually close it? I lean auto-close when full amount is paid — otherwise staff are doing unnecessary work. But if the workflow ever needs "the diner must confirm the amount at the cashier" (some tax jurisdictions require this), the auto-close rule changes.

4.9 Staff & permissions
What's included: inviting staff, assigning roles, per-branch scoping.

Workflow: A manager invites by email → invite email sent → the invitee sets a password → they're a member of the tenant with the assigned role and branches. Changing a role takes effect immediately (tokens are version-bumped). Removing a user archives their membership — historical data (orders they took, payments they recorded) remains attributed to them. Audit log entries from before removal stay intact.

Key workflow question: can a manager create custom roles, or only use the five seeded roles? I lean seeded roles only in the pilot — custom roles are a lot of UX surface for a feature most small restaurants won't use.

4.10 Inventory & purchasing
What's included: ingredients, suppliers, purchases, stock movements, waste, counts, recipes.

Workflow: Inventory is per-branch. Each ingredient tracks current quantity. Purchases add stock. Usage (from sales via recipes) deducts stock. Waste and adjustments are explicit movements with reasons. Stock counts reconcile the ledger with reality and produce discrepancy reports.

Staged approach: Start with manual stock tracking (adjustments, purchases, waste) and defer automatic deduction via recipes until the tenant has reliable recipes defined. Recipe-based deduction is a rabbit hole of edge cases (cancelled dishes, returns, portion size variation) and produces false confidence if the underlying data isn't clean.

Open decision: should inventory be included in the base plan or an add-on? My take: add-on — many small restaurants don't need it, and those who do will pay for it.

4.11 Reports & end-of-day
What's included: daily sales, payment totals, cancellations, refunds, order times, staff activity, end-of-day reconciliation.

Workflow: Reports are per branch by default, with tenant-wide rollup for owners. End-of-day is per branch — the cashier runs it at closing, sees expected cash vs recorded payments, records any discrepancy, and closes the business day. This is an auditable action.

Key workflow question: what does "closing the business day" actually prevent? My proposal: it snapshots reports for that day and locks them from later edits. Late-arriving payments or refunds show up in the next day's report, with a cross-reference to the original day. This is how accounting works in real restaurants.

4.12 Settings
What's included: tenant profile, branch profiles, tax rules, receipt templates, payment configuration, QR generation/rotation, notifications preferences.

Workflow: All settings changes are audited. Sensitive settings (tax mode, payment gateway configuration) require settings.manage and generate an audit entry that's visible to the owner. Rotating a table's QR immediately invalidates the old QR — the diner with the old QR sees "This QR code has been replaced."

5. Super admin features
Smaller surface, but each feature has huge blast radius. Everything here is "powerful, therefore dangerous."

5.1 Tenant management
What's included: list, search, filter, view detail, suspend, reactivate, force-logout sessions, view recent audit.

Workflow: Support agent searches for a tenant, opens its detail page. Sees status, plan, subscription, branches, user count, usage this month, recent audit actions, recent invoices. Can suspend (with reason, sends email to tenant owner), reactivate (with reason), force-logout all users (with reason).

No tenant data editing. Support can view and reference; edits to operational data are the tenant's own responsibility through their dashboard.

5.2 Plan & subscription management
What's included: creating plans, editing entitlements, viewing subscription states across tenants, overriding plans for specific tenants.

Workflow: Plans are created once at platform level. Editing a plan affects all tenants on that plan immediately — so this is a sensitive action requiring superadmin role and a reason. Subscription overrides (e.g. giving a tenant a higher order limit for a month) are recorded per tenant with an expiry date.

5.3 Platform analytics
What's included: aggregate metrics about tenants, revenue, growth, usage.

Workflow: Read-only. No actions. Reads from a separate analytics store or aggregated views — never queries production operational tables directly for heavy aggregation.

5.4 Platform billing
What's included: invoice list, invoice detail, refund, credit, retry failed payment.

Workflow: Every action logs to platform_audit_logs, sends the tenant owner a notification. Never does a billing action happen silently.

5.5 Platform audit
What's included: the super admin's own audit trail — who did what on which tenant when.

Workflow: Every state-changing platform action writes here. Immutable. Separately searchable from tenant audit.

5.6 Admin & feature flag management
What's included: creating/removing platform admins, role assignment, feature flags.

Workflow: Only superadmin role can manage admins. New admins require explicit approval by another admin. Feature flags can enable gradual rollout of new features to specific tenants.

6. Cross-cutting workflow concerns
Some features aren't apps, they're workflow properties that must be right in every app.

6.1 Notifications
Every notification has a target tenant + branch context and deep-links to the right place.

Push notifications on mobile, in-app notifications on web, both always available in a "Notifications center" — never only push.

Never trust a push notification as the sole source of truth; the app always refetches on open.

6.2 Error surfacing
Every error has a code, and the UI switches on the code, not the message.

Codes like TENANT_SUSPENDED, ENTITLEMENT_EXCEEDED, ORDER_ITEM_UNAVAILABLE, PRICE_CHANGED each get a specific workflow — a specific screen, a specific next action.

Generic "Something went wrong" is a last resort, never a default.

6.3 Offline & connectivity
Every app must degrade honestly. Show offline banner, block mutations, show "unknown result" on timeout.

Never auto-retry mutations without user action.

Every real-time screen has a polling fallback.

6.4 Data export & deletion
Tenants can export their data (per plan). Exports are audited and rate-limited.

Tenant deletion is a multi-step process: request → grace period → export offered → confirmation → cascade soft-delete → PII erasure → records preserved per retention policy.

6.5 Tenant suspension mid-service
This is the workflow that needs the most care. When a tenant is suspended:

Existing dining sessions can complete — a bill opened before suspension can still be paid and closed.

New sessions cannot start.

New orders cannot be created.

Customer QR shows "temporarily unavailable" for new sessions.

This is friendlier than hard cut-off, and gives the tenant a chance to fix billing without losing customers mid-meal.

7. Feature dependencies and build order
Not all features are equal. Here's the dependency graph:

Must exist first (nobody can operate without these):

Identity & membership

Tenant provisioning (at least manual)

Tables, menu, orders, kitchen, bills, payments (the operational core)

Tenant switching (if any user belongs to 2+ tenants)

Required for a functioning SaaS:

Subscriptions & entitlements

Super admin (at least basic tenant management)

Audit

Required for a good SaaS:

Branch model (if the first tenant has multiple locations)

Menu overrides per branch

Staff & permissions

Reports

Nice to have, defer:

Inventory & purchasing

Waiter request

Scheduled menus

Split bills

Custom roles

Impersonation

Deferred entirely:

Per-tenant custom domains

Multi-region

API keys for tenants

White-labeled staff app

8. The seven decisions I'd still want to settle
From my previous message, plus the new ones that surfaced here:

Identity model — one global account or per-tenant accounts? (My strong preference: one global account.)

Order entitlement behavior — hard-block or soft-overage at the order limit? (I lean soft.)

Trial state — does trial expire hard, or does it gracefully degrade? (Graceful is friendlier.)

Customer URL scheme — subdomain-per-tenant or path prefix? (Subdomain.)

Staff billing unit — per account, per membership, or per active-this-month? (Per active membership.)

QR payment timing — pay-per-order, pay-at-bill, or both? (Pay-at-bill only for pilot.)

Branch count for the first tenant — will the pilot restaurant actually be a multi-branch tenant, or is it single-branch? This changes whether Phase 3 ships before or after onboarding.


2. Feature-by-feature in multi-tenant context
2.1 Serving workflow (kitchen → READY → waiter → SERVED → auto-COMPLETE)
What stays: The state machine, the permission split (kitchen.update vs orders.serve), the auto-complete-on-last-item rule, the audit trail (actor_user_id, actor_membership_id, completed_at).

What changes:

orders.serve is now branch-scoped. A waiter belongs to a branch; they can only serve items belonging to their branch. A waiter belonging to Branch A sees Branch B's READY items as nonexistent in their view — not as "access denied," because that would leak existence.

The audit entry gains branch_id alongside tenant_id and membership_id. The question "who served this dish" becomes answerable at the branch level, and rollup reports at the tenant level can aggregate across branches without conflation.

The "kitchen stops at READY" rule is per branch. Each branch has its own kitchen workflow, and a READY item in Branch A doesn't affect Branch B's queue.

Workflow questions this raises:

Does a regional manager have orders.serve across all branches? My take: no. They have orders.serve within the branches they're a member of, which could be all of them, but the permission check still passes through the branch scoping. This keeps the workflow consistent — the manager is acting as a staff member in a specific branch, not as an override.

When a waiter is mid-shift on Branch A and Branch B needs help — how does that work in the workflow? I think the correct pattern is: the waiter can't spontaneously pick up Branch B's tickets. If the tenant needs cross-branch coverage, that's a scheduling concern (shift management) not a serving concern. The workflow should be: only members of a branch see and serve that branch's items.

2.2 Multiple orders → single consolidated bill
What stays: This pattern is the right one and survives untouched. DiningSession is per table, multiple orders attach to it, issue_bill consolidates all orders for the session into one bill.

What changes:

DiningSession becomes a branch-level entity. It's linked to a branch (which is linked to a tenant). The table belongs to a branch. The session carries tenant_id and branch_id for scoping.

issue_bill continues to work as-is, but its query must filter by branch_id as well as dining_session_id — because in a shared database, two tenants could theoretically have a dining_session_id that collides only if UUIDs weren't unique (they are), but adding branch_id to the WHERE clause is a defense-in-depth habit that catches un-scoped queries early.

The cashier's "all open bills" view becomes per branch by default. A tenant-wide owner can see a rollup grouped by branch, but the default view is scoped.

Workflow question this raises:

What does the bill look like to a diner who ordered from table 5 across 3 orders? The diner sees one bill, consolidating all orders. This is already the behavior when the last item completes and the bill auto-surfaces — good. But the diner's "order history" view should still show the 3 orders separately (because each had its own lifecycle), even though the bill consolidates. Two views, one truth.

2.3 Call-waiter / service calls
What stays: The two kinds (GUEST from QR, KITCHEN from the kitchen screen), the shared acknowledge workflow, the audit trail.

What changes:

Every service call record needs tenant_id and branch_id. A guest call from Branch A's table 3 goes to Branch A's waiter queue, not the tenant-wide queue.

The acknowledge workflow needs branch scoping — a waiter on Branch A shouldn't be able to acknowledge Branch B's calls.

Regional managers and owners see rollup: pending calls across all branches they're a member of, grouped by branch. This is a manager-view feature, not an operational one — they don't acknowledge from the rollup, they drill into a branch to acknowledge.

Polling has to become real-time in a multi-tenant context. At 5 seconds polling with one branch, it's fine. With 10 branches each producing events, the backend load grows linearly with branches and polling starts missing the SLA. This is on your "remaining work" list as medium priority — in multi-tenant it becomes high.

The escalation workflow from my previous discussion (escalate if no one claims within X seconds) becomes more important in multi-tenant because branch-ownership matters. If Branch A's waiters are all busy, does the call escalate to Branch B? No. It escalates to Branch A's manager, then to Branch A's owner, then surfaces as "unacknowledged" to the tenant-wide manager rollup. Cross-branch routing never happens.

Workflow question this raises:

Does the KITCHEN service call get seen by waiters on other branches? No — kitchen calls "food ready, come serve" means waiters on that branch. The regional manager might see the aggregate but doesn't act on individual calls.

2.4 Concurrent serving / multi-waiter race conditions
What stays: The idempotent "second press is harmless" behavior, the atomic transitions, the audit traceability.

What changes:

The idempotency is now per branch. Two waiters on the same branch racing is handled the same way as today. Two waiters on different branches can't race on the same item, because the item is branch-scoped.

The "who completed the order" traceability gains branch_id, which is useful for cross-branch reporting ("how many orders does each branch complete per hour?").

No workflow change here — this one is genuinely unchanged by multi-tenancy. It's one of the nice properties of branch-scoped entities.

2.5 Permission system (the 5 roles and their split)
What stays: The role definitions, the permission codes, the require_permission pattern, the 404-not-403 policy.

What changes:

require_permission gains a branch_scoped parameter (or a target-resource-based branch check). The permission check resolves: (user is member of tenant) AND (user has permission for role) AND (user is member of branch OR user has tenant-wide role) AND (resource is in a branch the user belongs to).

Roles stay the same five (owner, manager, waiter, kitchen, cashier). No new roles are needed for multi-tenant — that's a strong signal your permission model was well-designed.

A new "tenant-level" concept emerges: a user with owner role is owner in a specific tenant. They may be manager in another tenant. The role is per-membership, not per-user. Your existing membership_id in audit logs already handles this correctly.

Permission versioning — when roles change, tokens are invalidated. You don't currently have pv (permission version) in your tokens per your plan, but for SaaS you will need it. Otherwise a demoted waiter's open session keeps working for up to 15 minutes.

Workflow question this raises:

What happens to a waiter's in-flight session when their role changes mid-shift? Options: (a) next request fails with "permissions changed," (b) session gracefully ends with an alert, (c) token is refreshed and they continue with new permissions. My recommendation is (b) — a demotion mid-shift usually means something serious, and the workflow should acknowledge that rather than silently change their capabilities. A promotion is more forgiving (c) is fine.

2.6 Demo accounts
What stays: The concept, the kill-switch, the role-based demo cards.

What changes — significantly:

The current demo pattern is a single restaurant with demo users. In multi-tenant SaaS, demo accounts need rethinking:

Option A — Demo tenant. A single shared tenant (demo slug) with seeded data (Harbor Table-style restaurant with one branch). Demo users log in with a pre-configured demo account. Guest access via demo.platform.com/t/{token}. Rotates data nightly. This is my recommendation.

Option B — Per-tenant demo mode. Each new tenant can seed a demo branch inside their own tenant. Not great — mixes real and fake data.

Option C — No demo. Demo only on the marketing site as a video or guided tour. Loses the interactive "try it now" value.

Under Option A:

The DEMO_ACCOUNTS env flag moves to a platform-level flag ("demo tenant enabled"), not a per-app flag.

The demo tenant must be isolated the same way real tenants are — RLS applies, isolation tests run against it. Otherwise the demo tenant becomes a security hole.

The demo tenant should have no subscription and no billing; or a special "demo" plan with unlimited entitlements.

Demo data resets via a nightly job — the tenant is never suspended, never billed.

The marketing "Try it now" flow becomes: click → you're in the demo tenant → you can try every role (login chips) → you see the workflow end-to-end → an "Upgrade to a real account" CTA when you want to use it for real.

Workflow decision: does the demo tenant share a database with production tenants? Yes — it must, because the isolation model is the same. But it's marked as is_demo = true in the tenant record, and the platform analytics exclude demo tenants from revenue/usage metrics.

2.7 Branding (VITE_BRAND_NAME)
What stays: The env-driven pattern is fine.

What changes:

VITE_BRAND_NAME becomes the platform brand (e.g., "HarborOS", "TablePro"), not the restaurant brand. It appears on the marketing site, super admin app, and the staff dashboard chrome.

Restaurant branding comes from the tenant record — tenant.display_name and per-branch overrides. The customer app shows the tenant brand; the staff dashboard shows the tenant name in the header (e.g., "Blue Fork — Manager dashboard").

The platform brand and tenant brand are different things, and the env var should reflect that.

Workflow question: is there any surface where the platform brand shows on a customer-facing view? My take: only in the footer ("Powered by HarborOS") — the customer should perceive the restaurant, not the platform. This is a product decision but worth settling early.

2.8 Production bootstrap
What stays: Fail-fast on missing env, idempotent bootstrap.

What changes — significantly:

Your current bootstrap creates the first restaurant and its owner. In SaaS, this is the wrong shape. The bootstrap should:

Create the first platform admin (superadmin role), not a restaurant.

Use BOOTSTRAP_PLATFORM_ADMIN_EMAIL + password env vars.

Never create a tenant. The first tenant comes through the tenant registration flow, not the bootstrap.

Optionally seed the default plans (Starter / Growth / Scale) — this is fixed platform configuration, so seeding it is safe and desirable.

Why this matters: if bootstrap creates a restaurant, then the first restaurant is special — bypassing the registration flow, the plan assignment, the audit trail. Every subsequent restaurant has to go through the registration flow, and the first doesn't. That's an inconsistency waiting to bite you. Every tenant, including the pilot, should enter through the same door.

Second change: the bootstrap also seeds the demo tenant (if enabled) with its demo data. This is the only seed allowed to create demo content, and it's guarded by the same demo flag.

Workflow decision: does the first tenant get a trial subscription, or does it get a "founding customer" plan with custom entitlements? I'd suggest: trial by default, then you override the plan for the pilot restaurant after the trial ends. This keeps the workflow consistent for everyone.

2.9 Idempotency keys
What stays: The mechanism, the 8-character minimum, the 409-on-different-body behavior.

What changes:

Idempotency keys are currently scoped per restaurant_id. In multi-tenant with branches, they should be scoped per (branch_id, scope, key), because an order is branch-level.

The idempotency_keys table gains tenant_id and branch_id; the unique constraint becomes (branch_id, scope, key). A key from Branch A can't replay into Branch B.

Cross-tenant replay is already impossible (different UUIDs would be needed), but the table-level constraint makes it explicit.

No workflow change — the mechanism works identically. Just the scoping constraint changes.

2.10 Tenant scope (restaurant_id)
What stays: The scoping discipline, the 404-not-403 policy.

What changes:

restaurant_id becomes tenant_id plus branch_id. Every operational table gains branch_id.

Some tables become tenant-only (no branch): user accounts (identity is global), tenants, plans, subscriptions, permissions, platform_admins.

Some tables become tenant + branch (both columns): orders, bills, payments, tables, dining sessions, kitchen tickets, service calls, menu item availability overrides.

Some tables become tenant-level with optional branch (branch_id nullable = tenant-wide, set = branch-specific): menu_items, menu_categories. The availability override table is separate and always branch-scoped.

restaurant_id becomes a deprecated alias for tenant_id during the migration, then is dropped.

This is the single biggest change — every table, every query, every permission check touches it. But it's mechanical and well-understood.

3. How your existing features enable SaaS workflows
Some things you've built are more valuable in SaaS than they might seem:

Your service-call queue is a general-purpose "staff attention" primitive. In multi-tenant it becomes: guest calls (branch-scoped), kitchen calls (branch-scoped), payment failures (branch-scoped), entitlement warnings (tenant-scoped), subscription alerts (tenant-scoped). One queue, multiple event types, each with its own routing. This is much cleaner than building separate notification systems per feature.

Your DiningSession abstraction is what makes single-bill consolidation work — and it also makes session-scoped analytics possible. "How many sessions did Branch A have today?" is a query, not a computation. This will be a core reporting primitive.

Your audit trail with actor_membership_id already distinguishes "which user" from "which membership." When a user belongs to two tenants, this is exactly what's needed for the "who did this in which tenant" question — no schema change needed, just add branch_id.

Your "kitchen stops at READY" design means the bill only auto-surfaces at COMPLETED (last item served). This is user-friendly (diner sees the bill only when all food is served) and operationally correct (no bill before food is done). It also means the workflow naturally prevents "bill before food" which is a frequent operational complaint in other systems.

4. New workflows your features enable in SaaS
These aren't in your current build but become natural extensions:

4.1 Branch coverage workflow. Your kitchen and waiter screens are single-instance per restaurant. In multi-tenant, they're per branch. This enables: a regional manager watching all branches' kitchen boards in a grid, comparing load, seeing which branch is behind. This is a manager-view feature you'd build once and it's high-value for multi-branch tenants.

4.2 Tenant onboarding with demo data. Your demo tenant seeds data (tables, menu items, users). The same seed pattern can be used to pre-populate a new tenant's sandbox — "Do you want to try the system with sample data before you build your real menu?" This reduces time-to-first-order.

4.3 Consolidated reporting via sessions. Because DiningSession is the session abstraction and bills consolidate at session level, reports become simple: sessions per day, average ticket per session, items per session, session duration. This is the natural unit of reporting and it's already in your model.

4.4 Multi-branch owner as a product tier. Because you have branches, the "owner" dashboard becomes a distinct product experience — not just a permission, but a different information architecture. The regional owner doesn't need to see table 3's order history; they need to see "Branch A vs Branch B revenue, last 7 days." This is a real product differentiator.

5. The things that will actually hurt during migration
Being honest about the friction points:

5.1 restaurant_id → tenant_id + branch_id touches every table. There's no shortcut. Every operational table, every query, every index. You can do it in stages (add nullable, dual-write, switch reads, enforce NOT NULL, drop old), but it's real work. Budget 2–3 weeks for the pilot if you do it carefully. The good news is your schema discipline means the code changes are mechanical, not creative.

5.2 Bootstrap changes. The current shape (bootstrap creates restaurant) inverts in SaaS (bootstrap creates platform admin, restaurant comes via registration). This isn't hard to code but it changes your startup behavior and you'll need to test both paths carefully.

5.3 Demo tenant isolation. The demo tenant must go through the same isolation tests as a real tenant, must be markable as is_demo, must be excluded from platform analytics, must rotate data. It's more work than "just seed another restaurant" because the demo tenant touches the whole stack (RLS, entitlements, billing exclusion).

5.4 Service calls need branch routing. The existing "shared queue" pattern becomes "branch-scoped queue" — small code change, but the routing rules for escalation (branch waiter → branch manager → tenant manager → owner) are new. Don't underestimate the escalation workflow — it's the difference between a service call that gets handled and one that gets ignored.

5.5 Polling → real-time. You've marked this as "Medium" in your remaining-work list. In multi-tenant it becomes "High." Every service call, every kitchen status, every bill update should be pushed, not polled. Otherwise the polling load scales with (tenants × branches × staff concurrent) which is super-linear.

5.6 Outbox worker. You noted that outbox events are recorded but the worker may not be running. In SaaS, the outbox must be running — it's the delivery guarantee for WS events, notifications, receipts, and reconciliation. Ship this before onboarding the second tenant.

6. Revised priority of your "Remaining Work" list
Mapping your existing list against SaaS priorities:

Your item	Current priority	SaaS priority	Why
Multiple kitchens per restaurant	Low	High (becomes "kitchen per branch, stations per branch")	Every branch needs its own kitchen board
Web waiter SERVED buttons	Medium	High	Staff may be desk-based; mobile-only is a blocker
Kitchen role-gating for SERVED	Low	Medium	The split is correct; just needs UI consistency
Real-time notifications	Medium	High	Polling doesn't scale past a handful of branches
Combined bill view for guest	Low	Resolved — your auto-complete workflow already shows one bill per session at COMPLETED	May need "order history + consolidated bill" two views
Payment reconciliation dashboard	Low	High	Online payments demand it; a mismatch is money lost
Outbox worker	Medium	Critical	Without it, delivery guarantees are lost
New items to add to your remaining work (from the SaaS conversation):

Item	Priority	Why
Tenant/branch split (restaurant_id → tenant_id + branch_id)	Critical	Foundation
Tenant registration + onboarding wizard	High	No SaaS without it
Subscription + entitlements	High	No revenue without it
Super admin app	High	No operations without it
Branch-scoped service calls + escalation	High	Core workflow
Tenant switching UX	High (if any user has 2+ tenants)	Real for pilot
Platform bootstrap (superadmin, not restaurant)	High	First deploy needs it
Demo tenant (isolated, marked, rotated)	Medium	Marketing value
Permission versioning (pv in tokens)	High	Demoted users must lose access immediately
RLS enablement	Medium (Stage 4)	Defense-in-depth
7. The workflows that change shape, not just scope
Most features just get branch-scoped. A few genuinely change their workflow:

7.1 Login. Old: login → dashboard. New: login → if 1 tenant, dashboard; if 2+, tenant picker; picker remembers last choice; tenant switch clears all state and reconnects.

7.2 Demo experience. Old: demo users with VITE_DEMO_ACCOUNTS. New: demo tenant, accessible via marketing flow, isolated from real tenants, marked and rotated.

7.3 Bootstrap. Old: startup creates owner + restaurant. New: startup creates platform admin + default plans (+ optionally demo tenant). First restaurant comes through registration.

7.4 Permission checks. Old: role → permissions → allow/deny. New: role → permissions → resource's branch → user's branch membership → allow/deny. Three-layer check on every request.

7.5 Billing. Old: cashier issues bill, records payment, closes session. New: same, but per branch, and the tenant-wide owner sees branch rollups. Additionally, platform billing is entirely new — the SaaS bills the tenant, separately from the tenant billing the diner.

7.6 Service calls. Old: shared queue, any staff acknowledges. New: branch-scoped queue, branch members acknowledge, escalation to branch manager → tenant owner → unacknowledged rollup. Cross-branch routing never happens.

8. Decisions this material surfaces
Combined with the earlier list, these are the decisions that matter most now that we know what's built:

Is the pilot restaurant single-branch or multi-branch? If single-branch, you can defer Phase 3 (branch model) but the schema change still happens. If multi-branch, branches ship with the pilot.

Does the demo tenant share a database with production tenants, or is it isolated by deployment? I recommend shared (isolation tests prove it's safe) — otherwise you maintain two database schemas.

Does the bootstrap still create an owner account, or a platform admin? I recommend platform admin; the first restaurant comes through registration.

Does a user's role change mid-shift log them out, or gracefully downgrade? My recommendation: log out with a clear message — a role change mid-shift is meaningful.

Is the waiter request escalation a separate workflow, or part of service calls? I recommend separate — service calls are "notify staff of something," waiter requests are "specific request with expected acknowledgment." Different SLAs, different routing.

Does the tenant-wide owner have operational permissions (serve, accept QR orders), or only viewing + configuration? My recommendation: only viewing + config. Operational actions require branch membership. This keeps the workflow clean and the audit trail meaningful.

Does platform branding appear on the customer QR page? My recommendation: only in a footer ("Powered by [platform]"), if at all. The customer should see only the restaurant.

Is the outbox worker shipped with the SaaS migration, or separately? I recommend shipping it with Phase 2 (multi-tenant auth), because that's the first phase where reliable event delivery matters.

9. What I'd propose we discuss next
We can take any of these, but the three that seem most consequential for the SaaS shape:

A. The bootstrap and registration workflow. This is the "front door" of the SaaS and we've decided it changes shape. It's worth designing end-to-end — what the first super admin does on day one, what registration looks like for the pilot restaurant, how the demo tenant fits in.

B. The branch model and its workflows. Every operational workflow becomes branch-scoped. Getting branch workflows right (menu overrides, staff membership, per-branch kitchens, per-branch reporting) is the core of the SaaS value prop.

C. The notification and service-call architecture. You have a shared queue; SaaS needs branch-scoped routing plus escalation plus real-time plus a durable outbox. This is the "operational heartbeat" of the product.

My instinct: start with B (branch model), because it determines the shape of A and C. If branches are the fundamental organizing unit, then the bootstrap creates a tenant-with-a-branch, the registration creates a tenant-with-a-branch, the demo tenant has a branch, and notifications route by branch. Get branch right, and the rest follows.

All three — how they interlock, and the workflows that follow
I suggested starting with branches because branches decide everything else. But since you want all three, let me do it in the order that reveals the dependencies: branch first, because it defines the scoping unit. Bootstrap next, because it creates the first branch. Notifications last, because it routes by branch. Then I'll close with the tensions that only surface when you look at all three together.

No code, no architecture — workflows, features, and the decisions that need to be made.

Part 1 — Branch model: the scoping unit that makes everything else work
1.1 The core premise
Once you accept multi-tenancy, the restaurant business is the tenant and each physical location is a branch. Everything operational belongs to a branch. Everything commercial belongs to a tenant. This is the dividing line that makes the rest coherent.

The question isn't whether branches exist — the question is how visible they are to the people using the system. A branch can be:

Invisible — a staff member only ever belongs to one branch and never sees the concept. The UI speaks in the tenant's name.

Implicit — a staff member belongs to multiple branches but the system defaults to their "home" branch; switching is an action, not a prerequisite.

Explicit — a staff member sees a branch picker everywhere; each screen shows "which branch am I in."

These three levels feel very different to the user. The mistake most SaaS products make is choosing one and applying it universally. My recommendation: all three, by role.

Waiter, kitchen, cashier see implicit. They have one home branch. They never see a branch picker unless they're somehow a member of two branches (rare, temporary).

Branch manager sees explicit within their branch. They see the branch name everywhere, and they can configure it.

Regional manager and tenant owner see explicit, with switcher. They see a branch picker everywhere, plus rollup views.

The user's experience of "what is a branch" is determined by their role, not by an architecture decision. This is a workflow decision, not a permission decision.

1.2 The branch creation workflow
A branch is created when a tenant opens a second location. Before that, the tenant has exactly one branch — its first location. This means the tenant always has a "branch," even the very first one. The tenant is never branchless.

Workflow:

Owner or manager with branch.manage clicks "Add branch."

The system checks the tenant's entitlement (branches.limit) before opening the form, not after submission. If the plan allows 1 branch and this is branch 2, the button is disabled with a clear message: "Your Starter plan includes 1 branch. Upgrade to Growth to add more branches."

If allowed, the creation form asks for: name, slug (URL-safe identifier), timezone, currency, tax settings, service charge, receipt config, and optionally a copy of the menu from another branch.

On submit, the branch is created with its own operational space — empty menu (or seeded from another branch), no tables, no staff memberships.

The tenant admin is redirected to the new branch's setup wizard, which is the same flow a new tenant sees after registration: set up tables, set up staff, review menu.

Key workflow decision: does a new branch start empty or seeded from an existing branch? Both are valid; they imply different products.

Empty: branch 2 is born identical to nothing. The admin builds it up. Cleaner, but slower to first order.

Seeded: branch 2 inherits the menu, table layout, staff roles, and settings from branch 1. The admin tweaks. Faster to first order, but risks accidental copy errors (branch 1's "holiday menu" becomes branch 2's default).

My recommendation: seeded by default, with an option to start empty. When someone creates a second branch, they usually want it to behave like the first one. The setup wizard then prompts the admin to review what was inherited. This is the right default and lets the workflow be fast without being irreversible.

1.3 Branch configuration workflow
Every branch has its own operational settings. Some settings are branch-local; some are tenant-wide; some can be either.

Always tenant-wide (not per branch):

Billing details (legal entity name, tax ID, subscription)

Brand identity (logo, primary color)

Plans, entitlements, feature flags

User accounts (identity is global; memberships are per tenant)

Always branch-local:

Physical address and phone

Timezone (branches can be in different timezones)

Currency (unusual but possible — a chain near a border)

Tax rules (a chain in two tax jurisdictions)

Receipt layout (some branches print in a different language)

Tables and floor plan

Kitchen stations and printer routing

Dining session behavior (auto-close rules, waitlist)

Branch-local by default, tenant-override possible:

Menu items and prices

Service charge

Operating hours

Inventory

The workflow question here is where the "inheritance" happens. When a tenant admin changes the tenant-wide setting, which branches change? My recommendation:

Tenant-level setting change → all branches that haven't overridden. A branch that explicitly overrode the setting keeps its override.

A branch that inherits sees a "Inherited from tenant: [value]. Override?" prompt next to every inherited setting.

A branch that overrides sees its own value, plus a note "Overriding tenant default: [value]."

This is the same pattern as Kubernetes' config inheritance, or Shopify's multi-store settings. It works because it's honest — the branch admin always knows whether they're setting a value or inheriting one, and the tenant admin always knows what they're changing.

1.4 Staff membership across branches
This is where the branch model meets identity. A user is a member of a tenant, and within that membership, they're a member of zero or more branches.

Zero branches → they can only see tenant-level things (billing, plans, user management). They cannot see any operational data. This is rare — usually owner-level.

One branch → they're a branch-scoped staff member. Waiter, kitchen, cashier.

All branches → they're a tenant-wide staff member. Regional manager, owner.

Some branches → they're a subset manager. A manager of 2 of 5 branches.

The role-per-branch workflow question: can the same person be a manager in branch 1 and a waiter in branch 2? My take: yes, but it's rare and the workflow is deliberately inconvenient. The settings screen shows per-branch roles. Adding the second role requires a confirmation that reads like "you're giving Alice different roles in different branches — are you sure?" This is a real workflow but the UX should discourage it because it creates audit confusion and permission debugging hell.

The simpler workflow: one role per tenant, applied across all branches the user belongs to. A manager is a manager across all branches they're a member of. This is what most teams actually want, and the multi-role-per-branch case is deferred.

1.5 Branch switching — for the people who actually switch
Only two roles switch branches regularly: regional managers and owners. Everyone else stays put.

For a regional manager, the workflow is:

Login lands them on their last-used branch — usually their home branch.

The header shows [Tenant name] / [Branch name] with a switcher in the branch name.

The switcher shows all branches they're a member of, with quick stats per branch: number of open sessions, pending orders, pending service calls, "behind schedule" indicator.

Clicking a branch fully recontexts the app — every screen now shows that branch's data. In-progress actions (a half-written order, an unsaved form) prompt a confirmation before switching.

The URL includes the branch slug so deep links are unambiguous.

For a waiter or cashier, the workflow is different:

They're a member of one branch. They never see a switcher.

Their login lands them directly in that branch. No choice is required.

If they somehow need to cover another branch temporarily, an admin adds them to that branch's membership. They then see a switcher, but only for the branches they're a member of.

The most important workflow decision here: does switching branches clear all cached state, or preserve it? It must clear everything — every query cache, every store, every open modal. The classic cross-tenant leak in React apps is a UI that reuses stale data because the cache was keyed only by resource ID, not by tenant + branch. This isn't an architecture decision, it's a workflow rule: switching branches resets the app. Design the UX to make this feel natural (a 200ms "loading branch" screen is fine) rather than jarring.

1.6 Branch archival workflow
Branches don't get deleted. They get archived. The workflow:

Owner clicks "Archive branch."

System checks: are there open dining sessions? Are there unsettled bills? Are there scheduled shifts or pending orders?

If yes, the archive is blocked with a clear list of what needs to be resolved first. The owner can choose to close everything themselves (settle bills, close sessions) or ask for an override.

If no blockers, the branch is archived: status = 'archived', all memberships remain, all data preserved.

Archived branches do not appear in the switcher by default; they appear under a "Show archived" toggle.

Archiving is reversible — un-archiving restores the branch to active.

The workflow tension: a branch with settled bills and closed sessions should archive cleanly. A branch that's mid-dinner-service should not. The UX should make the difference visible — list the blockers prominently, then explain what to do about each. This is a workflow where the failure path is more important than the success path.

1.7 What branches enable in the product
Once branches exist as a first-class concept, several product workflows become possible:

Regional dashboards: rollup views by branch, with per-branch drill-down.

Cross-branch operations: transfer a staff member temporarily, share an inventory supplier, transfer stock (with logging).

Multi-branch reporting: "which branch had the highest average ticket this week?" becomes a natural query.

Franchise expansion: the tenant grows from 1 to 10 branches without changing their subscription mechanics (just their entitlement tier).

Per-branch A/B testing: a chain can pilot a menu change at one branch before rolling it out.

These aren't features to build now — they're workflows that become possible, and it's worth knowing they're coming so you don't accidentally design against them.

Part 2 — Bootstrap and registration: the front door
2.1 The bootstrap workflow on day one
The first deploy of the SaaS needs to answer: who logs in first, and what do they see?

My proposal:

Deploy with BOOTSTRAP_PLATFORM_ADMIN_EMAIL + BOOTSTRAP_PLATFORM_ADMIN_PASSWORD in the environment.

On startup, the backend:

If the platform has no admin yet: creates the platform admin from the env vars. Fails fast if env vars are missing.

Seeds the default plans (starter, growth, scale) if they don't exist. Plans are fixed platform configuration, not tenant data, so seeding is safe.

Optionally seeds the demo tenant if DEMO_TENANT_ENABLED=true. This is the only seed allowed to create demo data.

The platform admin logs in at admin.platform.com. No tenant exists yet. The super admin dashboard shows: "No tenants. Register your first tenant or invite a restaurant to sign up."

The first tenant is created via the same registration flow that any future tenant uses — not via a script, not via direct database insert.

This is the key difference from your current bootstrap: bootstrap creates the platform, not the product. Your current bootstrap creates the restaurant; in SaaS, the restaurant creates itself through registration, exactly like every future restaurant.

The workflow question: what if the first deploy needs to migrate the pilot restaurant? The pilot restaurant comes through the same registration flow with a special "migrate existing data" option, which is the migration path we discussed before. The first tenant isn't privileged by bootstrap — it's privileged by migration, which is a separate concern.

2.2 Three registration entry points
Self-serve. Restaurant owner fills out a form on the marketing site: name, email, phone, country. Behind the scenes, the form creates a tenant in pending status, sends a magic link to the email, and the owner completes setup. Fastest path, highest abandonment risk.

Sales-assisted. You talk to the restaurant, they decide to sign up, and you trigger an invite from the super admin (which sends them a magic link). Best for higher-touch customers. Requires the super admin to be functional.

Migrated. Existing pilot restaurant moves onto the platform. A migration script creates the tenant, its users, its data, and sends the owner a "welcome, here's what changed" email. This is the co-development path we discussed earlier.

The workflow question this raises: which of these does the pilot restaurant use? My recommendation: sales-assisted for the pilot (you control the experience end-to-end), and self-serve for the next 5–10 restaurants. Migrated is only for the one existing deployment.

The second workflow question: can the super admin create a tenant on a restaurant's behalf? Yes, but with a distinction: the super admin creates the tenant shell and sends an invite, they don't set up the restaurant's menu, tables, or staff. The restaurant does that themselves. This keeps the ownership clean — the platform registers, the restaurant configures.

2.3 The setup wizard
Once registered, the owner lands on the setup wizard. The wizard is the single most important workflow in the SaaS — it determines whether the restaurant ever reaches value.

The wizard has three tiers of setup:

Tier 1 — required to do anything:

Restaurant name and first branch name

Timezone and currency

Tax mode (included / excluded / none)

Owner's own password (if not already set via magic link)

Tier 2 — required to serve a customer:

At least one table (creates the first QR)

At least one menu category

At least one menu item with a price

At least one staff member invited (or use the owner's own account as staff for testing)

Tier 3 — required to operate at scale:

Full menu (import or manual)

All tables and floor plan

Staff invites with roles

Payment gateway configuration (if online payments are enabled)

Receipt template (if printing)

The wizard workflow is progressive: the owner completes Tier 1 to see their dashboard, then a banner prompts them through Tier 2 items. Tier 3 items are prompted as "recommended" but not blocked. The dashboard works with Tier 1 + Tier 2 complete, minus some features. This is important: a restaurant can go live without configuring everything, and the system never blocks them on completeness.

The setup wizard as a checklist. At any point, the owner can see a checklist: "5 of 8 setup steps complete." Each step is deep-linkable. Incomplete steps are visible but not blocking (except Tier 2 items, which block specific features — e.g., no table means no QR ordering).

The setup wizard abandonment workflow. If the owner starts the wizard and doesn't finish, the tenant is in pending state. After 7 days, an automated email nudges them: "Your trial is waiting — finish setting up to get started." After 30 days, the tenant is soft-archived (data preserved, no logins, no billing). After 90 days, a hard delete workflow begins (with a "recover" option for 7 more days). This is the workflow that prevents half-configured tenants from cluttering the platform.

2.4 Trial entry and conversion
When the tenant is registered, they enter a trial state. The workflow:

Trial is a specific duration (14 or 30 days — configurable per plan). A trial plan exists by default with full features so the restaurant can try everything.

The dashboard shows a persistent banner: "Trial — 23 days left. [Choose a plan]".

All features work. No entitlement limits during trial, or generous limits.

The conversion workflow is triggered either by time (trial ends → convert or lose access) or by usage (they hit the trial limit → prompt to upgrade).

The conversion workflow as a product experience:

7 days before trial ends: email the owner. "Your trial ends in 7 days. Choose a plan to keep your data and continue serving customers."

3 days before: dashboard banner turns amber. "Choose a plan in 3 days to avoid service interruption."

1 day before: dashboard banner turns red. "Trial ends tomorrow."

Trial expires: dashboard is read-only. Customer QR shows "This restaurant is temporarily unavailable." An email says "Trial ended — reactivate to continue."

The workflow question: does the trial expire silently or loudly? My recommendation: loudly, with a 7-day grace period after expiry where the dashboard still works but is clearly read-only and a large banner appears. This prevents the "we didn't know the trial ended" complaint.

The workflow question (arguable): does the restaurant's data survive trial expiry? Yes, always. Deleting a restaurant's menu and order history because they didn't convert is a reputation killer. Data survives for 90 days post-expiry, then enters the deletion workflow.

Part 1 — The honest audit
Discussed and settled
Single-tenant product plan and build plan (pages, features, workflows)

Schema, database rules, backend rules, frontend rules, mobile rules

Feature inventory (four layers: platform, super admin, restaurant dashboard, customer)

Multi-tenant architecture: shared schema + tenant_id + branch_id, RLS deferred to Stage 4

Branch model as the scoping unit

Tenant lifecycle states and transitions

Bootstrap changes (platform admin, not restaurant)

Registration paths (self-serve, sales-assisted, migrated)

Tenant switching workflow

Membership model (one global account, per-tenant memberships)

Service call workflow with escalation

Feature integration of your existing implementation (serving workflow, single bill, service calls, permissions, demo accounts, idempotency, audit, tenant scope)

Migration staging (M1–M6 rolling migration)

Super admin scope and safety (separate realm, separate app, separate auth)

Entitlements enforcement model (server-side, at mutation, not at read)

Security threat model and isolation strategy

Discussed but not fully detailed
Setup wizard — mentioned, but the full workflow (tiers, checklist, abandonment, recovery) was only sketched

Trial conversion — sketched, but the day-by-day email cadence and grace period need design

Subscription lifecycle — states defined, but the operational workflow (upgrades, downgrades, prorating, dunning, invoice generation, tax) is not fully designed

Data export and tenant exit — mentioned, no workflow

Support and incident workflows — mentioned, no escalation tree

Platform analytics — mentioned, no metrics list

Not discussed at all
Staff scheduling and shift management — never touched, but a real staff member will ask for it in week one

Reports and analytics workflow — feature listed, workflow not designed

Inventory in SaaS context — branch-scoped, entitlement-gated, but not detailed

Online payment gateway operations — reconciliation, disputes, chargebacks, gateway-specific flows

Multi-jurisdiction tax — one branch in one tax zone is easy; 5 branches in 3 zones is not

Mobile app store lifecycle — versioning, forced updates, App Store / Play Store review delays

Custom domains for tenants — white-labeling beyond subdomains

API access for tenants — future integrations, webhooks, programmatic access

Data residency — compliance, multi-region, GDPR-style deletion obligations in detail

Onboarding calls and handoff — the human workflow that turns a registered tenant into a paying customer

So the answer is: the architecture, the workflows at the operational level, and the migration are well covered. The commercial operations (billing, support, analytics), the growth workflows (scheduling, reporting, inventory detail), and the operational lifecycle of running the SaaS itself are not yet complete.

Let me now walk through the full product as a narrative, filling what I can and flagging what needs a later conversation.

Part 2 — The complete SaaS workflow, end to end
Stage 0 — Platform birth (Day 0)
You deploy the platform with BOOTSTRAP_PLATFORM_ADMIN_EMAIL, BOOTSTRAP_PLATFORM_ADMIN_PASSWORD, and (optionally) DEMO_TENANT_ENABLED=true.

On startup, the backend:

Creates the platform admin. Fails fast if env vars are missing.

Seeds the default plans (starter, growth, scale). Plans are platform configuration, not tenant data — safe to seed.

Seeds the demo tenant if the flag is on. Demo tenant is isolated, marked is_demo=true, excluded from analytics and billing.

Does not create any restaurant, branch, or menu.

The platform admin logs in at admin.platform.com. The super admin dashboard shows an empty tenant list with two CTAs: "Register a tenant" and "View demo tenant."

Workflow state: Platform is alive, no tenants exist, no revenue possible yet. This is the correct day-0 state.

Stage 1 — Tenant acquisition
Three doors into the platform:

Door A — Self-serve. Restaurant owner finds your marketing site, clicks "Start free trial," fills a short form. Behind the scenes: tenant created in pending, magic link emailed, owner completes setup.

Door B — Sales-assisted. You talk to the restaurant, they decide to try it, you (as super admin) create a tenant shell and send them a magic link. Same downstream flow — they complete setup themselves.

Door C — Migrated. Existing pilot restaurant moves onto the platform via a migration script. Same shape, but their data is pre-loaded and they receive a "welcome, here's what changed" email rather than going through the wizard.

The key workflow principle: all three converge on the same wizard. No path is special. The first tenant is not privileged by bootstrap; it's privileged by the sales relationship.

Stage 2 — The first 30 minutes (setup wizard)
Once registered, the owner lands on the setup wizard. This is the single most important workflow in the entire product — it determines whether the restaurant ever reaches value.

Tier 1 — Required to see anything:

Restaurant name and first branch name

Timezone and currency

Tax mode

Tier 2 — Required to serve a customer:

First table (creates the first QR code)

First menu category

First menu item with a price

First staff member invited

Tier 3 — Required to operate at scale:

Full menu (import or manual)

All tables and floor plan

Staff invites with roles

Payment gateway configuration

Receipt template

The progressive workflow: the dashboard unlocks after Tier 1. A persistent checklist shows progress ("3 of 8 setup steps"). Tier 3 items are recommended but never blocking. A restaurant can go live with Tier 1 + Tier 2 and add the rest later.

Abandonment workflow:

Day 7: email nudge — "Finish setting up to get started."

Day 30: tenant soft-archived. Data preserved. No billing. No logins.

Day 90: deletion workflow begins with a 7-day recovery window.

This prevents half-configured tenants from cluttering the platform and communicating with your support staff in confusing ways.

Stage 3 — The first day of operation
The restaurant has completed Tier 1 and Tier 2. The owner has invited staff. The staff have logged in.

The first order workflow:

A guest sits at Table 1, scans the QR. blue-fork.platform.com/t/{token} loads.

Guest browses the menu, adds an item, submits. Order is created as pending_confirmation.

The waiter (on mobile or web) sees a new pending order in their queue. They accept it.

Kitchen sees the ticket in New. Marks Preparing. Marks Ready.

Waiter marks the item Served. Order transitions to Completed.

The bill auto-surfaces in the customer app. Guest taps "Pay at counter" (or pays online if enabled).

Cashier opens the bill, records cash payment, closes bill, closes session.

The owner sees the first completed session in their reports.

Workflow state: Full operational loop closed. The system works end-to-end for one restaurant, one branch, one table, one item. This is the minimum viable product.

Stage 4 — Steady-state daily operations
Morning:

Manager opens the dashboard, checks the branch's yesterday summary.

Kitchen staff open the kitchen board.

Waiter sees today's table map.

Owner sees a rollup (if multi-branch).

Lunch rush:

QR orders flow in. Waiters accept them in the branch queue.

Waiter orders from the floor go straight to kitchen.

Kitchen marks items ready.

Waiters serve.

Bills accumulate per session.

Cashier closes sessions as guests leave.

Afternoon lull:

Manager adjusts menu availability (sold out items).

Staff take breaks. Service calls are still routed to whoever is on shift.

Owner reviews yesterday's report.

Dinner rush: repeat of lunch.

Close:

Cashier runs end-of-day for the branch. Reports snapshot and lock for the day.

Cash discrepancies are recorded if any.

Sessions still open are flagged — either closed or carried into tomorrow.

Owner's evening:

Sees the branch's daily summary: revenue, covers, average ticket, cancellations, service call SLA.

Sees the rollup if multi-branch.

Weekly/periodic:

Menu updates (owner/manager with menu.manage).

Staff changes (membership invites, removals, role changes).

Inventory counts (if enabled).

Reports review and export.

Billing reconciliation for the tenant's own subscription (if a paid plan).

Stage 5 — Growth: adding a branch
The owner wants to open a second location.

Clicks "Add branch." The entitlement check runs before the form opens — if the plan allows 1 branch and they have 1, the button is disabled with "Upgrade to Growth to add more branches."

If allowed, the creation form appears. The owner chooses to seed from branch 1 or start empty.

Branch 2 is created. A setup wizard runs (similar to tenant onboarding but for the branch).

Staff memberships are updated. Some staff are added to branch 2, some stay only at branch 1, some are added to both (regional manager).

First QR for branch 2 is generated. First table is opened. First order placed.

Workflow principle: branches are additive. Adding a branch doesn't change the tenant's identity, billing, or user accounts. It expands operational scope.

Stage 6 — Subscription lifecycle
Trial → active:

Trial starts when the tenant is registered. Configurable duration.

Email cadence: day 7 (halfway), day 3 (ending soon), day 1 (last day), day 0 (ended).

Conversion triggers: owner chooses a plan from the dashboard, or hits a trial limit.

Conversion creates a subscription with gateway_subscription_id (via Stripe or equivalent).

Active operations:

Monthly invoice generated by the gateway.

Invoice paid → platform_invoices row updated to paid.

Failed payment → dunning.

Upgrade:

Immediate. Prorated billing for the remainder of the current period.

New entitlements apply immediately.

If upgrading unlocks a feature the user was blocked from, the block is cleared and the user is notified.

Downgrade:

Takes effect at period end. Entitlements reduce when the new plan starts.

If the tenant currently exceeds the new plan's limits, they're notified at downgrade time and again 7 days before it takes effect. They can choose to remove branches/staff or upgrade again.

Payment failure → past_due:

Day 1: fail. Email to owner. Dashboard banner amber.

Day 3: retry. Email. Banner persists.

Day 7: retry. Email. Banner red — "Service will be suspended soon."

Day 8: suspended. Dashboard read-only. Customer QR blocked for new sessions. Email.

Suspended → reactivated:

Owner updates payment method. System attempts payment.

On success: instant reactivation. Subscription returns to active.

On failure: stays suspended; another retry cycle begins.

Cancelled:

Owner cancels. Subscription stays active until period end.

At period end: expired. Read-only dashboard. Customer QR shows "temporarily unavailable."

Data retained for 90 days. Email at day 30, day 60, day 85 warning of deletion.

The workflow question I flagged earlier: during the grace period between past_due and suspended, should customer QR still work? My recommendation: yes, until 24 hours before suspension. Cutting off a restaurant mid-service is a relationship-ending event; warning them clearly is not.

Stage 7 — Support and incident workflows
Scenario: tenant reports a bug.

Support agent (super admin with support role) logs into admin.platform.com.

Searches by tenant name, email, or slug. Opens tenant detail.

Views tenant status, plan, recent audit events (read-only).

If the bug is in the app, cannot fix it directly. Files a bug ticket, notifies engineering.

If the bug is data-related (e.g., "my bill is wrong"), the tenant's own manager fixes it through their dashboard. Support guides, doesn't act.

Scenario: payment processing fails for a tenant's subscription.

Alert triggers in platform monitoring.

Super admin billing role reviews the invoice, checks the gateway.

If it's a transient gateway issue, retry.

If the tenant's card is bad, the tenant receives email. If they update, retry succeeds.

If the tenant disputes a charge, super admin can issue a refund or credit.

Scenario: impersonation.

Not enabled in the pilot — it's the most dangerous feature.

When enabled later: read-only, requires superadmin role, logged, tenant owner receives email notification ("a support agent viewed your account on {date}").

Scenario: tenant asks to be deleted.

Support team confirms identity and intent (this matters — deleting a restaurant is irreversible).

Data export offered first. Always.

Owner confirms deletion.

Tenant enters "pending deletion" for 7 days. Access revoked. Data preserved.

During the 7 days: reactivation available.

After 7 days: cascade delete runs. PII erased. Financial records preserved per retention (7 years for audit/payment events).

Confirmation email sent.

Scenario: platform incident (outage).

Monitoring detects DB unavailability.

On-call engineer paged.

Status page updated (public marketing site).

Incident response: isolate, mitigate, communicate, resolve, retro.

Tenants see an honest "we're experiencing issues" banner if the dashboard is partially reachable.

Stage 8 — Data export and exit
Any tenant can export their data at any time. The workflow:

Owner clicks "Export data" in settings.

Export runs in the background (queue job). Takes minutes to hours depending on data volume.

Export produces: menu (CSV), orders (CSV), payments (CSV), inventory (CSV), staff list (CSV), audit log (JSON), plus a README explaining the format.

Export download link is time-limited (7 days). Notifications email the owner.

Every export is audited (who, when, what).

Export is allowed even for past_due and suspended tenants — blocking data export creates legal risk.

Exiting fully:

Cancel subscription. Access until period end.

Export data at any time during the period.

At period end: read-only dashboard for 90 days. Export still allowed.

At day 90: deletion workflow starts.

The workflow principle: the tenant's data is theirs. The platform is a custodian, not an owner. This is both correct and good commercial practice.

Stage 9 — Platform operations (super admin, ongoing)
The platform team does these things continuously:

Monitor: dashboards for tenants, revenue, signups, churn, support load.

Review: daily/weekly review of new tenants, failed trials, churn reasons.

Adjust plans: rarely, but plans evolve. Changes affect future subscriptions; existing ones are grandfathered unless a migration is run.

Roll out features: feature flags per tenant, gradual rollout for new features.

Manage admins: adding/removing platform admins, roles.

Incident response: as described above.

Capacity planning: watch DB growth, query times, Redis memory, gateway rate limits.

Onboarding support: the human workflow — a 30-min call for new tenants to make sure they actually go live.

Part 3 — Notifications architecture (the part I owed)
Notifications are how the product feels alive. They route by audience, branch, and urgency.

Notification types by audience
Staff — operational (immediate):

New QR order awaiting confirmation (waiter queue, branch)

Kitchen ticket ready for service (waiter, branch)

Service call from guest (waiter, branch)

Payment failure for a bill (cashier, branch)

Staff — manager (with escalation):

Pending QR order age > 2 min (branch manager)

Delayed kitchen ticket > threshold (branch manager)

Unacknowledged service call > threshold (branch manager)

Session open > X hours (branch manager)

Staff — owner (digest and alerts):

Daily rollup ready (owner email)

Unusual cancellations (owner alert)

Subscription past_due (owner alert)

Export ready, invoice paid, etc. (owner email)

Super admin — platform:

New tenant registered (immediate, to sales/support)

Trial ending in 3 days (billing alert)

Subscription past_due (billing alert)

Churn event (subscription cancelled)

Payment failure across gateway (ops alert)

Incident detection (ops alert)

New tenant activation (success metric)

Customer:

Order submitted (immediate)

Order accepted / rejected (immediate)

Order preparing / ready / served (immediate)

Waiter on the way (immediate, after claim)

Bill ready (when last item served)

Payment confirmed (after backend confirmation, never from browser)

Delivery channels
Channel	When used
In-app (web + mobile)	Every notification appears in an in-app inbox/center. Always available.
Push (mobile only)	When the app is backgrounded. Deep-links to the relevant screen.
Email	Digest, non-urgent, and account events (billing, trial, exports, deletions).
SMS	Optional. Only for critical alerts (subscription suspension warning, payment failure).
Webhook	Future. For tenant integrations.
Routing rules
Customer notifications are scoped to the dining session. They expire when the session closes.

Staff notifications are scoped to the branch. Only branch members receive them.

Manager notifications are scoped to the branch + branch membership.

Owner notifications are scoped to the tenant. Any branch events roll up.

Super admin notifications are platform-wide, filtered by role.

Cross-branch routing never happens for operational events. A guest call at Branch A never notifies waiters at Branch B. It escalates within Branch A.

Delivery guarantees
The outbox pattern is the backbone. Every notification-generating action writes to outbox_events in the same transaction. A worker delivers.

At-least-once delivery is the practical guarantee. Clients dedupe on (event_id, notification_id).

Exactly-once is attempted at the application layer (idempotent delivery + client dedupe), not guaranteed by infrastructure.

Never trust notifications for correctness. Every screen refetches on open. Notifications are accelerators, not the source of truth.

Escalation workflow (the important part)
New QR order:

0s: notify all waiters on branch.

60s unclaimed: notify branch manager.

180s unclaimed: notify tenant owner.

300s unclaimed: surface in super admin dashboard as a platform-level alert.

Delayed kitchen ticket (> threshold):

0s (over threshold): notify kitchen supervisor.

2 min: notify branch manager.

5 min: notify tenant owner.

Unacknowledged service call:

0s: notify waiters on branch.

30s unclaimed: notify branch manager.

2 min unclaimed: notify tenant owner. Customer sees "we're on it" message.

Subscription past_due:

Day 1: email owner.

Day 3: email + dashboard banner.

Day 7: email + SMS (if phone on file).

Day 8 (suspended): email + SMS + dashboard alert.

The escalation tree is configurable per tenant (with sensible defaults) because different restaurants have different SLAs.

Part 4 — What's still genuinely missing
Areas we have not designed and that will bite you if ignored:

4.1 Staff scheduling and shifts.
Every staff member will ask "when am I working?" within week one. This is a large feature — shift templates, time-clock, swap requests, labor cost reporting. Not in the pilot scope, but should be on the roadmap. Decision needed: is this a paid add-on or included in higher tiers?

4.2 Reports and analytics detail.
The feature exists in the inventory but the actual reports aren't designed. Which reports? Sales, payments, cancellations, prep times, staff activity, session metrics. For each: what's the data source, what's the aggregation window, what's the export format? This is the "what does the owner see when they log in?" question — the answer is currently vague.

4.3 Inventory in SaaS.
Branch-scoped inventory is a bigger product than it sounds. Recipes, unit conversions, waste, counts, supplier management, purchase orders. The staged approach is correct, but the workflow is not detailed. Decision needed: is inventory an add-on or bundled in scale plan?

4.4 Payment gateway operations.
Beyond "record a payment," there's reconciliation, disputes, chargebacks, refunds, and multi-currency. Each gateway (Stripe, Adyen, regional) has different workflows. Decision needed: which gateway, and for which countries? This affects whether the platform itself can operate in some regions.

4.5 Multi-jurisdiction tax.
One branch, one tax zone: easy. 5 branches in 3 tax zones: not. Tax reporting per branch, tax remittance per jurisdiction, tax-inclusive vs tax-exclusive pricing per region. Decision needed: which countries do you plan to serve? That determines tax complexity.

4.6 Mobile app store lifecycle.
App Store / Play Store reviews take days. Tenant updates, minimum version enforcement, staged rollouts, forced-update flows. If a critical bug is found, you can't fix it overnight. Decision needed: how do you handle forced updates without a store review cycle? (Answer: feature flags in the API, not client updates.)

4.7 Custom domains for tenants.
Beyond subdomains, some tenants want order.myrestaurant.com. This is a per-tenant SSL, DNS, and routing layer. Decision needed: offer this on scale plan, or defer indefinitely?

4.8 Data residency.
GDPR-style regulations may require tenant data to stay in a specific country. Currently single-region. Decision needed: which markets are you targeting, and does residency matter?

4.9 Onboarding handoff (human workflow).
The workflow from "tenant registered" to "tenant successful" is partly technical, mostly human. Who calls them? When? What's the checklist for a successful onboarding call? This is not engineering work, but it determines SaaS success more than any single feature.

4.10 Platform analytics.
What metrics do you track? Daily signups, trial conversions, churn, MRR, ARR, active tenants, active branches, average order volume per tenant, top churn reasons. This needs a defined metrics dashboard that the platform team uses daily.

4.11 Compliance and legal workflows.
Data Processing Agreements, privacy policy acceptance, terms of service, audit log retention policies per jurisdiction, incident disclosure timelines. These are legal/ops workflows, not engineering, but they gate your ability to onboard real paying customers.