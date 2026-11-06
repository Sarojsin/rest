# 02 — Tenant Entitlements Enforcement

**File:** `02_tenant_entitlements_enforcement.md`
**Area:** Backend enforcement of plan features and limits
**Status:** Draft

---

## 1. Overview

Hiding a feature in React is not security. The FastAPI backend must enforce subscription entitlements on every relevant operation. Every tenant action that consumes a plan-limited resource must check: (1) the feature is enabled, (2) the usage limit is not reached.

---

## 2. Current State

- `platform_subscriptions` links tenant to a plan.
- `PlatformPlan.entitlements` is a free-form JSON blob.
- No enforcement middleware or dependency exists.
- Tenant CRUD operations (create staff, branches, tables) do not check plan limits.

---

## 3. Desired State

A dependency `get_tenant_entitlements(db, restaurant_id)` that returns effective features and limits for a tenant's current subscription. Used as a dependency in endpoints that create/update/delete tenant-owned resources.

---

## 4. Implementation Steps

### 4.1. Create entitlement service
File: `backend/app/modules/platform/services/entitlements.py`

Functions:
- `get_effective_entitlements(db, restaurant_id) -> dict` — Returns `{features: {...}, limits: {...}}` for the tenant's active subscription.
- `check_feature_enabled(db, restaurant_id, feature_key) -> bool`
- `check_limit_available(db, restaurant_id, limit_key, increment=1) -> bool`
- `consume_limit(db, restaurant_id, limit_key, increment=1) -> bool` — Atomic increment + check.

### 4.2. Create enforcement dependency
File: `backend/app/modules/platform/deps.py` — Add `require_feature` and `require_limit` dependencies.

### 4.3. Enforce on tenant endpoints
- `POST /api/v1/restaurant_memberships` — Check `owners`/`managers`/`waiters`/`kitchen`/`cashier` limits before creating.
- `POST /api/v1/branches` — Check `branches` limit.
- `POST /api/v1/menu_items` / `PUT` / `DELETE` — Check `menu_management` feature.
- `POST /api/v1/table_qr_codes` — Check `qr_ordering` feature.
- `POST /api/v1/inventory` — Check `inventory` feature.
- `GET /api/v1/reports/advanced` — Check `advanced_reports` feature.

---

## 5. Schema Changes

### `platform_tenant_entitlements` (cache table)
| Column | Type | Notes |
|--------|------|-------|
| `restaurant_id` | UUID PK | |
| `plan_version_id` | UUID | |
| `features` | JSON | Denormalized effective features |
| `limits` | JSON | Denormalized effective limits |
| `computed_at` | timestamptz | |
| `subscription_id` | UUID | |

---

## 6. API Changes

No new public endpoints. Existing endpoints gain enforcement via dependencies.

Example:
```python
@router.post("/restaurant_memberships")
def create_membership(
    payload: ...,
    entitlements: dict = Depends(require_tenant_entitlements),
    db: Session = Depends(get_db),
):
    role = payload.role
    limit_key = f"{role}s"  # owners, managers, waiters, kitchen, cashier
    if not check_limit_available(db, restaurant_id, limit_key):
        raise AppError(409, "SEAT_LIMIT_REACHED", ...)
```

---

## 7. Acceptance Criteria

- [ ] Creating a 16th waiter on a Professional plan (limit 15) returns 409.
- [ ] Creating inventory items on a Starter plan (no inventory) returns 403.
- [ ] Enforcement works across all subscription statuses (trialing, active, past_due, grace).
- [ ] Unit tests cover each enforcement path.

---

## 8. Risks & Mitigations

- **Risk:** Race condition — two simultaneous invitations exceed the limit.
  - **Mitigation:** Use database transaction with `SELECT ... FOR UPDATE` on usage counters.
- **Risk:** Frontend and backend drift on plan data.
  - **Mitigation:** Frontend fetches entitlements from `/api/platform/subscriptions`; backend is source of truth.

---

## 9. Related Files

- `backend/app/modules/platform/services/entitlements.py` — New service
- `backend/app/modules/platform/deps.py` — Add enforcement dependencies
- `backend/app/modules/tenancy/router.py` — Existing tenant endpoints to enforce
