# Multi-Tenant Migration Plan (Based on baseplan.md)

## Current State Assessment
- **Single-tenant architecture**: `restaurant_id` overloaded (business + location)
- **Existing multi-tenant readiness**: 
  - Branch selectors and tenant context already in frontend
  - `orders.serve` permission exists in roles
  - Mobile kitchen has "Pending service calls" feature (Phase 3 completed)
  - Single bill consolidation for same table works by design
- **Key gaps**: 
  - No `tenant_id`/`branch_id` columns in operational tables
  - No multi-tenant auth (JWT lacks `tenant_id`, `branch_ids`)
  - No RLS policies (Stage 4)
  - No tenant switching flow
  - No subscription/billing system

## Immediate Next Steps (Phase 1: Tenancy Scaffolding)
1. **Create new multi-tenant tables** (M1)
   - `tenants`, `branches`, `memberships`, `membership_branches`, `roles`, `membership_roles`, `plans`, `subscriptions`, `usage_counters`, `platform_invoices`, `platform_billing_events`, `platform_admins`, `platform_audit_logs`
   - Ensure `UNIQUE (tenant_id, branch_id)` indexes on all operational tables per §3.1.2

2. **Backfill existing data** (M2)
   - Migrate `restaurant` → `tenants` + `branches` 
   - Set `tenant_id`/`branch_id` on existing operational tables
   - Validate row counts match pre-migration (use COUNT(*) parity checks)

3. **Add nullable `tenant_id`/`branch_id` columns** (M2)
   - Alter all operational tables listed in §3.1.2
   - Keep `restaurant_id` for backward compatibility during dual-write

4. **Implement dual-write in service layer** (M3)
   - Modify all endpoints to write to both `restaurant_id` and `tenant_id`/`branch_id`
   - Gate reads with `USE_TENANT_COLUMNS` feature flag
   - Ensure existing tests pass with dual-write enabled

5. **Add tenant resolution endpoints** (M2)
   - `/api/v1/tenant` - current tenant profile + entitlements
   - `/api/v1/branches` - branch selection for branch-scoped menus

## Critical Dependencies
- **Isolation test suite** must run in CI from M2 onward (§4.6)
- **Composite FKs** (e.g., `orders_session_tenant_fk`) to be added in M4
- **RLS policies** (§5.1) deferred to Phase 4 (M5) - must not enable before app-layer tenant scoping is verified

## Phase 2 (2 weeks)
- Implement multi-tenant JWT (`tenant_id`, `branch_ids`, `pv`)
- Tenant switcher flow with token re-issue
- Membership model with branch scoping

## Phase 3 (2 weeks)
- Branch CRUD operations
- Branch-scoped menus and availability
- Dual-write enforcement for reads

## Phase 4 (2 weeks)
- Enable RLS on operational tables (§5.1)
- Add composite foreign keys for cross-entity integrity
- Full cross-tenant test suite with RLS enabled

## Phase 5 (2 weeks)
- Super admin realm (`platform_admins`)
- Plans table with entitlements
- Tenant list/detail, suspend/reactivate

## Phase 6 (3 weeks)
- Stripe subscription integration
- Usage counters + Redis enforcement
- Entitlement enforcement on branches, staff users, orders/month

## Phase 7 (1 week)
- Customer QR tenant routing via subdomains
- qr_token → branch → tenant resolution

## Phase 8 (1 week)
- Waiter request feature (already in plan)
- New `waiter_requests` table + endpoint + UI

## Phase 9 (1 week)
- Drop `restaurant_id` columns after 2 weeks of green isolation tests
- Requires full backup and rollback plan

## Backward Compatibility
- All existing `/api/v1/*` endpoints continue working with implicit tenant
- Old tokens accepted for 1 access-token lifetime post-deploy
- QR URLs unchanged (`t/:qrToken`)
- Mobile app old binaries fall back to single-tenant behavior
- Web deep links redirect to subdomain format