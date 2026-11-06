# 07 — Restaurant Staff Roles & RBAC

**File:** `07_restaurant_staff_roles.md`
**Area:** Tenant staff roles (owner, manager, waiter, kitchen, cashier) with seat limits
**Status:** Draft

---

## 1. Overview

Restaurant-level RBAC with role-specific seat limits enforced by the backend. One primary owner per restaurant; additional managers per plan. Staff creation checks entitlements before inviting.

---

## 2. Current State

- `restaurant_memberships` table exists with `role` (owner, manager, waiter, kitchen, cashier).
- `token_version` column exists for force-logout.
- No seat limit enforcement.
- No role-based permission checks on tenant endpoints.
- Owner invitation exists; staff invitation does not.

---

## 3. Desired State

| Role | Max (Starter) | Max (Professional) | Max (Enterprise) |
|------|---------------|-------------------|------------------|
| Owner | 1 | 1 | 1 |
| Manager | 1 | 5 | 20 |
| Waiter | 3 | 15 | 50 |
| Kitchen | 2 | 10 | 30 |
| Cashier | 1 | 5 | 15 |

---

## 4. Schema Changes

No new tables required if `06_usage_counters_seat_limits.md` is implemented. The `platform_tenant_usage` table tracks counts per role.

---

## 5. Implementation Steps

### 5.1. Staff invitation endpoint
`POST /api/v1/restaurant_memberships/invite`
- Body: `{ email, role, name, phone }`
- Checks: caller has `restaurant.staff.manage` permission.
- Checks: seat limit for role not reached.
- Creates `restaurant_memberships` (status: INVITED).
- Creates one-time token for staff to set password.
- Returns invitation token (never a password).

### 5.2. Staff acceptance
`POST /api/platform/auth/invitations/{token}/accept` — Already exists for owner; extend for staff.

### 5.3. Role-based endpoint protection
Tenant endpoints check caller's role:
- `GET /api/v1/menu` — All staff can read.
- `POST /api/v1/menu` — Manager/Owner only.
- `POST /api/v1/orders` — Waiter/Cashier/Owner/Manager.
- `POST /api/v1/kitchen_tickets` — Kitchen/Waiter.
- `POST /api/v1/bills` — Cashier/Owner/Manager.

---

## 6. API Changes

Add role check dependency:
```python
def require_restaurant_role(allowed_roles: list[str]):
    def dependency(
        membership: RestaurantMembership = Depends(get_current_membership),
    ):
        if membership.role not in allowed_roles:
            raise AppError(403, "INSUFFICIENT_ROLE", ...)
    return dependency
```

---

## 7. Acceptance Criteria

- [ ] Owner can invite staff up to plan limits.
- [ ] Waiter cannot access owner-only settings.
- [ ] Seat limit enforced: 16th waiter on Professional (limit 15) rejected.
- [ ] Staff invitation is single-use, time-limited.
- [ ] Staff can set their own password on acceptance.

---

## 8. Risks & Mitigations

- **Risk:** Owner accidentally invites too many staff.
  - **Mitigation:** Clear UI showing remaining seats; backend rejects over-limit.
- **Risk:** Role escalation via direct API calls.
  - **Mitigation:** Backend enforces role on every endpoint; frontend-only restrictions insufficient.

---

## 9. Related Files

- `backend/app/modules/tenancy/router.py` — Existing tenant endpoints
- `backend/app/modules/tenancy/models.py` — `RestaurantMembership` model
- `backend/app/modules/platform/services/platform_directory.py` — `create_tenant` (owner invite)
