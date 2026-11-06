# 13 — Offboarding & Data Export

**File:** `backend/plan/workflow/13_offboarding_data_export.md`
**Area:** Restaurant closure / cancellation workflow with data export
**Status:** Proposed

---

## 1. Overview

When a restaurant closes or cancels, the platform must:
1. Record the cancellation request.
2. Set a subscription end date (paid access continues until then if scheduled).
3. Restrict normal operations.
4. Allow the owner to request a data export.
5. Retain data for the contractual/legal retention period.
6. Delete or anonymize data per policy.

Closing one branch must **not** cancel the entire tenant subscription.

---

## 2. Current State

- `POST /api/platform/tenants/{id}/suspend` — suspends a tenant (PA-0.13).
- `POST /api/platform/tenants/{id}/archive` — archives a tenant.
- `restaurant.status` can be ACTIVE / SUSPENDED / CANCELLED.
- No data export endpoint exists.
- No retention/anonymization job exists.

---

## 3. Desired State

### 3.1 Cancellation workflow

**Endpoint:** `POST /api/platform/tenants/{id}/cancel`

Body:
```json
{
  "reason": "Customer requested closure",
  "confirm": "<tenant_slug>",
  "effective_date": "2026-12-31"  // optional; if omitted, immediate
}
```

- Requires `tenant.delete` (Super Admin) or `tenant.suspend` (OPS).
- `confirm` must equal tenant slug.
- Sets `restaurant.status = 'CANCELLED'` and `cancelled_at`.
- If `effective_date` is in the future: subscription stays ACTIVE until then,
  then moves to CANCELLED. Normal operations restricted immediately.
- Audit event `TENANT_CANCELLED` recorded.

**Branch closure:** `PATCH /api/v1/branches/{id}` with `is_active=false` — only
deactivates that branch, not the tenant.

### 3.2 Data export

**Endpoint:** `GET /api/platform/tenants/{id}/export`

Returns a downloadable package (zip or JSON) containing all data for the
tenant:
- restaurant profile + settings
- branches
- menu categories + items
- tables + QR codes
- orders + order items
- dining sessions
- kitchen tickets
- payments + bills
- memberships (staff, without password hashes)
- inventory ingredients + stock movements
- reviews
- audit logs (tenant-scoped)

Export is generated asynchronously; endpoint returns a `job_id` and the client
polls `GET /api/platform/export/{job_id}` until complete, then downloads.

### 3.3 Retention & anonymization

- A background job (or manual admin action) anonymizes cancelled tenant data
  after the retention period (e.g., 90 days).
- Anonymization: replace emails/names with hashed placeholders, keep order
  aggregates for reporting, remove personal identifiers.
- Admin can trigger: `POST /api/platform/tenants/{id}/anonymize` (Super Admin
  only, step-up).

---

## 4. Acceptance Criteria

- [ ] Cancellation requires `confirm` = tenant slug and step-up.
- [ ] Branch deactivation does not cancel tenant subscription.
- [ ] Cancelled tenant cannot create orders/tables/menu items (403 on writes).
- [ ] Data export endpoint returns all tenant-scoped data.
- [ ] Export job can be polled and downloaded.
- [ ] Anonymization removes personal identifiers, keeps aggregates.
- [ ] Audit events recorded for cancel, export, anonymize.

---

## 5. Related Files

- `backend/app/api/platform/router_tenants.py` — cancel + export endpoints
- `backend/app/modules/platform/services/platform_directory.py` — set_tenant_status
- `backend/app/modules/tenancy/models.py` — Restaurant status transitions
- `backend/app/modules/operations/models.py` — Order, RestaurantTable (export scope)
- `backend/app/modules/catalog/models.py` — MenuCategory, MenuItem (export scope)
