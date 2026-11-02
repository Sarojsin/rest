# Tenant Isolation Strategy

**Goal:** no read, write, subscription, event, or log crosses a tenant boundary — ever — with defense applied in layers, so any single failure is contained.

## 1. The six defense layers

| Layer | Mechanism | Enforced where | When live |
|-------|-----------|----------------|-----------|
| L1 Auth context | `TenantContext{tenant_id, branch_ids, perms}` derived only from verified token + live membership check | Middleware/dependency | Phase 2 |
| L2 Repository discipline | Every query filtered by `tenant_id = ctx.tenant_id`, branch filter when resource is branch-scoped | Repository layer (every repo fn requires `ctx`) | Phase 2 |
| L3 Resource ownership | Service re-verifies loaded row's `tenant_id == ctx.tenant_id` (and branch membership when scoped) before mutation | Service layer | Phase 3 |
| L4 DB integrity | Composite FKs make cross-tenant parent/child links impossible | Schema | M4 |
| L5 Postgres RLS | `USING (tenant_id = current_setting('app.current_tenant_id', true))` + `WITH CHECK` on every tenant table | Database | M5 |
| L6 Isolation tests | Two-tenant matrix over every protected endpoint, run with RLS off then on | CI, merge-blocking | Skeleton Phase 0, gating from M2 |

L5 is the last line, not the design. It exists so an unscoped query returns zero rows rather than another tenant's data.

## 2. Tenant resolution — single source of truth per request type

| Request | Tenant source |
|---------|---------------|
| Staff API (`/api/v1/*`) | JWT `tenant_id` claim **verified live** against `memberships.status='active'` + `memberships.tenant_id` match; mismatch → 401 (stale token path) |
| Customer QR (`/api/qr/*`) | `qr_token` → `table_qr_codes` → `tables` → `branch` → `tenant`. Server-resolved; token + subdomain must agree (12 §2) |
| Payment webhooks | payment/intent row in DB; never from payload |
| Platform API (`/api/platform/*`) | platform JWT; tenant from path param, validated against tenants table, action audited |
| Health/metrics | no tenant |

**Never** accept `tenant_id` from URL, query, or body on tenant-scoped resources. A tenant slug in a URL must match the authenticated membership's tenant or 404.

## 3. RLS design (enabled at M5 only)

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;   -- owner cannot bypass

CREATE POLICY orders_tenant_isolation ON orders
  USING      (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

Rules:

- Generate one policy per tenant-scoped table from a manifest (single source: `backend/app/db/rls_manifest.py`); a test asserts manifest covers exactly the tables in 03 §4 classification.
- App connects via a dedicated DB role that is **not** table owner (FORCE covers owner bypass anyway).
- Every request transaction executes `SET LOCAL app.current_tenant_id = :ctx.tenant_id` inside the session before queries (`db/session.py` helper; super-admin role bypasses via `bypassrls` privilege, which is logged and rare).
- Workers run per-tenant batches, each in its own transaction with the variable set.
- Background/cron reads (e.g., nightly demo reset) explicitly set the variable or use the bypass role with audit.
- `NULL` session variable ⇒ `current_setting(..., true)` returns NULL ⇒ comparison false ⇒ zero rows (safe by default).
- Branch scoping stays in the application layer (L2/L3); RLS handles tenant only — branch sets are small and per-user, wrong cost/benefit for a database policy.

## 4. Composite foreign keys (M4)

Cross-entity parent/child links cannot cross tenants. Requires `UNIQUE (id, tenant_id)` on the parent first:

```sql
ALTER TABLE dining_sessions ADD CONSTRAINT dining_sessions_id_tenant_uq UNIQUE (id, tenant_id);
ALTER TABLE orders ADD CONSTRAINT orders_session_tenant_fk
  FOREIGN KEY (dining_session_id, tenant_id)
  REFERENCES dining_sessions (id, tenant_id);

ALTER TABLE branches ADD CONSTRAINT branches_id_tenant_uq UNIQUE (id, tenant_id);
ALTER TABLE tables ADD CONSTRAINT tables_branch_tenant_fk
  FOREIGN KEY (branch_id, tenant_id) REFERENCES branches (id, tenant_id);
```

Apply to every parent/child pair in 03 §4 ("Tenant + required branch"): sessions↔orders, tables↔sessions, orders↔order_items, orders↔kitchen_tickets, bills↔payments, menu_items↔menu_item_branch_overrides. `17-migration-runbook.md M4` lists them all.

## 5. Global-table allowlist (the ONLY tables without tenant_id)

Maintained in `backend/app/db/isolation_allowlist.py`:

```
plans, permissions (catalog), platform_admins, platform_audit_logs,
platform_billing_events*   (*tenant_id nullable by design),
users (global identity, D4), refresh_tokens, migrations/alembic
```

The isolation test asserts: (a) every table not on this list has `tenant_id`; (b) no allowlisted table is exposed through a tenant-scoped endpoint; (c) schema diff fails CI if a new table is missing from either list. Usage counters/platform_invoices DO have tenant_id and are not allowlisted.

## 6. Concrete isolation guarantees

1. Staff request cannot read a row with `row.tenant_id != ctx.tenant_id`, even with a guessed valid UUID → 404, never 403 (do not leak existence).
2. QR session from branch A table 3 cannot read another branch's or tenant's session/order/bill.
3. Worker processing tenant A uses its own transaction with the session variable set; never mixes tenants in one transaction.
4. Super-admin cross-tenant action is the single sanctioned bypass; logged to `platform_audit_logs` with reason (08 §3).
5. WS/SSE subscriptions validate `(tenant_id, branch_id)` per topic; cross-branch broadcast never happens.
6. Idempotency keys are unique `(branch_id, scope, key)` — a key from branch/tenant A cannot replay into B.
7. Exports and audit views are ctx-scoped; platform admins see aggregates through the platform realm only.
8. Middleware serially re-checks: every tenant-scoped response payload carries resolved `tenant_id`; assertion fails loudly in staging builds.

## 7. Suspension/expiry behavior (D10)

| Tenant status | New sessions | New orders | In-flight sessions | Reads/export |
|---------------|--------------|------------|--------------------|--------------|
| past_due | ✅ (banner for owner) | ✅ | ✅ | ✅ |
| suspended | ❌ `TENANT_SUSPENDED` on QR start | ❌ | ✅ finish & settle | ✅ export always |
| cancelled | ✅ until period end | ✅ | ✅ | ✅ |
| expired | ❌ | ❌ | ❌ | ✅ owner read-only + export |

Gate lives in one service-level helper `tenant_gate.require_operational(ctx)` called at session/order mutation entry points — not scattered conditionals. Suspension also revokes refresh sessions (token_version bump) so per-request checks are the only state needed.
