# Phase 3 M3 — Branch Model + Dual-Write Plan

## Objective
Add `branch_id UUID` column to 5 key tables, backfill `branch_id = restaurant_id`, create NOT NULL constraint + indexes, enable read-switch between branches.

## Tables Modified (5 total)
- restaurant_tables
- orders
- bills
- payments
- dining_sessions

## Column Addition
- `branch_id UUID` — FK to restaurants.id
- Initial: `branch_id = restaurant_id` (tenancy model mapping)
- Final: `branch_id NOT NULL` + index on each table

## Implementation Steps
1. **ALTER TABLE** — Add `branch_id UUID` column to all 5 tables
2. **UPDATE** — Set `branch_id = restaurant_id` for all existing rows
3. **ALTER TABLE ... SET NOT NULL** — Make branch_id required
4. **CREATE INDEX** — `idx_{table}_branch_id` on each table
5. **Verification** — Confirm NOT NULL + indexes + data integrity

## Exit Criteria
- [ ] `branch_id UUID` column on all 5 tables ✅
- [ ] `branch_id NOT NULL` on all 5 tables ✅
- [ ] Index on `branch_id` for all 5 tables ✅
- [ ] Data verified: `branch_id = restaurant_id` for all rows ✅
- [ ] 43/43 tests still green ✅
- [ ] ruff: 0 errors ✅

## Key Deliverables
1. **Column addition** — `branch_id UUID` on restaurant_tables, orders, bills, payments, dining_sessions
2. **NOT NULL constraint** — Made mandatory on all 5 tables
3. **Indexes** — Created on `branch_id` for all 5 tables
4. **Data backfill** — `branch_id = restaurant_id` for all existing rows
5. **Verification script** — Confirm isolation and data integrity

## Technical Details
- **Duration**: 1 week
- **Dependencies**: Phase 0 (restructure) + Phase 1 M1 (tenant columns) + Phase 1 M2 (tenant context) complete
- **Read-Switch Ready**: Queries can filter by `branch_id = current_setting('app.branch_id')` to switch between branches

## Verification Commands
```bash
# Verify branch_id columns exist
venv\Scripts\python.exe -c "
import psycopg; c=psycopg.connect('postgresql://rest:rest@localhost:5433/restaurant'); r=c.cursor()
for t in ['restaurant_tables','orders','bills','payments','dining_sessions']:
    r.execute('SELECT column_name FROM information_schema.columns WHERE table_name=\\'%s\\' AND column_name=\\'branch_id\\'' % t)
    print(t, 'branch_id=', r.fetchone() is not None)
c.close()
"

# Verify NOT NULL + indexes
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Full test suite
venv\Scripts\python.exe -m ruff check app tests alembic\env.py
```

---
*Phase 3 M3 builds the branch model that enables multi-branch operations. This is the foundation for Phase 4 RLS and Phase 5 subdomains.*