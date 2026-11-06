# 06 — Usage Counters & Seat Limits

**File:** `06_usage_counters_seat_limits.md`
**Area:** Usage tracking and seat limit enforcement
**Status:** Draft

---

## 1. Overview

Track current usage per tenant (branches, staff by role, tables, etc.) and enforce plan limits atomically to prevent race conditions.

---

## 2. Current State

- `tenant_usage` in `platform_directory.py` does ad-hoc `COUNT(*)` queries.
- No usage counter table.
- No atomic seat allocation.
- No limit enforcement at the backend.

---

## 3. Desired State

| Table | Purpose |
|-------|---------|
| `platform_tenant_usage` | Cached usage counters per tenant |
| `platform_usage_events` | Append-only log of usage changes |

---

## 4. Schema Changes

### `platform_tenant_usage`
| Column | Type | Notes |
|--------|------|-------|
| `restaurant_id` | UUID PK | |
| `branch_count` | integer | |
| `owner_count` | integer | |
| `manager_count` | integer | |
| `waiter_count` | integer | |
| `kitchen_count` | integer | |
| `cashier_count` | integer | |
| `table_count` | integer | |
| `updated_at` | timestamptz | |

### `platform_usage_events`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK | |
| `resource_type` | varchar(64) | e.g. `waiter`, `branch`, `table` |
| `change` | integer | +1 or -1 |
| `actor_admin_id` | UUID | Who made the change |
| `reason` | varchar(1000) | |
| `created_at` | timestamptz | |

---

## 5. Implementation Steps

1. Create migration for `platform_tenant_usage` and `platform_usage_events`.
2. Backfill existing usage from `COUNT(*)` queries.
3. Create `consume_limit` / `release_limit` functions using `SELECT ... FOR UPDATE`.
4. Replace ad-hoc `COUNT(*)` in tenant endpoints with counter checks.
5. Add triggers or application logic to keep counters in sync.

---

## 6. Atomic Seat Allocation

```python
def consume_limit(db, restaurant_id, limit_key, increment=1):
    # Lock the usage row
    row = db.execute(
        select(PlatformTenantUsage)
        .where(PlatformTenantUsage.restaurant_id == restaurant_id)
        .with_for_update()
    ).scalar_one()
    
    current = getattr(row, f"{limit_key}_count")
    limit = get_plan_limit(db, restaurant_id, limit_key)
    
    if current + increment > limit:
        return False  # Limit reached
    
    setattr(row, f"{limit_key}_count", current + increment)
    db.add(PlatformUsageEvent(...))
    db.commit()
    return True
```

---

## 7. Acceptance Criteria

- [ ] Creating a waiter when limit reached returns 409 with clear message.
- [ ] Counter increments/decrements atomically (no race conditions).
- [ ] Counter matches actual COUNT(*) after any operation.
- [ ] Usage events are auditable.

---

## 8. Risks & Mitigations

- **Risk:** Counter drifts from actual data.
  - **Mitigation:** Periodic reconciliation job; endpoint to recount and fix.
- **Risk:** Deadlocks on high-contention rows.
  - **Mitigation:** Keep transactions short; always lock in same order.

---

## 9. Related Files

- `backend/app/modules/tenancy/services/platform_directory.py` — Existing `tenant_usage`
- `backend/app/modules/tenancy/router.py` — Tenant endpoints
