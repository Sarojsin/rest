# 11 — Owner Dashboard Setup Checklist

**File:** `backend/plan/workflow/11_owner_setup_checklist.md`
**Area:** Restaurant dashboard — first-time owner onboarding checklist
**Status:** Proposed

---

## 1. Overview

When a restaurant owner activates their account (via invitation), they land on
their restaurant dashboard and see a setup checklist showing which onboarding
steps remain incomplete:

1. Accept invitation (verify email, set password)
2. Complete restaurant profile (logo, contact, branding)
3. Configure branches (hours, contact info)
4. Configure tables and QR codes
5. Configure menu (categories, items, prices, ingredients)
6. Invite employees (managers, waiters, kitchen, cashier)
7. Configure payments (cash, QR methods)
8. Start operations

Each step is marked complete when the backend detects the corresponding data
exists. The owner cannot skip ahead — operations work regardless, but the
checklist nudges completion.

---

## 2. Current State

- Restaurant owner login works (PA-0.0 / identity module).
- Owner dashboard pages exist in `apps/web/src/pages/staff/` (Overview, Tables,
  MenuManage, Employees, Inventory, etc.).
- No setup checklist UI or backend state tracking exists.
- `restaurant_settings` table has fields for branding but no onboarding stage
  tracking.

---

## 3. Desired State

### 3.1 Backend: Onboarding stage tracking

Add an `onboarding_stage` column (or a JSON `onboarding_json`) to
`restaurant_settings`:

| Column | Type | Notes |
|--------|------|-------|
| `onboarding_stage` | varchar(32) | Current stage: invited, profile, branches, tables, menu, staff, payments, operational |
| `onboarding_completed_at` | timestamptz | When all stages complete |
| `onboarding_json` | JSON | Per-step completion flags and timestamps |

### 3.2 Stage completion detection

Backend computes stage from existing data:
- `invited` → `profile`: restaurant_settings has locale/branding filled
- `profile` → `branches`: at least one branch exists
- `branches` → `tables`: at least one table exists
- `tables` → `menu`: at least one menu category + item exists
- `menu` → `staff`: at least one non-owner membership exists
- `staff` → `payments`: at least one payment method configured
- `payments` → `operational`: at least one order completed

Endpoint: `GET /api/v1/onboarding/status` → returns current stage, completed
steps, remaining steps, percent complete.

### 3.3 Frontend: Setup checklist component

A checklist card on the Overview page (or dedicated `/staff/onboarding` route)
showing each step with:
- Step title
- Status: pending / in-progress / complete
- "Go to step" button linking to the relevant page
- Overall progress percentage

---

## 4. API Changes

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/v1/onboarding/status` | GET | Current onboarding stage + progress | staff: any role |

---

## 5. Frontend Changes

- `apps/web/src/pages/staff/OnboardingChecklist.tsx` (new component)
- Integrate into `OverviewPage.tsx` or create `/staff/onboarding` route
- Update `src/App.tsx` route if dedicated page

---

## 6. Acceptance Criteria

- [ ] `GET /api/v1/onboarding/status` returns stage and progress.
- [ ] Stage auto-advances when required data exists (computed, not manual).
- [ ] Checklist UI shows all 8 steps with status.
- [ ] "Go to step" buttons navigate to the correct page.
- [ ] When all steps complete, checklist shows "Setup complete".

---

## 7. Related Files

- `backend/app/modules/tenancy/models.py` — `RestaurantSettings` onboarding fields + migration
- `backend/app/modules/tenancy/router.py` — onboarding status endpoint
- `apps/web/src/pages/staff/OverviewPage.tsx` — integrate checklist
- `apps/web/src/pages/staff/OnboardingChecklist.tsx` (new)
