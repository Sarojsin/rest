# 09 — Branch-Scoped Staff Invitations

**File:** `backend/plan/workflow/09_branch_scoped_staff.md`
**Area:** PA-07 extension — staff invitations scoped to branches
**Status:** Proposed

---

## 1. Overview

Extend the staff membership invitation endpoint so that managers, waiters,
kitchen, and cashier accounts are invited with an explicit `branch_id`. This
enables the Owner to grant staff access to specific branches rather than the
whole organization, matching the multi-branch model where:

- Owner → all branches
- Manager A → Kathmandu only
- Waiter A → Kathmandu only
- Cashier A → Pokhara only

A user may also be granted access to multiple branches if the restaurant wants
it.

---

## 2. Current State

- `POST /api/v1/restaurant_memberships/invite` (PA-07, implemented) accepts
  `{ email, role, name, phone }` with no branch scope.
- `RestaurantMembership` has `restaurant_id`, `user_id`, `role`, `status` but
  no branch assignment column.
- `ROLE_PERMISSIONS` in `app/modules/tenancy/permissions.py` grants role-based
  permissions but no branch scoping.
- Frontend `EmployeesPage.tsx` manages generic employee records (separate from
  login memberships).

---

## 3. Desired State

### 3.1 Schema Change: `restaurant_membership_branch`

New join table so a membership can be scoped to one or more branches:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `membership_id` | UUID FK → restaurant_memberships.id | |
| `branch_id` | UUID FK → branches.id | |
| `created_at` | timestamptz | |

Unique constraint on `(membership_id, branch_id)`.

Owner membership is implicitly "all branches" and does not require a row in
this table (owner bypasses branch scoping).

### 3.2 API Change: `POST /api/v1/restaurant_memberships/invite`

Body now includes optional `branch_id`:
```json
{
  "email": "sita@example.com",
  "role": "waiter",
  "name": "Sita",
  "phone": "+977-98-1111111",
  "branch_id": "b001-..."
}
```

- If `branch_id` is provided, validate it belongs to the same restaurant.
- Create membership + `restaurant_membership_branch` row atomically.
- Consume the role seat limit (already implemented in PA-07).

### 3.3 Middleware: Branch-scoped access enforcement

Add a dependency `require_branch_access(branch_id)` that checks:
- The caller's membership is an owner (bypass), OR
- The caller's membership has a `restaurant_membership_branch` row for the
  target branch.

Applied to endpoints that operate on branch-scoped resources (tables, orders,
kitchen tickets, cashier transactions within a specific branch).

---

## 4. Acceptance Criteria

- [ ] Invite endpoint accepts optional `branch_id`; invalid branch returns 400.
- [ ] Invited waiter can only access their assigned branch's tables/orders.
- [ ] Owner can access all branches without branch rows.
- [ ] Manager can be assigned to multiple branches via multiple join rows.
- [ ] Seat limit is consumed once per membership, not per branch.

---

## 5. Related Files

- `backend/app/modules/tenancy/models.py` — add `RestaurantMembershipBranch` model + migration
- `backend/app/api/v1/router_memberships.py` — update invite endpoint + schema
- `backend/app/modules/tenancy/permissions.py` — branch-scoped permission helper
- `backend/app/api/deps.py` — `require_branch_access` dependency
- `backend/app/modules/branches/router.py` — branch-scoped enforcement on table/order endpoints
