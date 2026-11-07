# Restaurant Staff Testing Workflow

**File:** `TESTING_WORKFLOW_RESTAURANT_STAFF.md`  
**Target:** Restaurant Staff (Owner, Manager, Waiter, Kitchen, Cashier)  
**URL:** `http://192.168.1.5:5173/`  
**Purpose:** Verify staff role-based access and operational workflows  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete

---

## Prerequisites

- [ ] Backend running on `http://127.0.0.1:8000`
- [ ] Frontend running on `http://127.0.0.1:5173`
- [ ] Restaurant tenant created with branches, tables, menu items
- [ ] Staff memberships created for each role (owner, manager, waiter, kitchen, cashier)
- [ ] Staff invitations accepted (passwords set)
- [ ] Test data: tables with QR codes, menu categories and items

---

## Staff Role Permissions Reference

| Permission | Owner | Manager | Waiter | Kitchen | Cashier |
|------------|-------|---------|--------|---------|---------|
| orders.read | ✅ | ✅ | ✅ | ✅ | ✅ |
| orders.create | ✅ | ✅ | ✅ | ❌ | ✅ |
| orders.confirm_qr | ✅ | ✅ | ✅ | ❌ | ❌ |
| orders.serve | ✅ | ✅ | ✅ | ❌ | ❌ |
| kitchen.read | ✅ | ✅ | ✅ | ✅ | ✅ |
| kitchen.update | ✅ | ✅ | ❌ | ✅ | ❌ |
| bills.issue | ✅ | ✅ | ❌ | ❌ | ✅ |
| payments.record | ✅ | ✅ | ❌ | ❌ | ✅ |
| menu.manage | ✅ | ✅ | ❌ | ❌ | ❌ |
| tables.manage | ✅ | ✅ | ✅ | ❌ | ✅ |
| reports.read | ✅ | ✅ | ✅ | ❌ | ✅ |
| staff.manage | ✅ | ❌ | ❌ | ❌ | ❌ |
| branches.read | ✅ | ✅ | ✅ | ❌ | ✅ |
| branches.create | ✅ | ✅ | ❌ | ❌ | ❌ |
| inventory.read | ✅ | ✅ | ✅ | ✅ | ❌ |
| inventory.manage | ✅ | ✅ | ❌ | ❌ | ❌ |
| employees.read | ✅ | ✅ | ❌ | ❌ | ❌ |
| employees.create | ✅ | ✅ | ❌ | ❌ | ❌ |
| loyalty.read | ✅ | ✅ | ✅ | ❌ | ✅ |
| loyalty.manage | ✅ | ✅ | ❌ | ❌ | ✅ |
| loyalty.redeem | ✅ | ✅ | ❌ | ❌ | ✅ |
| reviews.read | ✅ | ✅ | ✅ | ❌ | ❌ |
| reviews.create | ✅ | ✅ | ✅ | ❌ | ❌ |
| reviews.respond | ✅ | ✅ | ❌ | ❌ | ❌ |
| subscriptions.read | ✅ | ✅ | ❌ | ❌ | ✅ |
| subscriptions.create | ✅ | ✅ | ❌ | ❌ | ❌ |
| subscriptions.manage | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## Workflow S1: Staff Login

**Goal:** Staff member logs into restaurant dashboard

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S1.1 | Navigate to `/login` | Login page loads | ☐ |
| S1.2 | Enter staff email | Email accepted | ☐ |
| S1.3 | Enter password | Password masked | ☐ |
| S1.4 | Click Login | Redirects to `/staff` (dashboard) | ☐ |
| S1.5 | Verify role shown | Sidebar shows staff role | ☐ |
| S1.6 | Reload page | Session persists | ☐ |

**Test each role:** owner, manager, waiter, kitchen, cashier

---

## Workflow S2: Owner Dashboard & Overview

**Goal:** Owner views restaurant overview

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S2.1 | Login as owner | Dashboard loads | ☐ |
| S2.2 | View KPI cards | Tables, orders, sales, staff counts shown | ☐ |
| S2.3 | View "Needs attention" section | Pending orders and service calls shown | ☐ |
| S2.4 | View shortcuts | Quick links to menu, tables, employees, etc. | ☐ |
| S2.5 | View sales report | Gross sales, collected, outstanding shown | ☐ |
| S2.6 | View top items | Top selling items listed | ☐ |
| S2.7 | View onboarding checklist | Onboarding progress shown | ☐ |

---

## Workflow S3: Manager - Branch & Staff Management

**Goal:** Manager manages branches and staff

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S3.1 | Login as manager | Dashboard loads | ☐ |
| S3.2 | Navigate to Staff → Employees | Employees page loads | ☐ |
| S3.3 | View staff list | Existing staff listed | ☐ |
| S3.3 | Click "Invite Staff" | Invite form opens | ☐ |
| S3.4 | Fill email, role, name, branch | Form accepts input | ☐ |
| S3.5 | Click "Invite" | Invitation created | ☐ |
| S3.6 | View branches | Branch list shows | ☐ |
| S3.7 | Create branch | Branch created | ☐ |
| S3.7 | Edit branch | Branch details updated | ☐ |
| S3.8 | Deactivate branch | Branch status changes | ☐ |

---

## Workflow S4: Waiter - QR Ordering Flow

**Goal:** Waiter handles guest QR orders

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S4.1 | Login as waiter | Dashboard loads | ☐ |
| S4.2 | Navigate to Staff → Tables | Tables page loads | ☐ |
| S4.3 | View tables with QR codes | Tables listed with QR tokens | ☐ |
| S4.3 | Scan QR code (simulate customer) | Customer menu page loads | ☐ |
| S4.4 | Customer submits order | Order created, status PENDING_CONFIRMATION | ☐ |
| S4.5 | Waiter views orders | Order appears in queue | ☐ |
| S4.6 | Waiter accepts order | Order status changes to ACCEPTED | ☐ |
| S4.7 | Waiter creates dining session | Session created | ☐ |

---

## Workflow S5: Kitchen - Kitchen Tickets

**Goal:** Kitchen manages kitchen tickets

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S5.1 | Login as kitchen | Dashboard loads | ☐ |
| S5.2 | Navigate to Kitchen | Kitchen tickets page loads | ☐ |
| S5.3 | Wait for order accepted | Ticket appears | ☐ |
| S5.3 | Update item status to "IN_PROGRESS" | Ticket status changes | ☐ |
| S5.4 | Update item status to "READY" | Ticket status changes | ☐ |
| S5.4 | Kitchen calls waiter | Service call created | ☐ |

---

## Workflow S6: Cashier - Bills & Payments

**Goal:** Cashier issues bills and records payments

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S6.1 | Login as cashier | Dashboard loads | ☐ |
| S6.2 | Navigate to Cashier | Cashier page loads | ☐ |
| S6.3 | View orders needing bills | Orders without bills shown | ☐ |
| O6.4 | Click "Issue Bill" | Bill created | ☐ |
| O6.5 | Record payment | Payment recorded, balance updated | ☐ |
| O6.7 | Mark bill as paid | Bill status changes | ☐ |

---

## Workflow S7: Manager - Manage Staff Roles

**Goal:** Manager manages staff roles and branches

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| S7.1 | Login as manager | Dashboard loads | ☐ |
| S7.2 | Navigate to Staff → Employees | Employees page loads | ☐ |
| S7.3 | Invite new staff | Invitation created | ☐ |
| S7.4 | Edit staff role | Role updated | ☐ |
| S7.5 | Change branch assignment | Branch assignment updated | ☐ |
| S7.6 | Deactivate staff | Staff status changed to inactive | ☐ |

---

## Workflow S8: Owner - Manage Subscription

**Goal:** Owner manages restaurant subscription

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| O9.1 | Login as owner | Dashboard loads | ☐ |
| O9.2 | Navigate to Staff → Subscription | Subscription page loads | ☐ |
| O9.3 | View current plan | Plan details displayed | ☐ |
| O9.3 | View trial end date | Trial end date shown | ☐ |
| O9.4 | View features & limits | Features and limits displayed | ☐ |
| O9.5 | View usage vs limits | Usage counters shown | ☐ |

---

## Workflow O14: Owner - Manage Staff via Employees Page

**Goal:** Owner manages staff from dashboard

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| O14.1 | Login as owner | Dashboard loads | ☐ |
| O14.2 | Navigate to Staff → Employees | Employees page loads | ☐ |
| O14.3 | View staff list | Staff listed with roles | ☐ |
| O14.4 | Invite new staff | Invitation form opens | ☐ |
| O14.5 | Fill email, role, name, phone, branch | Form accepts input | ☐ |
| O14.6 | Click "Invite" | Invitation created | ☐ |
| O14.7 | Invitation token displayed | Token shown | ☐ |
| O14.8 | Seat limit enforced | If limit reached, error shown | ☐ |

---

## Workflow O15: Staff Invitation Acceptance

**Goal:** Staff member accepts invitation

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| O15.1 | Staff receives invitation link | Link received | ☐ |
| O15.2 | Click invitation link | MFA setup page loads | ☐ |
| O15.3 | Set up MFA | QR code scanned, code verified | ☐ |
| O15.4 | Staff redirected to dashboard | Dashboard loads | ☐ |
| O15.5 | Staff sees role-specific pages | Role-appropriate menu items shown | ☐ |

---

## Workflow O16: Role-Based Access Control

**Goal:** Verify role-based access control

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| O16.1 | Login as waiter | Waiter dashboard loads | ☐ |
| O16.2 | Try to access /staff/menu | Should be denied (waiter has no menu.manage) | ☐ |
| O16.3 | Login as kitchen | Kitchen dashboard loads | ☐ |
| O16.4 | Try to access /staff/employees | Should be denied | ☐ |
| O16.5 | Login as cashier | Cashier dashboard loads | ☐ |
| O16.6 | Try to access /staff/employees | Should be denied | ☐ |
| O16.7 | Login as manager | Manager dashboard loads | ☐ |
| O16.8 | Access /staff/employees | Should be allowed | ☐ |

---

## Workflow O17: QR Ordering Flow (End-to-End)

**Goal:** Complete QR ordering flow from customer to kitchen

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| O17.1 | Scan table QR code | Customer menu page loads | ☐ |
| O17.2 | Browse menu categories | Categories and items displayed | ☐ |
| O17.3 | Add items to cart | Items added | ☐ |
| O17.4 | Submit order | Order created, status PENDING_CONFIRMATION | ☐ |
| O17.5 | Waiter sees order | Order appears in queue | ☐ |
| O17.6 | Waiter accepts order | Order status ACCEPTED | ☐ |
| O17.7 | Kitchen sees ticket | Ticket appears in kitchen view | ☐ |
| O17.8 | Kitchen marks item ready | Ticket status changes | ☐ |
| O17.8 | Kitchen calls waiter | Service call created | ☐ |
| O17.9 | Waiter sees service call | Service call appears | ☐ |

---
