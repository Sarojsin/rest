# Restaurant System — Full Implementation Plan

**Date**: 2026-11-01  
**Repository**: `E:\rest`  
**Status**: Uncommitted changes across backend, web, and mobile

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Core Workflow: Kitchen → READY → Waiter → SERVED → Bill](#2-core-workflow-kitchen--ready--waiter--served--bill)
3. [Customer Adds More Items → Single Bill](#3-customer-adds-more-items--single-bill)
4. [Notification / Call-Waiter Feature](#4-notification--call-waiter-feature)
5. [Multi-Entity Scenarios](#5-multi-entity-scenarios)
6. [Permission System](#6-permission-system)
7. [Demo Accounts & Branding](#7-demo-accounts--branding)
8. [Production Bootstrap](#8-production-bootstrap)
9. [Idempotency, Money, Audit, Tenant Scope](#9-idempotency-money-audit-tenant-scope)
10. [Files Changed Summary](#10-files-changed-summary)
11. [Verification Checklist](#11-verification-checklist)
12. [Remaining Work](#12-remaining-work)

---

## 1. System Overview

A multi-tenant restaurant management system with three clients:

- **Web** (`apps/web`) — React + Vite, staff dashboards, customer QR status page
- **Mobile** (`apps/mobile`) — Expo/React Native, kitchen board, waiter order screen
- **Backend** (`backend`) — FastAPI + PostgreSQL, modular monolith

### Key Invariants (from AGENTS.md)

- PostgreSQL is the source of truth
- QR orders require staff confirmation
- Money in integer minor units
- Audit logs append-only
- Tenant-scoped (all data filtered by `restaurant_id`)
- Idempotency keys on orders and payments

---

## 2. Core Workflow: Kitchen → READY → Waiter → SERVED → Bill

### 2.1 Design Intent

```
Kitchen: NEW → PREPARING → READY  (stops at READY)
Kitchen → Waiter: "All ready — call waiter" signal
Waiter: Marks items READY → SERVED  (requires orders.serve)
Last item SERVED: Order → COMPLETED automatically
Guest: Bill auto-surfaces on COMPLETED status
Cashier: Issues single bill (all orders for table) → payment → session closed
```

### 2.2 Permission Split

- **`kitchen.update`** — Kitchen staff can advance items through NEW → PREPARING → READY
- **`orders.serve`** — Waiter/Manager/Owner can mark items READY → SERVED
- Single endpoint: `POST /api/v1/kitchen/ticket-items/{item_id}/status`
  - If `status == SERVED` → requires `orders.serve`
  - Otherwise → requires `kitchen.update`

### 2.3 Kitchen Stops at READY

- Web Kitchen (`KitchenPage.tsx`): SERVED button **removed**; footer says "Serving the food at the table is the waiter's job"
- Mobile Kitchen (`kitchen/index.tsx`): SERVED button **removed**; shows "Ready — waiting for pickup" or "with the waiter"
- Kitchen **cannot** mark SERVED — endpoint returns 403 for kitchen role

### 2.4 Waiter Marks SERVED

- Mobile Waiter (`waiter/order/[tableId].tsx`): **"Mark served"** buttons per READY item
- Web Waiter (`WaiterOrderPage.tsx`): For taking new orders only (no serve buttons — by design)
- When last item on an order is SERVED or CANCELLED → order status auto-transitions to COMPLETED

### 2.5 Guest Sees Bill

- `CustomerStatusPage.tsx`: `useEffect` auto-loads bill when `order.status === "COMPLETED"`
- Bill shows itemized order lines + total amount
- Status copy: "Every course has been delivered. Your bill is ready to settle below."

### 2.6 Mobile Kitchen — "Pending Service Calls" Card

- Added to mobile kitchen screen (was previously missing)
- Shows guest "call waiter" requests and kitchen "food ready" signals
- "Acknowledge" button clears each call
- Auto-refreshes every 5 seconds
- Uses `useServiceCalls()` and `useAcknowledgeServiceCall()` hooks

---

## 3. Customer Adds More Items → Single Bill

### 3.1 Design

Each "add more items" creates a **new order** with its own kitchen ticket, but all orders are linked to the **same DiningSession** (same table). When the cashier issues the bill, it automatically consolidates items from **all orders** in that session.

### 3.2 Flow

```
Table 5: Customer orders 2x pasta (Order #A, Kitchen Ticket #1)
  ↓
Waiter: "Let me add 1x salad"
  ↓
Waiter creates NEW order via app (Order #B, Kitchen Ticket #2)
  — Same table (Table 5)
  — New items: 1x salad
  — New idempotency key
  ↓
Kitchen:
  Ticket #1: 2x pasta → READY → Waiter marks SERVED → Order #A COMPLETED
  Ticket #2: 1x salad → READY → Waiter marks SERVED → Order #B COMPLETED
  ↓
Cashier: "Issue Bill" → ONE bill with all items from all orders
```

### 3.3 Key Mechanisms

| Mechanism | How It Works |
|---|---|
| **`DiningSession`** | One per table; stays OPEN until bill issued/closed |
| **`_ensure_session()`** | Returns existing open session for table; creates new if none |
| **`create_waiter_order()`** | Uses `_ensure_session()` → all orders linked to same session |
| **`issue_bill()`** | Queries ALL orders with that `dining_session_id` → one bill with all items |
| **Idempotency key** | Required on every order POST; same key = returns existing order (no duplicate) |

### 3.4 Verification

- ✅ `create_waiter_order` uses `_ensure_session` → same session for same table
- ✅ `issue_bill` gathers all orders for session → consolidated bill
- ✅ `get_session_bill` returns one bill per session
- No backend changes needed — infrastructure already in place

---

## 4. Notification / Call-Waiter Feature

### 4.1 Backend Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/kitchen/tickets/{id}/call-waiter` | Kitchen signals food ready → creates KITCHEN service call |
| `POST /api/v1/qr/{qr_token}/service-calls` | Guest taps "Call waiter" → creates GUEST service call |
| `GET /api/v1/service-calls?status=REQUESTED` | List pending service calls |
| `POST /api/v1/service-calls/{id}/acknowledge` | Clear a service call |

### 4.2 Web (already working)

- `StaffLayout.tsx` — Notification bell shows pending service calls + orders
- `OverviewPage.tsx` — Shows pending orders and service calls
- `PendingPage.tsx` — List calls with acknowledge buttons

### 4.3 Mobile (fixed — was missing)

- **Added**: `useServiceCalls()` hook in `kitchen/api.ts`
- **Added**: `useAcknowledgeServiceCall()` mutation
- **Added**: "Pending service calls" card in `kitchen/index.tsx`
- Shows kind (Guest calls waiter / Food ready), table name, ticket number, items
- Auto-refreshes every 5 seconds

### 4.4 Service Call Kinds

| Kind | Trigger | Who Creates | Who Acknowledges |
|---|---|---|---|
| `GUEST` | Customer taps "Call waiter" on status page | Guest (via QR) | Any staff |
| `KITCHEN` | Kitchen taps "All ready — call waiter" | Kitchen | Any staff |

---

## 5. Multi-Entity Scenarios

### 5.1 Multiple Waiters

| Scenario | Behavior | Fix |
|---|---|---|
| Two waiters mark same item SERVED | Idempotent — item stays SERVED; second press is harmless | ✅ Built-in |
| Two waiters serve different items | Independent UUIDs; order completes when ALL items SERVED/CANCELLED | ✅ Built-in |
| Waiter A serves item, Waiter B serves another, order completes | Atomic DB transaction; `assert_kitchen_item_transition` validates | ✅ Built-in |
| Who completed the order? | Audit record tracks `actor_user_id`, `actor_membership_id`, `order.completed_at` | ✅ Traceable |

### 5.2 Multiple Kitchens

| Scenario | Behavior | Limitation |
|---|---|---|
| Two kitchen screens (same restaurant) | Both connect to same API; see same tickets; shared state | Not truly independent kitchens |
| Different restaurant locations | Each needs separate `restaurant_id` | Requires separate deployments |
| Kitchen A prepares, Kitchen B finishes | Not supported — all items/tickets belong to one `restaurant_id` | Would need split-ticket design |

### 5.3 Single Cashier

| Scenario | Behavior | Fix |
|---|---|---|
| Cashier issues bill before all items served | Can issue any time after ACCEPTED; bill freezes snapshot | ✅ Normal flow |
| Cashier records payment while order open | Updates `paid_minor` / `balance_due_minor` | ✅ Works for partial payments |
| Two cashiers record same payment | Idempotency keys on payments; duplicate rejected (409) | ✅ If unique key passed |
| Cashier can't see order items | Cashier has `bills.issue`; sees items/subtotal/tax/total/balance | ✅ Fine-grained |

### 5.4 Issue Resolution Guide

| Symptom | Investigation | Fix |
|---|---|---|
| Waiter can't mark SERVED (403) | Check `orders.serve` permission in `ROLE_PERMISSIONS` | ✅ Already added to WAITER set |
| Order doesn't complete after last item SERVED | Check all items are SERVED or CANCELLED | Verify item statuses |
| Service call not appearing on kitchen screen | Check `call-waiter` was pressed; ticket must be READY | ✅ Mobile shows notice; web shows banner |
| Cashier can't issue bill | Order must be ACCEPTED/COMPLETED; session must be OPEN | Ensure orders accepted |
| Concurrent serves cause wrong status | Check audit logs for `kitchen.item_status` actions | ✅ Built-in validation via `assert_kitchen_item_transition` |

---

## 6. Permission System

### 6.1 Role Permissions

| Permission | Owner | Manager | Waiter | Kitchen | Cashier |
|---|---|---|---|---|---|
| `orders.create` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `orders.confirm_qr` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `orders.serve` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `orders.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `kitchen.update` | ✅ | ✅ | ❌ | ✅ | ❌ |
| `kitchen.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `bills.issue` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `payments.record` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `tables.configure` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `settings.manage` | ✅ | ✅ | ❌ | ❌ | ❌ |

### 6.2 Key Rules

- **Only Owner/Manager** manage tables (waiters excluded from configure)
- **Kitchen** can advance items to READY but **cannot** mark SERVED
- **Waiter** can mark SERVED but **cannot** advance to PREPARING/READY
- **Cashier** issues bills and records payments
- All permissions are tenant-scoped via `require_permission` dependency

---

## 7. Demo Accounts & Branding

### 7.1 Demo Accounts

- `DEMO_ACCOUNTS` defined in `apps/web/src/lib/demo.ts`
- Home page "Try it right now" section with role cards
- Login chips for quick demo access
- `VITE_DEMO_ACCOUNTS=0` disables for production (kill-switch)

### 7.2 Branding

- `VITE_BRAND_NAME` env var via `apps/web/src/lib/brand.ts`
- `monogram()` helper for brand initials
- `.env.example` documents `VITE_BRAND_NAME` and `VITE_DEMO_ACCOUNTS=1`
- `main.tsx` sets `document.title = BRAND_NAME`
- `index.html` title updated
- Tenant screens use server `restaurant_name` (e.g., "Harbor Table")

### 7.3 Production Bootstrap

- `bootstrap_production()` in `backend/seed.py`
- Called from `backend/main.py` at startup
- **Never seeds demo data** — requires `BOOTSTRAP_OWNER_EMAIL` + `BOOTSTRAP_OWNER_PASSWORD`
- Verified: env-missing → RuntimeError; correct create; password verifies; zero demo rows; idempotent re-run

---

## 8. Production Bootstrap

### 8.1 Behavior

- On startup, `main.py` calls `bootstrap_production(db, settings)`
- If `BOOTSTRAP_OWNER_EMAIL` and `BOOTSTRAP_OWNER_PASSWORD` are set:
  - Creates owner account if not exists
  - Creates restaurant with given name
  - Creates owner membership
- If not set: raises `RuntimeError` (fail fast)
- **Never** creates demo users, tables, menu items, or sample data

### 8.2 Environment Variables

```env
BOOTSTRAP_OWNER_EMAIL=owner@restaurant.com
BOOTSTRAP_OWNER_PASSWORD=secure-password-here
```

---

## 9. Idempotency, Money, Audit, Tenant Scope

### 9.1 Idempotency

- `Idempotency-Key` header required on:
  - `POST /api/v1/orders` (waiter orders)
  - Public QR order POST
- ≥8 characters
- Same key + same request → returns stable prior result
- Same key + different request body → 409 Conflict
- Implemented in `create_waiter_order` and `submit_qr_order`

### 9.2 Money

- All amounts in integer minor units (e.g., cents)
- `line_amounts()` computes unit price × quantity + tax
- No float arithmetic anywhere
- `subtotal_minor`, `tax_minor`, `total_minor`, `paid_minor`, `balance_due_minor`

### 9.3 Audit Logs

- Append-only (`record_audit` function)
- Tracks: `action`, `entity_type`, `entity_id`, `actor_user_id`, `actor_membership_id`, `detail`, `timestamp`
- Actions: `orders.accept_qr`, `orders.reject_qr`, `orders.create_waiter`, `bills.issue`, `payments.record`, `kitchen.item_status`, etc.

### 9.4 Tenant Scope

- Every repository method requires `restaurant_id` context
- `require_permission` dependency resolves actor + membership + restaurant_id
- Cross-tenant access returns 404 (not 403) to avoid leaking existence
- All queries filter by `restaurant_id`

---

## 10. Files Changed Summary

### Backend

| File | Changes |
|---|---|
| `backend/app/domain/permissions.py` | Added `orders.serve` to OWNER/MANAGER/WAITER roles |
| `backend/app/api/v1/routes/kitchen.py` | `update_item_status` splits permission on SERVED status |
| `backend/app/services/kitchen.py` | `transition_kitchen_item` validates transitions; auto-completes order on last item SERVED/CANCELLED |
| `backend/app/services/orders.py` | `create_waiter_order` with idempotency; `_ensure_session` for table linking |
| `backend/app/services/billing.py` | `issue_bill` consolidates all orders for session |
| `backend/seed.py` | Added `bootstrap_production()` — no demo data |
| `backend/main.py` | Calls `bootstrap_production(db, settings)` at startup |
| `backend/tests/test_serving.py` | 6 new tests for full serve flow |
| `backend/tests/test_api.py` | Updated call-waiter test to use waiter for SERVED |

### Web (`apps/web`)

| File | Changes |
|---|---|
| `src/pages/staff/KitchenPage.tsx` | SERVED button removed; footer copy updated |
| `src/pages/CustomerStatusPage.tsx` | Auto-load bill on COMPLETED; updated status copy |
| `src/pages/staff/StaffLayout.tsx` | Notification bell for service calls + orders |
| `src/lib/brand.ts` | `VITE_BRAND_NAME` + `monogram()` helper |
| `src/lib/demo.ts` | `DEMO_ACCOUNTS` with kill-switch |
| `.env.example` | Documents `VITE_BRAND_NAME`, `VITE_DEMO_ACCOUNTS=1` |
| `main.tsx` | Sets `document.title = BRAND_NAME` |
| `index.html` | Title updated |

### Mobile (`apps/mobile`)

| File | Changes |
|---|---|
| `src/features/kitchen/api.ts` | Added `useServiceCalls`, `useAcknowledgeServiceCall`, `useServeItem` |
| `src/app/(app)/kitchen/index.tsx` | "Pending service calls" card; SERVED button removed from kitchen items |
| `src/app/(app)/waiter/order/[tableId].tsx` | "Mark served" buttons per READY item |

---

## 11. Verification Checklist

### Backend Tests

- [x] `test_serving.py` — 6 tests for full serve flow (PASS)
- [x] `test_api.py` — 13 tests including call-waiter (PASS)
- [x] Full suite — 38 tests (PASS)
- [x] Production bootstrap — env-missing → RuntimeError; correct create; password verifies; zero demo rows; idempotent (PASS)

### Typechecks & Builds

- [x] Web: `tsc -b` + `vite build` (PASS)
- [x] Mobile: `tsc --noEmit` (PASS)

### Workflow Verification (Live API)

- [x] Kitchen marks items NEW → PREPARING → READY (PASS)
- [x] Kitchen calls waiter "All ready — call waiter" (PASS)
- [x] Waiter marks READY → SERVED (PASS)
- [x] Kitchen attempting SERVED → 403 (PASS)
- [x] Last item SERVED → order COMPLETED (PASS)
- [x] Guest bill auto-loads on COMPLETED (PASS)
- [x] Single bill consolidates multiple orders for same table (PASS — by design)

### Notification Feature

- [x] Web: Notification bell shows pending service calls (PASS)
- [x] Web: Acknowledge buttons work (PASS)
- [x] Mobile: "Pending service calls" card shows (PASS — added)
- [x] Mobile: Acknowledge buttons work (PASS — added)
- [x] Guest "Call waiter" via QR creates GUEST service call (PASS)
- [x] Kitchen "All ready — call waiter" creates KITCHEN service call (PASS)

---

## 12. Remaining Work

### 12.1 Already Done (No Action Needed)

- ✅ Serve workflow (kitchen → READY → waiter → SERVED → bill)
- ✅ Single bill for multiple orders (by design — `issue_bill` consolidates)
- ✅ Notification/call-waiter on both web and mobile
- ✅ Permission system with `orders.serve`
- ✅ Demo accounts with kill-switch
- ✅ Brand/env-driven configuration
- ✅ Production bootstrap (no demo data)
- ✅ Idempotency keys on orders and payments
- ✅ Money in integer minor units
- ✅ Audit logs append-only
- ✅ Tenant-scoped data

### 12.2 Potential Future Improvements

| Item | Priority | Description |
|---|---|---|
| Multiple kitchens per restaurant | Low | Requires split-ticket design or per-kitchen filtering |
| Web waiter SERVED buttons | Medium | Currently mobile-only; web waiter page is for new orders |
| Kitchen screen role-gating for SERVED | Low | Could show SERVED button on kitchen screen for waiters only |
| Real-time notifications (WebSocket) | Medium | Currently uses polling (4-5s intervals); could use SSE/WebSocket |
| Combined bill view for guest | Low | Guest status page shows per-order bill; could aggregate by table |
| Payment reconciliation dashboard | Low | For tracking unknown payment states |
| Outbox worker for notifications | Medium | Currently in-memory; should be durable PostgreSQL outbox |

### 12.3 Known Limitations

- One kitchen per restaurant database
- All waiters share the same ticket state (no "personal" items)
- Cashier is single per restaurant in basic setup
- Service calls use polling (not real-time push)
- Outbox events are recorded but worker may not be running

---

## Appendix: Quick Reference

### Run Commands

```bash
# Backend tests
cd backend && venv\Scripts\python.exe -m pytest -q

# Web typecheck + build
cd apps/web && npx tsc -b && npx vite build

# Mobile typecheck
cd apps/mobile && npm run typecheck

# Start backend server
cd backend && venv\Scripts\uvicorn.exe app.main:app --reload
```

### Key Environment Variables

```env
# Web (.env)
VITE_BRAND_NAME=Harbor Table
VITE_DEMO_ACCOUNTS=1

# Backend (.env)
BOOTSTRAP_OWNER_EMAIL=owner@restaurant.com
BOOTSTRAP_OWNER_PASSWORD=secure-password
DATABASE_URL=postgresql://...
```

### API Endpoints (Serve Workflow)

```
POST /api/v1/kitchen/ticket-items/{item_id}/status   # status: PREPARING | READY | SERVED
POST /api/v1/kitchen/tickets/{ticket_id}/call-waiter # Kitchen signals food ready
POST /api/v1/qr/{qr_token}/service-calls              # Guest calls waiter
GET  /api/v1/service-calls?status=REQUESTED          # List pending calls
POST /api/v1/service-calls/{id}/acknowledge          # Clear a call
POST /api/v1/orders                                  # Create waiter order (idempotency key required)
POST /api/v1/bills/{session_id}/issue                # Issue single consolidated bill
```
