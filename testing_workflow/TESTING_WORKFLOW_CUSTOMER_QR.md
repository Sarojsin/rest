# Customer QR Ordering Workflow Tests

**File:** `TESTING_WORKFLOW_CUSTOMER_QR.md`  
**Target:** Customer QR Ordering Surface (Public Realm)  
**URL:** `http://192.168.1.5:5173/t/{qr_token}`  
**Purpose:** Verify customer-facing QR ordering flow end-to-end  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete

---

## Prerequisites

- [ ] Backend running on `http://127.0.0.1:8000`
- [ ] Frontend running on `http://127.0.0.1:5173`
- [ ] Restaurant tenant created with at least one branch
- [ ] Restaurant tables created with QR codes
- [ ] Menu categories and items created
- [ ] QR tokens generated for tables

---

## Workflow QR1: Customer Accesses QR Menu

**Goal:** Customer scans QR code and views menu

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR1.1 | Navigate to `http://192.168.1.5:5173/t/{qr_token}` | Customer menu page loads | ☐ |
| QR1.2 | Restaurant name displayed | Restaurant name shown | ☐ |
| QR1.3 | Menu categories displayed | Categories listed | ☐ |
| QR1.3 | Menu items displayed | Items listed under categories | ☐ |
| QR1.4 | Item details shown | Name, description, price displayed | ☐ |
| QR1.5 | Table display name shown | Correct table name shown | ☐ |

---

## Workflow QR2: Customer Places Order

**Goal:** Customer submits order via QR menu

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR2.1 | Click on menu item | Item added to cart | ☐ |
| QR2.2 | Adjust quantity | Quantity updated | ☐ |
| QR2.3 | Add note to item | Note saved | ☐ |
| QR2.3 | Click "Place Order" | Order created, status PENDING_CONFIRMATION | ☐ |
| QR2.4 | Order confirmation shown | Confirmation message displayed | ☐ |
| QR2.4 | Order ID shown | Order ID displayed | ☐ |
| QR2.4 | Status token shown | Status token displayed | ☐ |

---

## Workflow QR3: Customer Checks Order Status

**Goal:** Customer checks order status via status token

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR3.1 | Navigate to `http://192.168.1.5:5173/status/{status_token}` | Order status page loads | ☐ |
| QR3.2 | Order status displayed | Current status shown | ☐ |
| QR3.2 | Order details shown | Items, total, table shown | ☐ |
| QR3.3 | Status updates in real-time | Status updates as staff changes it | ☐ |

---

## Workflow QR3: Staff Accepts QR Order

**Goal:** Staff accepts customer order

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR3.1 | Login as waiter | Waiter dashboard loads | ☐ |
| QR3.2 | Navigate to Staff → Tables | Tables page loads | ☐ |
| QR3.3 | Table shows occupancy | Table shows "OCCUPIED" or pending order | ☐ |
| QR3.3 | Waiter accepts order | Order status changes to ACCEPTED | ☐ |
| QR3.4 | Dining session created | Session created for order | ☐ |

---

## Workflow QR4: Kitchen Sees Ticket

**Goal:** Kitchen sees order ticket

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR4.1 | Login as kitchen | Dashboard loads | ☐ |
| QR4.2 | Navigate to Kitchen | Kitchen tickets page loads | ☐ |
| QR4.3 | Ticket appears | Order ticket visible | ☐ |
| QR4.3 | Ticket shows items | Order items listed | ☐ |
| QR4.3 | Ticket shows table | Table name shown | ☐ |

---

## Workflow QR5: Kitchen Marks Item Ready

**Goal:** Kitchen marks item ready

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR5.1 | Click item status | Status dropdown opens | ☐ |
| QR5.2 | Select "READY" | Item status changes to READY | ☐ |
| QR5.3 | Ticket shows "Ready" | Ticket marked as ready | ☐ |

---

## Workflow QR6: Kitchen Calls Waiter

**Goal:** Kitchen calls waiter for order pickup

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR6.1 | Click "Call Waiter" button | Service call created | ☐ |
| QR6.2 | Waiter sees service call | Call appears in waiter's view | ☐ |
| QR6.3 | Waiter acknowledges call | Call acknowledged | ☐ |

---

## Workflow QR4: Waiter Sees Service Calls

**Goal:** Waiter sees kitchen calls

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR4.1 | Login as waiter | Dashboard loads | ☐ |
| QR4.2 | Navigate to tables | Tables page loads | ☐ |
| QR4.3 | Service call badge shown | Badge shows count | ☐ |
| QR4.3 | Waiter sees call details | Call details shown | ☐ |

---

## Workflow QR5: Complete Order Flow (End-to-End)

**Goal:** Complete full QR ordering flow

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR5.1 | Customer scans QR | Customer menu loads | ☐ |
| QR5.2 | Customer adds items | Items added to cart | ☐ |
| QR5.3 | Customer places order | Order created, PENDING_CONFIRMATION | ☐ |
| QR5.4 | Waiter accepts order | Order status ACCEPTED | ☐ |
| QR5.5 | Kitchen sees ticket | Ticket appears | ☐ |
| QR5.6 | Kitchen marks ready | Ticket marked ready | ☐ |
| QR5.7 | Kitchen calls waiter | Service call created | ☐ |
| QR5.8 | Waiter sees call | Call appears | ☐ |
| QR5.9 | Waiter delivers order | Order marked delivered | ☐ |
| QR5.10 | Customer sees order status | Status updated on customer screen | ☐ |

---

## Workflow QR6: Customer Status Page

**Goal:** Customer checks order status page

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| QR6.1 | Navigate to `/status/{status_token}` | Status page loads | ☐ |
| QR6.2 | Order status shown | Current status displayed | ☐ |
| QR6.3 | Order details shown | Items, total, table shown | ☐ |
| QR6.3 | Status updates | Status updates as staff changes it | ☐ |

---
