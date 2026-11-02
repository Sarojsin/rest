# Migration Runbook — M1…M6

**Everything here uses Postgres (D12). Each stage: ships independently, never breaks running behavior, has a verified fallback. CI gate for merging: `upgrade → down → upgrade` green + isolation suite green (18 §5).**

State flags: `tenant_columns.backfill_complete`, `tenant_columns.read_new`, `platform.rls_enabled` — runtime config, not env-only, so ops can flip without redeploying.

## M1 — New tables only (Phase 1)

`tenants, branches, memberships, membership_branches, roles(new scoped), membership_roles, plans, subscriptions, usage_counters, platform_invoices, platform_billing_events, platform_admins, platform_audit_logs, menu_item_branch_overrides` (+ `waiter_requests` deferred to Phase 8).

- Touches nothing existing ⇒ zero risk. Down: `DROP` in reverse-dependency order.
- Seed: default plans (trial/starter/growth/scale) + permissions catalog rows (platform config).
- `memberships` migration: existing `restaurant_memberships` rows **stay put**; new tables run parallel until M3 completes the move (dual write to both).

## M2 — Add columns, backfill (Phase 1)

```sql
-- per 03 §4 table list (STAGE A)
ALTER TABLE orders ADD COLUMN tenant_id UUID NULL REFERENCES tenants(id);
ALTER TABLE orders ADD COLUMN branch_id UUID NULL REFERENCES branches(id);
-- indexes
CREATE INDEX CONCURRENTLY idx_orders_tenant_branch ON orders (tenant_id, branch_id);
```

Backfill (single deployment today ⇒ mechanical):

```sql
INSERT INTO tenants (slug, legal_name, display_name, primary_email, default_currency, default_timezone, status)
SELECT 'pilot', name, name, contact_email, currency, timezone, 'active' FROM restaurants;

INSERT INTO branches (tenant_id, slug, name, timezone, currency_code, tax_config, ...)
SELECT t.id, 'main', r.name, tz_from_admin(r.id), cur(r.id), r.settings::jsonb, ...
FROM restaurants r JOIN tenants t ON t.slug='pilot';

UPDATE orders o SET tenant_id=b.tenant_id, branch_id=b.id
  FROM branches b WHERE o.restaurant_id = <legacy restaurant id>;
-- repeat per table; generic form uses restaurant_id join
-- memberships/roles: map restaurant_memberships → memberships + membership_roles + membership_branches
```

**General(N-restaurant) backfill — the maintained specification.** The SQL above is the single-restaurant quick path; the real artifact is `backend/scripts/backfill_legacy.py` (idempotent, CLI-driven), so a second inherited deployment never requires improvising SQL:

- **Input:** a mapping file (JSON) with one entry per legacy deployment:
  `{ deployment_ref, restaurant_id, tenant_slug, legal_name, display_name, primary_email, primary_phone, country_code, currency, timezone }`.
- **Per entry (transactional per tenant):** create-or-skip tenant by slug → create `main` branch → map every table by `restaurant_id` join → map memberships/roles/branches → per-table row-count parity check → abort loudly on any mismatch with a written per-tenant report (never partially commit a tenant).
- **Scope rule:** M-scope backfill is reserved for deployments that existed at migration time (Door C, 24 §1). A *new* legacy customer discovered after Phase 1 goes through **Door A registration** with a data-import tool (out of M scope, its own ADR if it ever happens) — the M scripts are frozen once the pilot migration completes.

Verification (gate before STAGE B — **mandatory even for one restaurant**):

```sql
SELECT 'orders' t, count(*) c FROM orders WHERE restaurant_id IS NOT NULL AND tenant_id IS NULL;  -- must be 0
-- repeat per table; plus row-count parity: count(*) = count(*) WHERE tenant_id IS NOT NULL
```

Down: nothing to undo (columns nullable, harmless).

## M3 — Dual-write (Phase 3)

- Writers set both `restaurant_id` and `(tenant_id, branch_id)` (repository base class handles it — 21 §6).
- New-column values authoritative when both present; mismatch assert fails loudly in staging/test-only.
- Deprecation headers on old-shaped endpoints (`14 §5`); existing clients unchanged.

## M4 — Read-switch + constraints + composite FKs (Phase 3)

- Flip `tenant_columns.read_new=true` per service module (flag-gated revert path).
- Uniqueness re-keys: e.g. `UNIQUE(restaurant_id, table_code)` → `UNIQUE(branch_id, table_code)`; idempotency keys → `(branch_id, scope, key)`; daily counters join keys re-keyed.
  **Idempotency re-key collision safety (mandatory):** in-flight client retries across the M4 window must not collide with migrated keys. Mechanism: scope value is versioned — legacy rows migrate to `scope='legacy:<old scope>'`, live code writes `scope='<scope>:v2'` from M4 deploy onward; legacy-scoped keys expire by cron 24h after M4 (deletion log retained). A replay attempt against an expired legacy key is simply processed fresh (server-side idempotency is per-scope, so cross-scope replay is impossible by construction). No maintenance window required; the 24h tail is covered by the flag-gate reading contract (clients retry ≤15 min).
- STAGE B: `ALTER COLUMN tenant_id/branch_id SET NOT NULL` after backfill verification.
- Composite FKs per 04 §4 (parents first get `UNIQUE(id, tenant_id)`).
- Memberships move: `restaurant_memberships` → `memberships` (transfer roles/branches), old table becomes a view (compat) until M6.

Down: flag flip (read old) — no SQL rollback needed.

## M5 — RLS enablement (Phase 4)

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY; ALTER TABLE orders FORCE ROW LEVEL SECURITY;
CREATE POLICY orders_tenant_isolation ON orders
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = ...same...);
-- generated for every table in rls_manifest.py
```

- App role: non-owner, `bypassrls` NOT granted; super-admin realm uses a separate restricted role with explicit `BYPASSRLS` + audit.
- `SET LOCAL app.current_tenant_id` in every transaction (session helper; buildkite-style check via CI test hitting un-scoped repo method returns 0 rows).
- Rollback: `DISABLE`/`DROP` policy per table (config flag for fast global disable in incident).

## M6 — Drop legacy (Phase 9; only after all-reads-new for ≥2 clean weeks)

```sql
ALTER TABLE orders DROP COLUMN restaurant_id;   -- per 03 §4 list
ALTER TABLE restaurant_daily_counters RENAME TO branch_daily_counters;
ALTER TABLE restaurant_tables RENAME TO tables;  -- renames finalized here, minimal churn
UPDATE outbox_events ... ; -- drop legacy keys if retained
DROP VIEW restaurant_memberships;  DROP TABLE restaurant_memberships;
DROP TABLE restaurants; -- export + archive snapshot first
```

**Requires:** full backup verified by restore drill (20 §5), no legacy column reads (asserted by grep on codegen + runtime Deprecation-usage log = zero for 14 days), down-migration script pre-written (re-add columns + repopulate from snapshot) and rehearsed in staging.
