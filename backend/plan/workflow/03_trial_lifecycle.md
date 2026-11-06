# 03 — Trial Lifecycle

**File:** `03_trial_lifecycle.md`
**Area:** Trial expiry, grace period, notifications
**Status:** Draft

---

## 1. Overview

A subscription lifecycle includes TRIALING → ACTIVE → PAST_DUE → GRACE → SUSPENDED → CANCELLED/EXPIRED. Trials must expire automatically, notify owners before expiration, and not be repeatedly creatable to avoid payment.

---

## 2. Current State

- `platform_subscriptions.status` supports `TRIALING`, `ACTIVE`, `PAST_DUE`, `GRACE`, `SUSPENDED`.
- `trial_ends_at` column exists.
- No automatic trial expiration.
- No trial expiry notifications.
- No trial history tracking.
- No trial extension limits.

---

## 3. Desired State

| Status | Meaning |
|--------|---------|
| `trialing` | Free trial is active |
| `active` | Paid subscription is active |
| `past_due` | Payment is overdue |
| `grace_period` | Temporary payment extension |
| `expired` | Trial or subscription period ended |
| `cancelled` | Subscription cancelled |
| `suspended` | Platform access restricted |

---

## 4. Schema Changes

### `platform_subscription_trial_history`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK | |
| `trial_start_at` | timestamptz | |
| `trial_end_at` | timestamptz | |
| `plan_version_id` | UUID | |
| `converted_to_paid` | boolean | |
| `converted_at` | timestamptz | null |
| `reason` | varchar(1000) | |

### `platform_subscriptions` updates
- Add `cancel_at_period_end` boolean (already exists in model).
- Add `canceled_at` timestamptz (already exists).

---

## 5. Implementation Steps

### 5.1. Trial expiration job
Create a background task (or management command) that:
- Finds subscriptions where `status = 'TRIALING'` AND `trial_ends_at < now()`.
- Sets `status = 'EXPIRED'`.
- Creates audit record.

### 5.2. Trial expiry notifications
- When `trial_ends_at - now() <= 3 days`, create notification.
- When `trial_ends_at - now() <= 1 day`, create notification.
- Store notifications in `platform_notifications` table or send via email.

### 5.3. Trial extension limit
- Track trial extensions per tenant.
- Max 1 extension of 7 days (configurable).
- Super Admin can override with reason + audit.

### 5.4. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/platform/subscriptions/{id}/extend-trial` | POST | Extend trial (Super Admin only) |
| `/api/platform/subscriptions/{id}/cancel` | POST | Cancel at period end or immediately |
| `/api/platform/subscriptions/{id}/reactivate` | POST | Reactivate cancelled/expired |

---

## 6. Acceptance Criteria

- [ ] Trial subscription automatically expires when `trial_ends_at` passes.
- [ ] Owner receives notification 3 days and 1 day before trial expiry.
- [ ] Cannot create more than 1 trial per tenant (tracked in trial history).
- [ ] Super Admin can extend trial with recorded reason + audit.
- [ ] Expired restaurants cannot create new orders/staff/branches.

---

## 7. Risks & Mitigations

- **Risk:** Trial expiration job misses edge cases.
  - **Mitigation:** API also checks `trial_ends_at` on every request; defense in depth.
- **Risk:** Owner creates new trial after expiry to avoid payment.
  - **Mitigation:** `platform_subscription_trial_history` tracks all trials per tenant; reject new trial if history exists.

---

## 8. Related Files

- `backend/app/modules/platform/services/billing.py` — Existing subscription logic
- `backend/app/api/platform/router_subscriptions.py` — Existing subscription router
- `backend/app/modules/platform/models.py` — Existing `PlatformSubscription` model
