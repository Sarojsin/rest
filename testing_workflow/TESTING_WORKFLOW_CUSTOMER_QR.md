# Customer QR Ordering Workflow Tests

**File:** `TESTING_WORKFLOW_CUSTOMER_QR.md`  
**Target:** Customer QR Ordering Surface (Public Realm)  
**URL:** `http://192.168.1.5:5173/t/{qr_token}`  
**Backend:** `http://127.0.0.1:8000`  
**Purpose:** Verify customer-facing QR ordering flow end-to-end  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete  

---

## Testing Standards

### Test Format
Every test case MUST include:
| Field | Description |
|-------|-------------|
| **Test ID** | Unique identifier (e.g., QR-001) |
| **Workflow** | Related business workflow |
| **Priority** | P0 (Critical/Release-blocking) / P1 (High/Pre-production) / P2 (Medium/Operational) |
| **Actor** | Customer, Waiter, Kitchen, Cashier |
| **Preconditions** | Required initial state |
| **Test Data** | Exact test account and records |
| **Action** | What the tester does |
| **Expected Result** | Expected UI and backend behavior |
| **Actual Result** | What happened (filled during testing) |
| **Status** | Pass / Fail / Blocked / Not Tested |
| **Evidence** | Screenshot, API response, log |
| **Bug ID** | Related defect if failed |

### Testing Levels
- **UI Tests**: Buttons, pages, forms, navigation
- **API Tests**: Authorization, validation, business rules
- **Integration Tests**: Frontend, backend, database work together
- **E2E Tests**: Complete customer-to-waiter-to-kitchen-to-cashier workflow

---

## Prerequisites

| # | Task | Status |
|---|------|--------|
| P1 | Backend running on `http://127.0.0.1:8000` | ☐ |
| P2 | Frontend running on `http://127.0.0.1:5173` | ☐ |
| P3 | Restaurant tenant created with at least one branch | ☐ |
| P4 | Restaurant tables created with QR codes | ☐ |
| P5 | Menu categories and items created | ☐ |
| P6 | QR tokens generated for tables | ☐ |

---

## Workflow QR1: QR Access & Table Identification (P0)

**Goal:** Customer scans QR code and identifies correct restaurant, branch, and table

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-1.1 | P0 | Customer | Valid QR token | QR token | Navigate to `http://192.168.1.5:5173/t/{qr_token}` | Correct restaurant, branch, and table load | | | | |
| QR-1.2 | P0 | Customer | Invalid QR token | Invalid token | Navigate to invalid QR URL | Clear invalid-QR page; no menu/order access | | | | |
| QR-1.3 | P0 | Customer | Expired QR token | Expired token | Navigate to expired QR URL | Access denied | | | | |
| QR-1.4 | P0 | Customer | Another table QR | Different table QR | Open another table's QR | That table's context loads | | | | |
| QR-1.5 | P0 | Customer | Another tenant QR | Different tenant QR | Open QR from another tenant | No data from another restaurant exposed | | | | |
| QR-1.6 | P0 | Customer | QR page loaded | Table ID | Refresh the menu page | Table context remains correct | | | | |

**Critical:** Backend resolves table from QR token and establishes correct tenant/branch context. Never trust tenant_id, branch_id, or table_id supplied by browser.

---

## Workflow QR2: Menu Loading, Categories, Search & Filtering (P1)

**Goal:** Customer browses menu correctly

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-2.1 | P1 | Customer | Menu page loaded | None | Menu categories displayed | Categories listed | | | | |
| QR-2.2 | P1 | Customer | Categories visible | Category ID | Click on category | Items under category displayed | | | | |
| QR-2.3 | P1 | Customer | Menu page loaded | None | Search by dish name | Matching items shown | | | | |
| QR-2.4 | P1 | Customer | Menu page loaded | None | Filter by category | Items filtered correctly | | | | |
| QR-2.5 | P1 | Customer | Empty category | Empty category | View empty category | Empty state shown appropriately | | | | |
| QR-2.6 | P1 | Customer | Empty menu | No items | View empty menu | Empty menu state shown | | | | |

---

## Workflow QR3: Item Details, Variants & Availability (P0)

**Goal:** Customer views item details with correct availability

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-3.1 | P0 | Customer | Menu item visible | Item ID | Click on menu item | Item details shown (name, description, price) | | | | |
| QR-3.2 | P0 | Customer | Active item | Active item | View active item | Item available for ordering | | | | |
| QR-3.3 | P0 | Customer | Inactive item | Inactive item | View inactive item | Item not orderable | | | | |
| QR-3.4 | P0 | Customer | Out-of-stock item | Out-of-stock item | View out-of-stock item | Item marked unavailable | | | | |
| QR-3.5 | P0 | Customer | Item with variants | Variant item | Select variant | Variant price and details shown | | | | |
| QR-3.6 | P0 | Customer | Item with add-ons | Add-on item | View add-ons | Add-ons and extra ingredients shown | | | | |
| QR-3.7 | P0 | Customer | Required customization | Required customization | View required customization | Customization required before adding to cart | | | | |
| QR-3.8 | P0 | Customer | Optional customization | Optional customization | View optional customization | Customization optional | | | | |
| QR-3.9 | P0 | Customer | Price change during cart | Item in cart | Price changes while item in cart | Backend applies current valid price or requests confirmation | | | | |
| QR-3.10 | P0 | Customer | Disabled item | Disabled item | Item disabled while menu open | Item removed or marked unavailable | | | | |

**Critical:** Backend calculates final order price from trusted menu data. Never trust price submitted by customer frontend.

---

## Workflow QR4: Cart & Quantity Management (P0)

**Goal:** Customer manages cart correctly

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-4.1 | P0 | Customer | Menu page loaded | Item ID | Add multiple items | All items appear correctly in cart | | | | |
| QR-4.2 | P0 | Customer | Item in cart | Cart ID | Increase/decrease quantity | Quantity and subtotal update | | | | |
| QR-4.3 | P0 | Customer | Item in cart | Cart ID | Remove an item | Item removed from cart | | | | |
| QR-4.4 | P0 | Customer | Item in cart | Cart ID | Add item-specific note | Note attached to correct item | | | | |
| QR-4.5 | P0 | Customer | Cart exists | Cart ID | Add order-level note | Note attached to order | | | | |
| QR-4.6 | P0 | Customer | Cart exists | Cart ID | Enter maximum quantity | Configured quantity limit enforced | | | | |
| QR-4.7 | P0 | Customer | Empty cart | None | Submit empty cart | Submission rejected | | | | |
| QR-4.8 | P0 | Customer | Unavailable items | Cart ID | Submit order with unavailable items | Validation error; unavailable items cannot be ordered | | | | |
| QR-4.9 | P0 | Customer | Cart exists | Cart ID | Change item price before submission | Backend applies current valid price or requests confirmation | | | | |

---

## Workflow QR5: Order Submission & Idempotency (P0)

**Goal:** Customer submits order with idempotency protection

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-5.1 | P0 | Customer | Cart with items | Cart ID | Click "Place Order" | Order created, status PENDING_CONFIRMATION | | | | |
| QR-5.2 | P0 | Customer | Order submitted | Order ID | Order confirmation shown | Confirmation message displayed | | | | |
| QR-5.3 | P0 | Customer | Order submitted | Order ID | Order ID shown | Order ID displayed | | | | |
| QR-5.4 | P0 | Customer | Order submitted | Order ID | Status token shown | Status token displayed | | | | |
| QR-5.5 | P0 | Customer | Order submitted | Idempotency key | Double-click Place Order | Only one order created | | | | |
| QR-5.6 | P0 | Customer | Network lost | Cart ID | Lose network during submission and retry | No duplicate order created | | | | |
| QR-5.7 | P0 | Customer | Same idempotency key | Same payload | Reuse idempotency key with same payload | Original result returned | | | | |
| QR-5.8 | P0 | Customer | Same idempotency key | Different payload | Reuse idempotency key with different payload | Conflict/rejection according to policy | | | | |

**Critical:** Idempotency key must survive retries/reloads. Repeated request with same key must not create another order.

---

## Workflow QR6: Multiple Customers Ordering from One Table (P0)

**Goal:** Multiple customers can order from same table independently

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-6.1 | P0 | Customer A | Table QR scanned | Table ID | Customer A scans QR | Table context loads | | | | |
| QR-6.2 | P0 | Customer B | Same table QR | Table ID | Customer B scans same QR | Table context loads (same table) | | | | |
| QR-6.3 | P0 | Customer A | Cart created | Items added | Customer A adds items to cart | Cart A contains Customer A's items | | | | |
| QR-6.4 | P0 | Customer B | Cart created | Items added | Customer B adds items to cart | Cart B contains Customer B's items | | | | |
| QR-6.5 | P0 | Customer A | Cart A submitted | Order A | Customer A submits order | Order A created under Table ID | | | | |
| QR-6.6 | P0 | Customer B | Cart B submitted | Order B | Customer B submits order | Order B created under Table ID | | | | |
| QR-6.7 | P0 | Staff | Orders A and B exist | Order A, Order B | Staff views orders | Both orders appear under correct table | | | | |
| QR-6.8 | P0 | Customer A | Order A submitted | Order A ID | Customer A tracks order | Customer A sees only Order A status | | | | |
| QR-6.9 | P0 | Customer B | Order B submitted | Order B ID | Customer B tracks order | Customer B sees only Order B status | | | | |
| QR-6.10 | P0 | Staff | Two orders same table | Dining session | Staff verifies dining session | Orders associated with correct dining session | | | | |

**Key Rule:** Each customer device has its own cart and order-status token. Table can have multiple orders.

---

## Workflow QR7: Staff Confirmation & Order Rejection (P0)

**Goal:** Waiter confirms or rejects customer orders

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-7.1 | P0 | Waiter | Authenticated as Waiter | None | Login as waiter | Waiter dashboard loads | | | | |
| QR-7.2 | P0 | Waiter | Waiter dashboard loaded | None | Navigate to Staff → Tables | Tables page loads | | | | |
| QR-7.3 | P0 | Waiter | Tables page loaded | Pending order | Table shows occupancy | Table shows "OCCUPIED" or pending order | | | | |
| QR-7.4 | P0 | Waiter | Pending order | Order ID | Waiter accepts order | Order status changes to ACCEPTED | | | | |
| QR-7.5 | P0 | Waiter | Accepted order | Order ID | Waiter tries to accept already accepted order | Rejected: order already accepted | | | | |
| QR-7.6 | P0 | Waiter | Pending order | Order ID | Waiter rejects order | Order status: REJECTED | | | | |
| QR-7.7 | P0 | Waiter | Rejected order | Order ID | Waiter tries to accept rejected order | Denied: order already rejected | | | | |
| QR-7.8 | P0 | Waiter | Order from another branch | Waiter not authorized | Waiter tries to accept order from another branch | Denied | | | | |
| QR-7.9 | P0 | Kitchen | Rejected order | Order ID | Rejected order appears in kitchen | Denied: rejected orders don't reach kitchen | | | | |

---

## Workflow QR8: Dining Session & Table Occupancy (P0)

**Goal:** Verify dining session creation and table occupancy rules

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-8.1 | P0 | Waiter | Accepted order | Order ID | First accepted order creates dining session | Dining session created | | | | |
| QR-8.2 | P0 | Waiter | Dining session exists | Session ID | Another order from same table joins session | Order joins existing session | | | | |
| QR-8.3 | P0 | Customer | Pending order | Order ID | Two customers ordering from same table | Both associated with correct session | | | | |
| QR-8.4 | P0 | Customer | Pending order | Order ID | Pending order does not create duplicate sessions | No duplicate sessions | | | | |
| QR-8.5 | P0 | Staff | Table occupancy | Table ID | Table occupancy changes at correct point | Occupancy changes when order accepted (or per policy) | | | | |
| QR-8.6 | P0 | Staff | Completed session | Session ID | Completed and paid dining session can be closed | Session closed | | | | |
| QR-8.7 | P0 | Customer | New customer | Table ID | New customer uses table after previous session closes | New customer can use table | | | | |
| QR-8.8 | P0 | Customer | Old status token | Old token | Old status token cannot access new dining session's orders | Denied | | | | |

**Key Distinction:** Pending order and occupied table are not necessarily the same. Define exact occupancy rule.

---

## Workflow QR9: Kitchen Ticket & Item Preparation (P0)

**Goal:** Kitchen manages order tickets and item preparation

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-9.1 | P0 | Kitchen | Authenticated as Kitchen | None | Login as kitchen | Dashboard loads | | | | |
| QR-9.2 | P0 | Kitchen | Kitchen page loaded | Accepted order | Ticket appears | Only accepted orders appear | | | | |
| QR-9.3 | P0 | Kitchen | Ticket exists | Ticket ID | Ticket shows items | Order items listed | | | | |
| QR-9.4 | P0 | Kitchen | Ticket exists | Ticket ID | Ticket shows table | Table name shown | | | | |
| QR-9.5 | P0 | Kitchen | Ticket item exists | Item ID | Item quantities visible | Correct quantities shown | | | | |
| QR-9.6 | P0 | Kitchen | Ticket item exists | Item ID | Item customizations visible | Customization notes shown | | | | |
| QR-9.7 | P0 | Kitchen | Ticket item exists | Item ID | Update item to IN_PROGRESS | Item status changes | | | | |
| QR-9.8 | P0 | Kitchen | Ticket item exists | Item ID | Update item to READY | Item status changes | | | | |
| QR-9.9 | P0 | Kitchen | Ticket item READY | Item ID | Mark item READY twice | Duplicate readiness rejected | | | | |
| QR-9.10 | P0 | Kitchen | Multi-item ticket | Item 1 READY | Item 2 still PENDING | Item 2 NOT automatically marked READY | | | | |
| QR-9.11 | P0 | Kitchen | Ticket exists | Ticket ID | Kitchen tries to edit menu prices | Denied | | | | |
| QR-9.12 | P0 | Kitchen | Ticket exists | Ticket ID | Kitchen accesses payment records | Denied | | | | |
| QR-9.13 | P0 | Kitchen | New ticket | Ticket ID | New orders appear without manual refresh | Orders appear in real-time or after refresh interval | | | | |

---

## Workflow QR10: Kitchen Calls Waiter (P1)

**Goal:** Kitchen calls waiter when items ready

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-10.1 | P1 | Kitchen | Ticket item READY | Ticket ID | Kitchen calls waiter | Service call created (type: KITCHEN_READY) | | | | |
| QR-10.2 | P1 | Waiter | Kitchen call exists | Call ID | Waiter receives notification | Distinguishable from customer request | | | | |
| QR-10.3 | P1 | Waiter | Multiple calls | Multiple calls | Multiple calls for same order handled correctly | Calls grouped or handled individually | | | | |
| QR-10.4 | P1 | Kitchen | Multiple items READY | Multiple items | Kitchen calls waiter multiple times | Each call tracked separately | | | | |

---

## Workflow QR11: Customer Calls Waiter (P1)

**Goal:** Customer can call waiter

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-11.1 | P1 | Customer | Order delivered | Table ID | Customer presses Call Waiter | Service call created (type: CUSTOMER_REQUEST) | | | | |
| QR-11.2 | P1 | Customer | Service call created | Call ID | Customer presses button again | Duplicate calls prevented or grouped | | | | |
| QR-11.3 | P1 | Waiter | Service call exists | Call ID | Waiter receives notification | Correct table and call type shown | | | | |
| QR-11.4 | P1 | Waiter | Service call acknowledged | Call ID | Waiter acknowledges call | Call status: ACKNOWLEDGED | | | | |
| QR-11.5 | P1 | Customer | Call acknowledged | Call ID | Customer views call status | Customer sees acknowledgement | | | | |
| QR-11.6 | P1 | Waiter | Call unacknowledged | Call ID | Waiter does not acknowledge | Call remains pending and visible | | | | |
| QR-11.7 | P1 | Customer | Another table | Table ID | Customer calls from another table | Call associated with correct table | | | | |

**Distinction:** Customer call vs Kitchen call are different service-call types.

---

## Workflow QR12: Waiter Acknowledges & Delivers (P0)

**Goal:** Waiter acknowledges calls and delivers food

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-12.1 | P0 | Waiter | Service call exists | Call ID | Waiter acknowledges call | Call status: ACKNOWLEDGED | | | | |
| QR-12.2 | P0 | Waiter | Call acknowledged | Call ID | Acknowledged call disappears | Call removed from pending queue | | | | |
| QR-12.3 | P0 | Waiter | Order ready | Order ID | Waiter delivers food | Order/item delivery status updated | | | | |
| QR-12.4 | P0 | Waiter | Order delivered | Order ID | Order marked delivered | Delivery status confirmed | | | | |

---

## Workflow QR13: Customer Order-Status Tracking (P0)

**Goal:** Customer tracks order status

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-13.1 | P0 | Customer | Status token | Status token | Navigate to `/status/{status_token}` | Order status page loads | | | | |
| QR-13.2 | P0 | Customer | Status page loaded | Order ID | Order status displayed | Current status shown | | | | |
| QR-13.3 | P0 | Customer | Status page loaded | Order ID | Order details shown | Items, total, table shown | | | | |
| QR-13.4 | P0 | Customer | Status page loaded | Order ID | Status updates in real-time | Status updates as staff changes it | | | | |
| QR-13.5 | P0 | Customer | Invalid token | Invalid token | Navigate to invalid status URL | Access denied | | | | |
| QR-13.6 | P0 | Customer | Expired token | Expired token | Navigate to expired status URL | Access denied | | | | |
| QR-13.7 | P0 | Customer | Another customer's token | Different token | Try to access another customer's order | Denied | | | | |
| QR-13.8 | P0 | Customer | Status page loaded | Order ID | Refresh status page | Status persists | | | | |
| QR-13.9 | P0 | Customer | Status page loaded | Order ID | Status changes while page open | Status updates without reload | | | | |
| QR-13.10 | P0 | Customer | Multi-item order | Order ID | Multiple items with different statuses | Each item status shown separately | | | | |
| QR-13.11 | P0 | Customer | Rejected order | Order ID | Rejected order explanation | Rejection reason shown | | | | |
| QR-13.12 | P0 | Customer | Delivered order | Order ID | Delivered order confirmation | Delivery confirmed | | | | |

**Real-time:** Test actual mechanism (polling, SSE, or WebSockets). Don't assume real-time updates.

---

## Workflow QR14: Billing & Payment (P0)

**Goal:** Customer completes payment

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-14.1 | P0 | Cashier | Dining session with orders | Session ID | Cashier opens table/session bill | Bill generated | | | | |
| QR-14.2 | P0 | Cashier | Bill exists | Bill ID | Bill includes all eligible orders | All orders in session included | | | | |
| QR-14.3 | P0 | Cashier | Bill exists | Bill ID | Verify bill calculations | Subtotal, tax, discount, total correct | | | | |
| QR-14.4 | P0 | Customer | Bill exists | Bill ID | Customer chooses payment method | Available payment methods shown | | | | |
| QR-14.5 | P0 | Cashier | Cash payment | Bill ID | Record cash payment | Payment recorded | | | | |
| QR-14.6 | P0 | Cashier | Online payment | Bill ID | Record QR/bank transfer payment | Payment recorded (pending verification) | | | | |
| QR-14.7 | P0 | Cashier | Bill paid | Bill ID | Generate receipt | Receipt generated | | | | |
| QR-14.8 | P0 | Cashier | Duplicate payment | Bill ID | Try to pay bill twice | Duplicate payment prevented | | | | |
| QR-14.9 | P0 | Cashier | Excessive payment | Bill ID | Payment exceeds outstanding balance | Rejected unless explicitly supported | | | | |
| QR-14.10 | P0 | Cashier | Pending payment | Bill ID | Payment pending verification | Payment marked pending | | | | |
| QR-14.11 | P0 | Cashier | Failed payment | Bill ID | Failed payment recorded | Payment marked failed | | | | |
| QR-14.12 | P0 | Cashier | Refund request | Payment ID | Refund or payment reversal | Refund processed (if supported) | | | | |
| QR-14.13 | P0 | Cashier | Unpaid balance | Table session | Close session with unpaid balance | Session closure blocked until paid | | | | |
| QR-14.14 | P0 | Online payment | Webhook payload | Webhook | Test webhook signature verification | Valid signature accepted, invalid rejected | | | | |

**Critical:** Showing payment success in frontend ≠ money received. Online payments verified via provider callbacks. Manual QR transfers need authorized verification.

---

## Workflow QR15: Receipt & Session Closure (P1)

**Goal:** Customer receives receipt and session closes

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-15.1 | P1 | Cashier | Bill paid | Bill ID | Generate receipt | Receipt generated with correct details | | | | |
| QR-15.2 | P1 | Customer | Receipt generated | Receipt ID | Customer views receipt | Receipt displayed | | | | |
| QR-15.3 | P1 | Cashier | Session paid | Session ID | Close session | Session closed | | | | |
| QR-15.4 | P1 | Customer | Session closed | Table ID | New customer uses table | New customer can use table | | | | |
| QR-15.5 | P1 | Customer | Old status token | Old token | Old token cannot access new session | Denied | | | | |

---

## Workflow QR16: Customer Feedback & Rating (P2)

**Goal:** Customer submits feedback after service

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-16.1 | P2 | Customer | Eligible order | Order ID | Customer submits rating | Rating submitted | | | | |
| QR-16.2 | P2 | Customer | Rating submitted | Rating ID | Customer tries to rate another customer's order | Denied | | | | |
| QR-16.3 | P2 | Customer | Rating submitted | Rating ID | Duplicate rating | Handled according to policy | | | | |
| QR-16.4 | P2 | Customer | Rating submitted | Rating ID | Rating associated with correct restaurant/branch | Correct association | | | | |

---

## Workflow QR17: Security & Tenant Isolation (P0)

**Goal:** Public QR surface security testing

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-17.1 | P0 | Customer | Status token | Another token | Guess another status token | Cannot access another order | | | | |
| QR-17.2 | P0 | API Client | Order ID | Forged ID | Change order ID in API request | Cannot access/modify another order | | | | |
| QR-17.3 | P0 | Customer | Frontend price | Fake price | Submit fake price from frontend | Backend ignores/rejects | | | | |
| QR-17.4 | P0 | Customer | Another tenant item | Tenant B item | Submit another tenant's item ID | Backend rejects | | | | |
| QR-17.5 | P0 | Customer | Another branch table | Tenant B table | Submit another branch's table ID | Backend rejects | | | | |
| QR-17.6 | P0 | Customer | Malformed data | Invalid data | Send malformed order data | Validation error, no corrupted order | | | | |
| QR-17.7 | P0 | Customer | Rate limit | Multiple requests | Send excessive order requests | Rate limiting or abuse protection | | | | |
| QR-17.8 | P0 | Customer | Revoked QR | Revoked token | Use revoked QR token | Access denied | | | | |
| QR-17.9 | P0 | Customer | Staff API | Staff endpoint | Attempt staff-only API from customer session | Unauthorized | | | | |
| QR-17.10 | P0 | Customer | Long notes | Long text | Submit excessively long notes | Input limits enforced | | | | |
| QR-17.11 | P0 | Customer | HTML injection | Script tags | Inject HTML/script in notes | Content safely handled | | | | |

**Critical:** Public endpoints must not expose staff emails, internal user IDs, private customer info, or backend details.

---

## Workflow QR18: Network Failures & Retry Handling (P0)

**Goal:** Verify network failure resilience

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-18.1 | P0 | Customer | Menu page | None | Slow network loading | Page loads within acceptable time | | | | |
| QR-18.2 | P0 | Customer | Menu loading | None | Network disconnect during menu loading | Error shown, retry option | | | | |
| QR-18.3 | P0 | Customer | Order submission | Cart ID | Network disconnect during submission | Error shown, retry with same idempotency key | | | | |
| QR-18.4 | P0 | Customer | Large menu | Many items | Large menu with many categories/items | Page loads and is usable | | | | |
| QR-18.5 | P0 | Customer | Large images | Product images | Large product images | Images load or fallback shown | | | | |
| QR-18.6 | P0 | Customer | 3D model | 3D model | 3D model loading failure | Ordering remains usable without 3D model | | | | |
| QR-18.7 | P0 | Customer | Rapid taps | Buttons | Rapid repeated button taps | No duplicate actions | | | | |

---

## Workflow QR19: Mobile Responsiveness & Performance (P1)

**Goal:** Verify mobile experience

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| QR-19.1 | P1 | Customer | Android | None | QR page on Android screen size | Page renders correctly | | | | |
| QR-19.2 | P1 | Customer | iPhone | None | QR page on iPhone screen size | Page renders correctly | | | | |
| QR-19.3 | P1 | Customer | Low-end device | None | Page performance on low-end mobile | Usable performance | | | | |
| QR-19.4 | P1 | Customer | Accessibility | None | Readable contrast, touch-target sizes | Accessibility standards met | | | | |
| QR-19.5 | P1 | Customer | Reduced motion | None | Reduced-motion preference respected | Animations reduced or disabled | | | | |

---

## Recommended End-to-End Product Flow

```
Customer → Restaurant → Payment
1. Customer scans table QR
   → Restaurant, branch and table identified
2. Customer browses menu
   → Categories, dishes, prices, availability, details
3. Customer builds cart
   → Quantities, customizations, item notes, order notes
4. Customer submits order
   → Backend validates, creates pending order
5. Waiter confirms order
   → Accepted orders enter restaurant workflow
6. Kitchen prepares food
   → Kitchen sees accepted items, updates preparation status
7. Kitchen calls waiter
   → Waiter receives and acknowledges pickup request
8. Waiter delivers food
   → Order/item delivery status updated
9. Cashier handles bill
   → All orders associated with dining session included
10. Customer pays
    → Cashier-verified or online payment recorded
11. Session closes
    → Payment and outstanding balance reconciled
12. Customer gives feedback
    → Rating linked to correct restaurant/branch
```

**Critical Separation:** Customer ordering and customer tracking remain separate public capabilities. QR token identifies table; order-status token identifies specific order. Never use QR token as authorization to retrieve every order from that table.

---

## Testing Execution Tracker

| Section | Total Tests | Passed | Failed | Blocked | Not Tested | % Complete |
|---------|-------------|--------|--------|---------|------------|------------|
| QR-1 QR Access & Table ID | 6 | 0 | 0 | 0 | 6 | 0% |
| QR-2 Menu Loading & Filtering | 6 | 0 | 0 | 0 | 6 | 0% |
| QR-3 Item Details & Availability | 10 | 0 | 0 | 0 | 10 | 0% |
| QR-4 Cart & Quantity | 9 | 0 | 0 | 0 | 9 | 0% |
| QR-5 Order Submission & Idempotency | 8 | 0 | 0 | 0 | 8 | 0% |
| QR-6 Multiple Customers & Table | 10 | 0 | 0 | 0 | 10 | 0% |
| QR-7 Staff Confirmation & Rejection | 9 | 0 | 0 | 0 | 9 | 0% |
| QR-8 Dining Session & Occupancy | 8 | 0 | 0 | 0 | 8 | 0% |
| QR-9 Kitchen Ticket & Preparation | 13 | 0 | 0 | 0 | 13 | 0% |
| QR-10 Kitchen Calls Waiter | 4 | 0 | 0 | 0 | 4 | 0% |
| QR-11 Customer Calls Waiter | 7 | 0 | 0 | 0 | 7 | 0% |
| QR-12 Waiter Acknowledges & Delivers | 4 | 0 | 0 | 0 | 4 | 0% |
| QR-13 Customer Status Tracking | 12 | 0 | 0 | 0 | 12 | 0% |
| QR-14 Billing & Payment | 14 | 0 | 0 | 0 | 14 | 0% |
| QR-15 Receipt & Session Closure | 5 | 0 | 0 | 0 | 5 | 0% |
| QR-16 Feedback & Rating | 4 | 0 | 0 | 0 | 4 | 0% |
| QR-17 Security & Isolation | 11 | 0 | 0 | 0 | 11 | 0% |
| QR-18 Network Failures & Retry | 7 | 0 | 0 | 0 | 7 | 0% |
| QR-19 Mobile Responsiveness | 5 | 0 | 0 | 0 | 5 | 0% |
| **TOTAL** | **131** | **0** | **0** | **0** | **131** | **0%** |

---

## Bug Tracking Template

| Bug ID | Section | Test Case | Description | Severity | Status | Fix Verified |
|--------|---------|-----------|-------------|----------|--------|--------------|
| BUG-001 | | | | | | |
| BUG-002 | | | | | | |
| BUG-003 | | | | | | |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| QA Lead | | | |
| Product Owner | | | |
| Dev Lead | | | |

---

## Testing Environment

**Backend URL:** `http://127.0.0.1:8000`  
**Frontend URL:** `http://192.168.1.5:5173`  
**Customer URL:** `http://192.168.1.5:5173/t/{qr_token}`  
**Status URL:** `http://192.168.1.5:5173/status/{status_token}`  
**Database:** PostgreSQL `restaurant`  
**Alembic Head:** `pa0016`