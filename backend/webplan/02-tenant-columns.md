# Phase 1 M1 — Tenant Columns Plan

## Objective
Add `tenant_id` and `permission_version` columns to 5 key tables, backfill existing rows, and verify queries.

## Tables Affected
- restaurant_tables
- orders
- bills
- payments
- dining_sessions

## Columns Added
- `tenant_id UUID` — references tenants (multi-tenant partitioning)
- `permission_version INT` — version tracking for permission changes

## Backfill Strategy
- All existing rows get `tenant_id = restaurant_id` (same tenancy model)
- All existing rows get `permission_version = 1`
- New rows must provide both values

## Exit Criteria
- [ ] All 5 tables have `tenant_id` NOT NULL column
- [ ] All 5 tables have `permission_version` NOT NULL column
- [ ] Backfill verified: `SELECT count(*) FROM table WHERE tenant_id IS NULL = 0`
- [ ] Verification queries pass (see verification docs)
- [ ] 43/43 tests still green

## Key Deliverables
1. **ALTER TABLE** statements for all 5 tables
2. **UPDATE statements** to backfill `tenant_id = restaurant_id`
3. **UPDATE statements** to backfill `permission_version = 1`
4. **Verification queries** to confirm data integrity
5. **Test updates** if any tests reference old schema

## Technical Details
- **Duration**: 1 week
- **Dependencies**: Phase 0 (module restructure) must be complete FIRST
- **Data Model**: `tenant_id = restaurant_id` (one-tenant-per-restaurant model)

## Verification Commands
```bash
# Check tenant_id on all tables
venv\Scripts\python.exe -c "
import psycopg; c=psycopg.connect('postgresql://rest:rest@localhost:5433/restaurant'); r=c.cursor()
for t in ['restaurant_tables','orders','bills','payments','dining_sessions']:
    r.execute('SELECT count(*) FROM information_schema.columns WHERE table_name=\\'%s\\' AND column_name=\\'tenant_id\\'%' % t)
    print(t, 'tenant_id=', r.fetchone() is not None)
c.close()
"

# Verify no NULLs
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header
```

---
*Phase 1 M1 follows Phase 0 restructure. Do not start until restructure sign-off.*