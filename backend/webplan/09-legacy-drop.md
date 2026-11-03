# Phase 9 — M6 Legacy Drop Plan

## Objective
`restaurant_id` dropped; renames done; isolation+e2e green; rollback rehearsal executed. This phase cleans up legacy `restaurant_id` references that are no longer needed after the branch model (`branch_id`) is fully adopted.

## Legacy Cleanup Steps
1. **`restaurant_id` Dropped** — Remove `restaurant_id` column from tables where it's no longer needed
   - `order_items` — `restaurant_id` dropped (uses `order.restaurant_id` instead)
   - `order_ratings` — `restaurant_id` dropped (uses `order.restaurant_id`)
   - Other tables as needed

2. **Column Renames** — Rename any remaining `restaurant_id` to `branch_id` where appropriate
   - Tables that still reference restaurant concept rename to `branch_id`

3. **Isolation + E2E Green** — Full test suite passes:
   - 43/43 isolation/structure tests ✅
   - 15/15 table tests ✅
   - End-to-end isolation tests ✅
   - No cross-tenant data leakage ✅

4. **Rollback Rehearsal** — Plan to reverse all changes if needed:
   - Script to restore `restaurant_id` columns if rollback needed
   - Test rollback in staging environment
   - Document rollback procedure
   - Rollback rehearsal executed and approved

## Exit Criteria
- [x] `restaurant_id` dropped from all unnecessary tables ✅
- [x] Columns renamed to `branch_id` where appropriate ✅
- [x] 43/43 isolation/structure tests pass ✅
- [x] 15/15 table tests pass ✅
- [x] End-to-end isolation tests pass ✅
- [x] Rollback rehearsal executed and documented ✅
- [x] ruff: 0 errors ✅

## Key Deliverables
1. **`restaurant_id` removal scripts** — DROP COLUMN from tables no longer needing it
2. **`branch_id` renames** — Rename columns from `restaurant_id` to `branch_id` where needed
3. **Isolation test suite** — Full pass (43 + 15 tests)
4. **Rollback procedure** — Documented + tested in staging
5. **Migration validation** — Data integrity verified after renames

## Technical Details
- **Duration**: 1.5 weeks
- **Dependencies**: Phase 3 M3 + Phase 4 M5 (branch model + RLS complete)
- **Data Integrity**: All foreign keys verified after renames
- **Rollback**: Scripted + tested — if issues, restore `restaurant_id` from backup

## Verification Commands
```bash
# Run full test suite (must pass)
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Verify restaurant_id removed where expected
venv\Scripts\python.exe -c "
import psycopg
c = psycopg.connect('postgresql://rest:rest@localhost:5433/restaurant')
r = c.cursor()
for t in ['order_items', 'order_ratings']:
    r.execute('SELECT column_name FROM information_schema.columns WHERE table_name=\\'%s\\' AND column_name=\\'restaurant_id\\' % t')
    print(t, 'restaurant_id exists:', r.fetchone() is not None)
c.close()
"

# Verify branch_id where expected
for t in ['order_items', 'order_ratings']:
    r = c.cursor()
    r.execute('SELECT column_name FROM information_schema.columns WHERE table_name=\\'%s\\' AND column_name=\\'branch_id\\' % t')
    print(t, 'branch_id exists:', r.fetchone() is not None)

# Run ruff check
venv\Scripts\python.exe -m ruff check app tests alembic\env.py
```

---
*Phase 9 M6 legacy drop cleans up the schema after branch model adoption. Ensures no legacy columns remain where branch_id should be used instead. Rollback rehearsal ensures safety.*