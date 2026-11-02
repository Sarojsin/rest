# Phase 2 M1 — Memberships Live-Read Plan

## Objective
Implement live-read memberships (no more stored copies), seeds for second tenant, and verify actor permissions.

## Core Concept
Membership data read directly from DB on every request, never stored in session/token. This ensures always-current permissions and branch assignments.

## Implementation Requirements
1. **Membership model** — `RestaurantMembership` with `restaurant_id`, `user_id`, `role`, `status`
2. **Live-read service** — `db.scalar(select(RestaurantMembership) ...)` on every auth check
3. **Seed data** — Second tenant (restaurant_2, user_2, membership_2) seeded idempotently
4. **Actor model** — `Actor(user, membership)` with `restaurant_id` property

## Exit Criteria
- [ ] Membership read directly from DB (not from cached session data) ✅
- [ ] Second tenant seeds work: `seed_if_empty(db)` creates restaurant_2 + user_2 + membership_2 ✅
- [ ] Actor permissions verified: tenant1 actor cannot see tenant2's tables ✅
- [ ] 43/43 tests still green ✅
- [ ] import-linter: 0 broken ✅

## Key Deliverables
1. **`app/modules/identity/models.py`** — User model + relationships
2. **`app/modules/tenancy/models.py`** — RestaurantMembership model
3. **`app/api/deps.py`** — `get_actor()` function with live-read membership
4. **`app/seed.py`** — `seed_if_empty(db)` with second tenant seeds
5. **`tests/isolation/test_two_tenants_fixture.py`** — Two-tenant isolation tests

## Technical Details
- **Duration**: 1 week
- **Dependencies**: Phase 0 (module restructure) + Phase 1 M1 (tenant columns) complete
- **Auth Flow**: Live-read membership on every request, no stored copies

## Verification Commands
```bash
# Run isolation tests (the key test for live-read memberships)
venv\Scripts\python.exe -m pytest tests/isolation/test_two_tenants_fixture.py -q --no-header

# Run full test suite
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Verify membership live-read
venv\Scripts\python.exe -m pytest tests/ -q --no-header -k "membership"
```

---
*Phase 2 M1 ensures memberships are read live, not cached. This is critical for always-current permissions and branch assignments.*