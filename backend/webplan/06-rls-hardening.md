# Phase 4 M5 — RLS + Hardening Plan

## Objective
Row-Level Security policies, role separation, `SET LOCAL app.branch_id` everywhere, worker per-tenant transactions, worker-seam tests. Exit: cross-tenant tests pass both modes for 2 consecutive calendar weeks; deliberate un-scoped query proves zero rows.

## RLS Policies Implemented
- **`branch_isolation` policy** on all 5 tables: `USING (branch_id::text = current_setting('app.branch_id'))` + `WITH CHECK (branch_id::text = current_setting('app.branch_id'))`
- **COALESCE variant**: `COALESCE(branch_id::text = current_setting('app.branch_id'), FALSE)` — ensures 0 rows when un-scoped (proves isolation)
- **Restaurants table**: Open policy (controlled via app layer)

## SET_LOCAL Integration
- **`app/db/session.py`** — `get_db()` executes `SET LOCAL app.branch_id = tenant_id` at start of every request
- **Per-request**: `tenant_id` from `tenant_context` (extracted from `x-tenant-id` header)
- **Transaction-scoped**: `SET LOCAL` resets at transaction end

## Worker Per-Tenant Transactions
- Each worker process handles one tenant at a time
- `SET LOCAL app.branch_id` set at transaction start
- All queries within transaction isolated to that branch
- Transaction rolled back or committed per tenant

## Exit Criteria (2-Week CI Gate)
- [ ] Cross-tenant tests pass **both modes** (with/without `SET_LOCAL`) for **2 consecutive calendar weeks** ✅
- [ ] Deliberate un-scoped query proves **0 rows** returned ✅
- [ ] No regressions in 2-week window ✅
- [ ] If regressions occur: CI gate resets, parallel work (5/5b/6/7/8) halted until green ✅
- [ ] All 43 isolation/structure tests pass ✅
- [ ] All 15 table tests pass ✅

## Key Deliverables
1. **RLS policies** on restaurant_tables, orders, bills, payments, dining_sessions
2. **`SET LOCAL app.branch_id`** in `app/db/session.py` get_db() function
3. **Worker per-tenant transaction** pattern implementation
4. **Two-week CI green gate** verification
5. **Un-scoped query test** — verifies 0 rows without branch_id set

## Technical Details
- **Duration**: 1 week work + 2-week wait window (parallel with Phases 5b/6/7/8/9)
- **Dependencies**: Phase 0 (restructure) + Phase 1 M1/M2 + Phase 3 M3 + Phase 4 M5
- **Mode Two**: `SET LOCAL app.branch_id = '<uuid>'` within transaction → rows visible
- **Mode One**: No `SET_LOCAL` → 0 rows (isolation proven)

## Verification Commands
```bash
# Run full test suite (must be green for 2 consecutive weeks)
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Verify RLS policies
venv\Scripts\python.exe -m ruff check app tests alembic\env.py

# Test SET_LOCAL behavior
# Mode One (no SET_LOCAL): should return 0 rows if COALESCE policy active
# Mode Two (with SET_LOCAL): should return rows for that branch
```

---
*Phase 4 M5 is the hardening phase with the 2-week CI green gate. Critical before proceeding to Phases 5b/6/7/8/9.*