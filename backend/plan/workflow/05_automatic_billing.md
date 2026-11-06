# 05 — Automatic Billing

**File:** `05_automatic_billing.md`
**Area:** Invoice generation, renewal, payments
**Status:** Draft

---

## 1. Overview

Generate an invoice for every billing period. If payment succeeds, renew the subscription. If payment fails, move to past_due, then grace period. Manual payments verified by Billing staff.

---

## 2. Current State

- `platform_invoices` table exists with manual creation via `/api/platform/invoices`.
- `platform_payments` table exists with manual confirmation.
- No automatic invoice generation.
- No renewal scheduling.
- No payment webhook handling.

---

## 3. Desired State

| Event | Action |
|-------|--------|
| Subscription period ends | Generate new invoice |
| Payment received | Mark invoice PAID, renew subscription |
| Payment fails | Move to PAST_DUE, start grace period |
| Grace period ends | Move to SUSPENDED |

---

## 4. Schema Changes

### `platform_billing_cycles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `subscription_id` | UUID FK | |
| `period_start` | timestamptz | |
| `period_end` | timestamptz | |
| `invoice_id` | UUID FK → `platform_invoices.id` | |
| `status` | varchar(24) | pending, paid, overdue, grace, suspended |
| `next_retry_at` | timestamptz | |

---

## 5. Implementation Steps

### 5.1. Invoice generation service
File: `backend/app/modules/platform/services/billing.py` — Add:
- `generate_period_invoice(db, subscription) -> PlatformInvoice` — Creates invoice for next period.
- `generate_all_due_invoices(db) -> list[PlatformInvoice]` — Called by scheduler.

### 5.2. Renewal logic
- When invoice is paid: set `subscription.status = ACTIVE`, extend `current_period_end`.
- When payment fails: set `subscription.status = PAST_DUE`.
- After grace period: set `subscription.status = SUSPENDED`.

### 5.3. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/platform/billing/generate-invoices` | POST | Manual trigger (Super Admin / cron) |
| `/api/platform/billing/renew/{subscription_id}` | POST | Renew a specific subscription |
| `/api/platform/billing/webhook` | POST | Payment gateway webhook (future) |

---

## 6. Acceptance Criteria

- [ ] Invoice auto-generates when subscription period ends.
- [ ] Payment success renews subscription for next period.
- [ ] Payment failure moves subscription to PAST_DUE.
- [ ] Grace period transitions to SUSPENDED.
- [ ] Manual payment verification by Billing staff works.

---

## 7. Risks & Mitigations

- **Risk:** Double-charging on retry.
  - **Mitigation:** Idempotency keys on payments; check existing confirmed payments before creating new.
- **Risk:** Invoice generation fails midway.
  - **Mitigation:** Database transaction; rollback on failure.

---

## 8. Related Files

- `backend/app/modules/platform/services/billing.py` — Existing billing service
- `backend/app/api/platform/router_billing.py` — Existing billing router
- `backend/app/modules/platform/models.py` — Existing invoice/payment models
