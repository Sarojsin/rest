# 08 — Admin Console Onboarding Wizard

**File:** `backend/plan/workflow/08_admin_onboarding_wizard.md`
**Area:** Admin Console — multi-step restaurant onboarding flow
**Status:** Proposed

---

## 1. Overview

A single, transactional onboarding workflow in the Admin Console that lets an
authorized Super Admin or OPS user register a complete restaurant organization:
business details, owner invitation, subscription plan, trial configuration, and
initial branches — all created atomically.

Previously these were separate endpoints/pages; this plan unifies them into one
guided wizard with review-before-confirm.

---

## 2. Current State

- `POST /api/platform/tenants` creates a tenant (PA-04 / router_tenants.py).
- `POST /api/platform/plans/{id}/versions` + limits/features create plan versions (PA-01).
- `POST /api/platform/self-service/registrations/{id}/approve` approves a self-service app (PA-04).
- `POST /api/v1/branches` creates a branch under a tenant (PA-02 enforcement now applied).
- Admin Console pages exist for Restaurants, Plans, Subscriptions, Tenants, etc., but there is **no single onboarding wizard**.
- Owner invitation token is generated but **no email delivery** is wired (see plan 14).

---

## 3. Desired State

| Step | Title | What the admin enters | Backend action |
|------|-------|----------------------|----------------|
| 1 | Organization details | name, legal_name, email, phone, country, province, district, address, website, logo, timezone, currency | Validate uniqueness of slug/email |
| 2 | Owner account | full name, email, phone | Generate invitation token; store INVITED owner |
| 3 | Subscription | plan_code, trial_days, billing_interval | Create subscription + plan version reference + entitlements |
| 4 | Branches | name, code, address, phone, email, opening_hours, timezone | Create N branch rows under tenant |
| 5 | Review & create | Summary of all above | Transactional create: tenant → subscription → branches → owner invite → audit |

**Outputs:**
- `tenant_id` (permanent org ID, not the owner email)
- `subscription_id`
- `branch_id`s
- Owner invitation token (sent via email, never shown as password)

---

## 4. API Changes

### New endpoint: `POST /api/platform/onboarding/restaurants`

Body:
```json
{
  "restaurant": {
    "name": "MAISON Restaurant",
    "legal_name": "MAISON Pvt. Ltd.",
    "slug": "maison-restaurant",
    "contact_email": "contact@maison.example",
    "contact_phone": "+977-1-1234567",
    "country": "NP",
    "province": "Bagmati",
    "district": "Kathmandu",
    "address": "Business address",
    "website": "maison.example",
    "timezone": "Asia/Kathmandu",
    "currency_code": "NPR"
  },
  "owner": {
    "full_name": "Restaurant Owner",
    "email": "owner@maison.example",
    "phone": "+977-98-1234567"
  },
  "subscription": {
    "plan_code": "professional",
    "trial_days": 14,
    "billing_interval": "MONTHLY"
  },
  "branches": [
    { "name": "MAISON Kathmandu", "code": "KTM-01", "address": "...", "phone": "...", "email": "...", "opening_hours": "09:00-22:00", "timezone": "Asia/Kathmandu" },
    { "name": "MAISON Pokhara", "code": "PKR-01", "address": "...", "phone": "...", "email": "...", "opening_hours": "09:00-22:00", "timezone": "Asia/Kathmandu" }
  ]
}
```

Response:
```json
{
  "tenant_id": "7f2a...",
  "restaurant": { "id", "name", "slug", "status": "ACTIVE" },
  "subscription": { "id", "plan_code", "status": "TRIALING", "trial_ends_at" },
  "branches": [ { "id", "name", "code", "status": "ACTIVE" } ],
  "owner_invitation": { "email", "token", "expires_at" },
  "audit_id": "..."
}
```

**Permissions:** `tenant.create` + `subscription.manage` (OPS/Super Admin).
**Step-up:** Required (sensitive: creates tenant + subscription + invitation).
**Idempotency:** `Idempotency-Key` header supported; duplicate key returns prior result.

---

## 5. Transactional Behavior

1. Validate slug + owner email uniqueness.
2. Create `restaurants` row (status: ACTIVE).
3. Create `restaurant_settings` row.
4. Create `platform_subscriptions` row (TRIALING if trial_days > 0, else ACTIVE).
5. Create `branch` rows (each with unique branch_id).
6. Create owner `users` row (status: INVITED) + `restaurant_memberships` (role: owner, ACTIVE).
7. Create `platform_one_time_token` (purpose: OWNER_INVITE, TTL 72h).
8. Write audit event `RESTAURANT_ONBOARDED`.
9. Commit.

On any failure: full rollback. No partial tenant.

---

## 6. Acceptance Criteria

- [ ] One POST creates tenant, subscription, branches, owner invitation atomically.
- [ ] Duplicate slug or owner email returns 409 before any writes.
- [ ] Branch count does not exceed plan's `branches` limit.
- [ ] Owner invitation token is single-use, 72h TTL, returned once.
- [ ] Audit event recorded with admin_id, restaurant_id, before/after.
- [ ] Idempotency key prevents duplicate creation on retry.

---

## 7. Related Files

- `backend/app/api/platform/router_tenants.py` — add onboarding route
- `backend/app/modules/platform/services/platform_directory.py` — `create_tenant` (reuse)
- `backend/app/modules/platform/services/self_service.py` — approve flow (reference for invite token)
- `backend/app/modules/tenancy/models.py` — `Restaurant`, `RestaurantMembership`, `RestaurantSettings`
- `backend/app/modules/platform/models.py` — `PlatformSubscription`, `PlatformOneTimeToken`
