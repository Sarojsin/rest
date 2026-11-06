# 12 — Subscription Upgrade / Downgrade Flow

**File:** `backend/plan/workflow/12_subscription_upgrade_downgrade.md`
**Area:** Subscription lifecycle — plan changes with usage-vs-limit validation
**Status:** Proposed

---

## 1. Overview

Allow a restaurant (via owner in dashboard) or an authorized admin (OPS/Super
Admin in Admin Console) to change a tenant's subscription plan. The backend
must check whether current usage fits the new plan's limits before permitting
the change, and must not silently delete users or resources on downgrade.

---

## 2. Current State

- `PlatformSubscription` links a restaurant to a plan version (PA-01/PA-03).
- `platform_plan_limits` / `platform_plan_features` store per-version limits.
- `GET /api/platform/tenants/{id}/entitlements` returns effective features/limits
  (PA-02).
- `consume_limit` / `release_limit` enforce seat limits atomically (PA-06).
- Admin can suspend/reactivate tenants (PA-0.13).
- No upgrade/downgrade endpoint exists.

---

## 3. Desired State

### 3.1 Upgrade workflow (owner or admin)

1. Owner opens Settings → Subscription (or Admin Console → Restaurants →
   Subscription).
2. Backend returns available plans (excluding current).
3. Owner selects a new plan.
4. Backend computes price difference (prorated for remaining billing period).
5. Owner confirms; payment or invoice is created.
6. Subscription switches to new plan version; entitlements update immediately.
7. Audit event `SUBSCRIPTION_UPGRADED` recorded.
8. Next renewal date recalculated.

### 3.2 Downgrade workflow (with guard)

1. Owner selects a lower-tier plan.
2. Backend checks **current usage vs new plan limits**:
   - branches: current branch_count <= new plan branches limit
   - waiters: current waiter_count <= new plan waiters limit
   - managers, kitchen, cashier, tables, owners similarly
3. If any usage exceeds the new limit → reject with 409 and a list of
   violations:
   ```json
   {
     "code": "DOWNGRADE_LIMIT_EXCEEDED",
     "violations": [
       { "resource": "waiters", "current": 12, "limit": 3, "excess": 9 },
       { "resource": "branches", "current": 5, "limit": 3, "excess": 2 }
     ]
   }
   ```
4. Owner must either reduce usage (remove staff/branches/tables) or choose a
   different plan. No silent deletion.
5. If all checks pass: subscription switches; audit event `SUBSCRIPTION_DOWNGRADED`.

### 3.3 API: `POST /api/platform/tenants/{id}/subscription/change`

Body:
```json
{
  "new_plan_code": "professional",
  "reason": "Customer requested upgrade",
  "confirm": "<tenant_slug>"
}
```

- Requires `subscription.manage` + step-up.
- `confirm` must equal the tenant slug (typed confirmation, PA-04 pattern).
- Returns new subscription details + invoice (if payment required).

---

## 4. Data Model

No new tables required. Reuse:
- `platform_subscriptions` (status, plan_id, plan_version_id, trial ends)
- `platform_plan_versions` (pricing per version)
- `platform_invoices` / `platform_payments` (billing)
- `platform_tenant_usage` (current usage for downgrade check)

Add `platform_subscription_change_history` table for audit:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK | |
| `from_plan_version_id` | UUID FK | |
| `to_plan_version_id` | UUID FK | |
| `changed_by_admin_id` | UUID FK | |
| `reason` | varchar(1000) | |
| `created_at` | timestamptz | |

---

## 5. Acceptance Criteria

- [ ] Upgrade switches plan version and updates entitlements immediately.
- [ ] Downgrade rejects (409) when usage exceeds new plan limits, with violation list.
- [ ] Downgrade never silently deletes staff, branches, or tables.
- [ ] `confirm` field required and must match tenant slug.
- [ ] Step-up required for plan changes.
- [ ] Audit event recorded for every plan change.
- [ ] Prorated price calculation for mid-cycle changes.

---

## 6. Related Files

- `backend/app/api/platform/router_subscriptions.py` — new change-plan endpoint
- `backend/app/modules/platform/services/entitlements.py` — usage counters (reuse)
- `backend/app/modules/platform/models.py` — `PlatformSubscriptionChangeHistory` + migration
- `backend/app/modules/platform/services/billing.py` — prorated invoice creation
