# Restaurant Owner Testing Workflow

**File:** `TESTING_WORKFLOW_RESTAURANT_OWNER.md`  
**Target:** Restaurant Staff (Owner, Manager, Waiter, Kitchen, Cashier)  
**URL:** `http://192.168.1.5:5173/`  
**Backend:** `http://127.0.0.1:8000`  
**Purpose:** Verify staff role-based access and operational workflows  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete  

---

## Testing Standards

### Test Format
Every test case MUST include:
| Field | Description |
|-------|-------------|
| **Test ID** | Unique identifier (e.g., RO-001) |
| **Workflow** | Related business workflow |
| **Priority** | P0 (Critical/Release-blocking) / P1 (High/Pre-production) / P2 (Medium/Operational) |
| **Actor** | Owner, Manager, Waiter, Kitchen, or Cashier |
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
- **Integration Tests**: Database, order-to-kitchen, billing-to-payment
- **E2E Tests**: Complete customer-to-waiter-to-kitchen-to-cashier workflow

---

## Prerequisites

| # | Task | Status |
|---|------|--------|
| P1 | Backend running on `http://127.0.0.1:8000` | ☐ |
| P2 | Frontend running on `http://127.0.0.1:5173` | ☐ |
| P3 | Restaurant tenant created with branches, tables, menu items | ☐ |
| P4 | Staff memberships created for each role (owner, manager, waiter, kitchen, cashier) | ☐ |
| P5 | Staff invitations accepted (passwords set) | ☐ |
| P6 | Test data: tables with QR codes, menu categories and items | ☐ |

---

## Role Permission Matrix (P0)

**Principle of Least Privilege** — Permissions separated into granular operations.

| Permission | Owner | Manager | Waiter | Kitchen | Cashier |
|------------|-------|---------|--------|---------|---------|
| **orders.read** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **orders.create** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **orders.confirm_qr** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **orders.serve** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **orders.reject** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **orders.cancel** | ✅ | ✅* | ❌ | ❌ | ❌ |
| **kitchen.read** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **kitchen.update** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **kitchen.call_waiter** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **bills.issue** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **payments.record** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **payments.refund** | ✅ | ✅** | ❌ | ❌ | ❌ |
| **menu.manage** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **tables.manage** | ✅ | ✅* | ✅ | ❌ | ✅ |
| **tables.assign** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **tables.configure** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **reports.read** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **staff.manage** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **staff.invite** | ✅ | ✅** | ❌ | ❌ | ❌ |
| **staff.update_role** | ✅ | ✅** | ❌ | ❌ | ❌ |
| **staff.deactivate** | ✅ | ✅** | ❌ | ❌ | ❌ |
| **branches.read** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **branches.create** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **branches.assign_staff** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **inventory.read** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **inventory.manage** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **employees.read** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **employees.create** | ✅ | ✅** | ❌ | ❌ | ❌ |
| **loyalty.read** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **loyalty.redeem** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **loyalty.configure** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **reviews.read** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **reviews.create** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **reviews.respond** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **subscriptions.read** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **subscriptions.create** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **subscriptions.manage** | ✅ | ❌ | ❌ | ❌ | ❌ |

*\* Manager requires explicit Owner authorization*  
*\*\* Manager requires explicit Owner delegation*

**Critical**: Manager cannot grant themselves additional permissions. Manager cannot assign staff to branches outside their authorized scope.

---

## Workflow RO-1: Staff Authentication & Sessions (P0)

**Goal:** Verify staff login, session persistence, and security

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-1.1 | P0 | All roles | Login page accessible | None | Navigate to `/login` | Login page renders with email/password fields | | | | |
| RO-1.2 | P0 | All roles | Login page loaded | Staff email | Enter staff email | Email accepted without error | | | | |
| RO-1.3 | P0 | All roles | Email entered | Staff password | Enter password | Password masked | | | | |
| RO-1.4 | P0 | All roles | Credentials valid | Same user | Click "Login" | Redirects to `/staff` (dashboard) | | | | |
| RO-1.5 | P0 | All roles | Dashboard loaded | Same user | Verify role shown | Sidebar shows staff role correctly | | | | |
| RO-1.6 | P0 | All roles | Session active | Same user | Reload page | Session persists | | | | |
| RO-1.7 | P0 | All roles | Authenticated | None | Log out | Redirected to `/login`, session cleared | | | | |
| RO-1.8 | P0 | All roles | Logged out | None | Try accessing `/staff` without login | Redirected to `/login` | | | | |
| RO-1.9 | P0 | Waiter | Authenticated | None | Try MFA enrollment | MFA optional per restaurant policy (not mandatory for all staff) | | | | |
| RO-1.10 | P0 | All roles | Session active | None | Try inactive session after expiry | Redirected to login | | | | |

---

## Workflow RO-2: Owner Dashboard & Overview (P1)

**Goal:** Owner views restaurant overview and KPIs

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-2.1 | P1 | Owner | Authenticated as Owner | None | Login as owner | Dashboard loads | | | | |
| RO-2.2 | P1 | Owner | Dashboard loaded | None | View KPI cards | Tables, orders, sales, staff counts shown | | | | |
| RO-2.3 | P1 | Owner | Dashboard loaded | None | View "Needs attention" section | Pending orders and service calls shown | | | | |
| RO-2.4 | P1 | Owner | Dashboard loaded | None | View shortcuts | Quick links to menu, tables, employees, etc. | | | | |
| RO-2.5 | P1 | Owner | Dashboard loaded | None | View sales report | Gross sales, collected, outstanding shown | | | | |
| RO-2.6 | P1 | Owner | Dashboard loaded | None | View top items | Top selling items listed | | | | |
| RO-2.7 | P1 | Owner | Dashboard loaded | None | View onboarding checklist | Onboarding progress shown | | | | |

---

## Workflow RO-3: Manager - Branch & Staff Management (P1)

**Goal:** Manager manages branches and staff within authorized scope

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-3.1 | P1 | Manager | Authenticated as Manager | None | Login as manager | Dashboard loads | | | | |
| RO-3.2 | P1 | Manager | Dashboard loaded | None | Navigate to Staff → Employees | Employees page loads | | | | |
| RO-3.3 | P1 | Manager | Employees page loaded | None | View staff list | Existing staff listed | | | | |
| RO-3.4 | P1 | Manager | Employees page loaded | Owner authorization | Invite staff with explicit owner authorization | Invitation form opens | | | | |
| RO-3.5 | P1 | Manager | Invite form open | Valid staff data | Fill email, role, name, branch | Form accepts input | | | | |
| RO-3.6 | P1 | Manager | Form complete | Valid staff data | Click "Invite" | Invitation created | | | | |
| RO-3.7 | P1 | Manager | Staff invited | Invited staff | View staff list | New staff appears with status "INVITED" | | | | |
| RO-3.8 | P1 | Manager | Authenticated | None | View branches | Branch list shows | | | | |
| RO-3.9 | P1 | Manager | Branches page loaded | Owner authorization | Create branch | Branch created | | | | |
| RO-3.10 | P1 | Manager | Branch exists | Owner authorization | Edit branch | Branch details updated | | | | |
| RO-3.11 | P1 | Manager | Branch exists | Owner authorization | Deactivate branch | Branch status changes | | | | |
| RO-3.12 | P0 | Manager | Authenticated | None | Try to invite staff without Owner authorization | Denied | | | | |
| RO-3.13 | P0 | Manager | Authenticated | None | Try to create branch without Owner authorization | Denied | | | | |

---

## Workflow RO-4: Waiter - QR Ordering Flow (P0)

**Goal:** Waiter handles guest QR orders

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-4.1 | P0 | Waiter | Authenticated as Waiter | None | Login as waiter | Dashboard loads | | | | |
| RO-4.2 | P0 | Waiter | Dashboard loaded | None | Navigate to Staff → Tables | Tables page loads | | | | |
| RO-4.3 | P0 | Waiter | Tables page loaded | None | View tables with QR codes | Tables listed with QR tokens | | | | |
| RO-4.4 | P0 | Waiter | Tables page loaded | None | Customer submits order (simulate) | Order created, status PENDING_CONFIRMATION | | | | |
| RO-4.5 | P0 | Waiter | Orders page loaded | Pending order | Waiter views orders | Order appears in queue | | | | |
| RO-4.6 | P0 | Waiter | Pending order in queue | Waiter authorized | Waiter accepts order | Order status changes to ACCEPTED | | | | |
| RO-4.7 | P0 | Waiter | Accepted order | Waiter authorized | Waiter creates dining session | Session created | | | | |
| RO-4.8 | P0 | Waiter | Accepted order | Waiter authorized | Waiter tries to accept already accepted order | Rejected: order already accepted | | | | |
| RO-4.9 | P0 | Waiter | Order from another branch | Waiter not authorized | Waiter tries to accept order from another branch | Denied | | | | |
| RO-4.10 | P0 | Waiter | Two waiters, same order | Same pending order | Two waiters attempt to accept same order | Only one succeeds, no duplicate kitchen tickets | | | | |

---

## Workflow RO-5: Kitchen - Kitchen Tickets (P0)

**Goal:** Kitchen manages kitchen tickets

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-5.1 | P0 | Kitchen | Authenticated as Kitchen | None | Login as kitchen | Dashboard loads | | | | |
| RO-5.2 | P0 | Kitchen | Dashboard loaded | None | Navigate to Kitchen | Kitchen tickets page loads | | | | |
| RO-5.3 | P0 | Kitchen | Kitchen page loaded | Accepted order | Ticket appears | Only accepted orders appear | | | | |
| RO-5.4 | P0 | Kitchen | Ticket exists | Ticket ID | Ticket shows items | Order items listed with customizations | | | | |
| RO-5.5 | P0 | Kitchen | Ticket exists | Ticket ID | Ticket shows table | Table name shown | | | | |
| RO-5.6 | P0 | Kitchen | Ticket item exists | Item ID | Update item status to "IN_PROGRESS" | Ticket status changes | | | | |
| RO-5.7 | P0 | Kitchen | Ticket item exists | Item ID | Update item status to "READY" | Ticket status changes | | | | |
| RO-5.8 | P0 | Kitchen | Ticket item READY | Ticket ID | Mark item READY twice | Prevented: duplicate readiness rejected | | | | |
| RO-5.9 | P0 | Kitchen | Ticket item READY | Ticket ID | Kitchen calls waiter | Service call created | | | | |
| RO-5.10 | P0 | Kitchen | Ticket exists | Ticket ID | Kitchen tries to edit menu prices | Denied | | | | |
| RO-5.11 | P0 | Kitchen | Ticket exists | Ticket ID | Kitchen accesses payment records | Denied | | | | |

---

## Workflow RO-6: Cashier - Bills & Payments (P0)

**Goal:** Cashier issues bills and records payments

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-6.1 | P0 | Cashier | Authenticated as Cashier | None | Login as cashier | Dashboard loads | | | | |
| RO-6.2 | P0 | Cashier | Dashboard loaded | None | Navigate to Cashier | Cashier page loads | | | | |
| RO-6.3 | P0 | Cashier | Cashier page loaded | None | View orders needing bills | Orders without bills shown | | | | |
| RO-6.4 | P0 | Cashier | Order without bill | Order ID | Click "Issue Bill" | Bill created | | | | |
| RO-6.5 | P0 | Cashier | Bill exists | Bill ID | Verify bill total | Includes subtotal, tax, discount, total | | | | |
| RO-6.6 | P0 | Cashier | Bill exists | Bill ID | Record cash payment | Payment recorded, balance updated | | | | |
| RO-6.7 | P0 | Cashier | Bill exists | Bill ID | Record QR/bank transfer payment | Payment recorded (pending verification) | | | | |
| RO-6.8 | P0 | Cashier | Payment recorded | Payment ID | Mark bill as paid | Bill status changes | | | | |
| RO-6.9 | P0 | Cashier | Bill exists | Bill ID | Try to pay bill twice | Duplicate payment prevented | | | | |
| RO-6.10 | P0 | Cashier | Bill exists | Bill ID | Payment exceeds outstanding balance | Rejected unless explicitly supported | | | | |
| RO-6.11 | P0 | Cashier | Bill paid | Bill ID | Generate receipt | Receipt generated | | | | |
| RO-6.12 | P0 | Cashier | Outstanding balance | Table session | Prevent session closure with outstanding balance | Session closure blocked until paid | | | | |

---

## Workflow RO-7: Staff Role & Permission Management (P0)

**Goal:** Verify role-based access control at UI and API level

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-7.1 | P0 | Waiter | Authenticated as Waiter | None | Login as waiter | Waiter dashboard loads | | | | |
| RO-7.2 | P0 | Waiter | Waiter dashboard loaded | None | Try to access `/staff/menu` | Denied (waiter has no menu.manage) | | | | |
| RO-7.3 | P0 | Waiter | Waiter dashboard loaded | None | Try to access `/staff/employees` | Denied | | | | |
| RO-7.4 | P0 | Kitchen | Authenticated as Kitchen | None | Login as kitchen | Kitchen dashboard loads | | | | |
| RO-7.5 | P0 | Kitchen | Kitchen dashboard loaded | None | Try to access `/staff/employees` | Denied | | | | |
| RO-7.6 | P0 | Kitchen | Kitchen dashboard loaded | None | Try to access `/staff/menu` | Denied | | | | |
| RO-7.7 | P0 | Cashier | Authenticated as Cashier | None | Login as cashier | Cashier dashboard loads | | | | |
| RO-7.8 | P0 | Cashier | Cashier dashboard loaded | None | Try to access `/staff/employees` | Denied | | | | |
| RO-7.9 | P0 | Cashier | Cashier dashboard loaded | None | Try to access `/staff/menu` | Denied | | | | |
| RO-7.10 | P0 | Manager | Authenticated as Manager | None | Login as manager | Manager dashboard loads | | | | |
| RO-7.11 | P0 | Manager | Manager dashboard loaded | Owner authorization | Access `/staff/employees` | Allowed | | | | |
| RO-7.12 | P0 | Manager | Manager dashboard loaded | Owner authorization | Access `/staff/menu` | Allowed | | | | |
| RO-7.13 | P0 | Owner | Authenticated as Owner | None | Login as owner | Owner dashboard loads | | | | |
| RO-7.14 | P0 | Owner | Owner dashboard loaded | None | Access `/staff/employees` | Allowed | | | | |
| RO-7.15 | P0 | Owner | Owner dashboard loaded | None | Access `/staff/menu` | Allowed | | | | |
| RO-7.16 | P0 | API Client | Waiter token | None | `GET /api/v1/staff/employees` | 403 Forbidden | | | | |
| RO-7.17 | P0 | API Client | Waiter token | None | `POST /api/v1/menu/items` | 403 Forbidden | | | | |
| RO-7.18 | P0 | API Client | Waiter token | None | `PATCH /api/v1/subscriptions/current` | 403 Forbidden | | | | |
| RO-7.19 | P0 | API Client | Waiter token | None | `POST /api/v1/payments/refunds` | 403 Forbidden | | | | |

---

## Workflow RO-8: Owner Subscription Management (P1)

**Goal:** Owner manages restaurant subscription

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-8.1 | P1 | Owner | Authenticated as Owner | None | Login as owner | Dashboard loads | | | | |
| RO-8.2 | P1 | Owner | Dashboard loaded | None | Navigate to Staff → Subscription | Subscription page loads | | | | |
| RO-8.3 | P1 | Owner | Subscription page loaded | None | View current plan | Plan details displayed | | | | |
| RO-8.4 | P1 | Owner | Subscription page loaded | None | View trial end date | Trial end date shown | | | | |
| RO-8.5 | P1 | Owner | Subscription page loaded | None | View features & limits | Features and limits displayed | | | | |
| RO-8.6 | P1 | Owner | Subscription page loaded | None | View usage vs limits | Usage counters shown | | | | |

---

## Workflow RO-9: Staff Invitation Acceptance (P0)

**Goal:** Staff member accepts invitation securely

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-9.1 | P0 | Staff | Invitation email received | Invitation token | Click invitation link | MFA setup page loads (if MFA required by policy) | | | | |
| RO-9.2 | P0 | Staff | Invitation link valid | Valid token | Verify invitation validity | Token valid and not expired | | | | |
| RO-9.3 | P0 | Staff | Invitation link valid | Single-use token | Accept invitation | Token consumed, single-use enforced | | | | |
| RO-9.4 | P0 | Staff | Invitation accepted | Same token | Try to accept again | Already accepted, cannot reuse | | | | |
| RO-9.5 | P0 | Staff | Expired invitation | Expired token | Try to accept expired invitation | Denied | | | | |
| RO-9.6 | P0 | Staff | Revoked invitation | Revoked token | Try to accept revoked invitation | Denied | | | | |
| RO-9.7 | P0 | Staff | Invitation accepted | New staff account | Set up password | Password set successfully | | | | |
| RO-9.8 | P0 | Staff | Password set | MFA optional | MFA enrollment if required by policy | MFA setup if policy requires | | | | |
| RO-9.9 | P0 | Staff | MFA enrolled | Authenticated | Staff redirected to dashboard | Dashboard loads | | | | |
| RO-9.10 | P0 | Staff | Authenticated | None | Staff sees role-specific pages | Role-appropriate menu items shown | | | | |

**Security Note:** Never expose usable invitation tokens in production logs or ordinary UI responses. MFA is a product security policy decision — test separately from invitation acceptance.

---

## Workflow RO-10: Branch Isolation (P0)

**Goal:** Verify staff cannot access unauthorized branches

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-10.1 | P0 | Waiter | Authenticated, assigned to Branch A | Branch B exists | Waiter tries to access Branch A | Authorized | | | | |
| RO-10.2 | P0 | Waiter | Authenticated, assigned to Branch A | Branch B exists | Waiter tries to access Branch B | Denied | | | | |
| RO-10.3 | P0 | Waiter | Authenticated, assigned to Branch A | Branch B table | Waiter tries to access Branch B's table | Denied | | | | |
| RO-10.4 | P0 | Waiter | Authenticated, assigned to Branch A | Branch B order | Waiter tries to access Branch B's order | Denied | | | | |
| RO-10.5 | P0 | Manager | Authenticated, assigned to Branch A | Branch B exists | Manager tries to access Branch A | Authorized | | | | |
| RO-10.6 | P0 | Manager | Authenticated, assigned to Branch A | Branch B exists | Manager tries to access Branch B | Denied (unless explicitly authorized) | | | | |

---

## Workflow RO-11: Order Rejection & Cancellation (P0)

**Goal:** Verify order lifecycle failure scenarios

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-11.1 | P0 | Waiter | Pending order exists | Order ID | Waiter rejects order | Order status: REJECTED | | | | |
| RO-11.2 | P0 | Waiter | Rejected order exists | Order ID | Waiter tries to accept rejected order | Denied: order already rejected | | | | |
| RO-11.3 | P0 | Waiter | Accepted order exists | Order ID | Waiter cancels accepted order | Allowed if policy permits | | | | |
| RO-11.4 | P0 | Customer | Pending order exists | Order ID | Customer cancels before preparation | Allowed if policy permits | | | | |
| RO-11.5 | P0 | Customer | Preparation started | Order ID | Customer tries to cancel after preparation | Denied: preparation started | | | | |
| RO-11.6 | P0 | Staff | Invalid transition | Order ID | Staff attempts invalid status transition | Denied: invalid transition | | | | |
| RO-11.7 | P0 | Kitchen | Rejected order exists | Order ID | Rejected order appears in kitchen | Denied: rejected orders don't reach kitchen | | | | |

---

## Workflow RO-12: Multiple Customers & Dining Sessions (P0)

**Goal:** Verify multiple customers can order from same table

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-12.1 | P0 | Customer A | Table QR scanned | Table ID | Customer A scans QR | Table context loads | | | | |
| RO-12.2 | P0 | Customer B | Same table QR | Table ID | Customer B scans same QR | Table context loads (same table) | | | | |
| RO-12.3 | P0 | Customer A | Cart created | Items added | Customer A adds items to cart | Cart A contains Customer A's items | | | | |
| RO-12.4 | P0 | Customer B | Cart created | Items added | Customer B adds items to cart | Cart B contains Customer B's items | | | | |
| RO-12.5 | P0 | Customer A | Cart A submitted | Order A | Customer A submits order | Order A created under Table ID | | | | |
| RO-12.6 | P0 | Customer B | Cart B submitted | Order B | Customer B submits order | Order B created under Table ID | | | | |
| RO-12.7 | P0 | Staff | Orders A and B exist | Order A, Order B | Staff views orders | Both orders appear under correct table | | | | |
| RO-12.8 | P0 | Customer A | Order A submitted | Order A ID | Customer A tracks order | Customer A sees only Order A status | | | | |
| RO-12.9 | P0 | Customer B | Order B submitted | Order B ID | Customer B tracks order | Customer B sees only Order B status | | | | |
| RO-12.10 | P0 | Staff | Two orders same table | Dining session | Staff verifies dining session | Orders associated with correct dining session | | | | |

**Key Rule:** Each customer device has its own cart and order-status token. Table can have multiple orders.

---

## Workflow RO-13: Kitchen Item-Level Lifecycle (P0)

**Goal:** Verify individual item preparation tracking

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-13.1 | P0 | Kitchen | Accepted order with multiple items | Multi-item order | Kitchen receives ticket | Ticket shows all items | | | | |
| RO-13.2 | P0 | Kitchen | Multi-item ticket | Item 1 | Kitchen marks Item 1 as READY | Item 1 status: READY | | | | |
| RO-13.3 | P0 | Kitchen | Item 1 READY | Item 2 | Item 2 still PENDING | Item 2 NOT automatically marked READY | | | | |
| RO-5.14 | P0 | Kitchen | Multi-item ticket | None | Item customizations visible | Customization notes shown | | | | |
| RO-13.15 | P0 | Kitchen | Ticket exists | None | Item quantities visible | Correct quantities shown | | | | |

---

## Workflow RO-14: Customer & Kitchen Service Calls (P1)

**Goal:** Verify service call coordination

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-14.1 | P1 | Customer | Order delivered | Table ID | Customer presses Call Waiter | Service call created (type: CUSTOMER_REQUEST) | | | | |
| RO-14.2 | P1 | Customer | Service call created | Call ID | Customer presses button again | Duplicate calls prevented or grouped | | | | |
| RO-14.3 | P1 | Waiter | Service call exists | Call ID | Waiter receives notification | Correct table and call type shown | | | | |
| RO-14.4 | P1 | Waiter | Service call acknowledged | Call ID | Waiter acknowledges call | Call status: ACKNOWLEDGED | | | | |
| RO-14.5 | P1 | Customer | Call acknowledged | Call ID | Customer views call status | Customer sees acknowledgement | | | | |
| RO-14.6 | P1 | Waiter | Call unacknowledged | Call ID | Waiter does not acknowledge | Call remains pending and visible | | | | |
| RO-14.7 | P1 | Kitchen | Food ready | Order ID | Kitchen calls waiter | Service call created (type: KITCHEN_READY) | | | | |
| RO-14.8 | P1 | Waiter | Kitchen call exists | Call ID | Waiter receives notification | Distinguishable from customer request | | | | |

**Distinction:** Customer call vs Kitchen call are different service-call types.

---

## Workflow RO-15: Bill Aggregation & Settlement (P0)

**Goal:** Verify bill creation and payment settlement

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-15.1 | P0 | Cashier | Dining session with orders | Session ID | Cashier opens table/session bill | Bill generated | | | | |
| RO-15.2 | P0 | Cashier | Bill exists | Bill ID | Bill includes all eligible orders | All orders in session included | | | | |
| RO-15.3 | P0 | Cashier | Bill exists | Bill ID | Verify bill calculations | Subtotal, tax, discount, total correct | | | | |
| RO-15.6 | P0 | Cashier | Bill exists | Bill ID | Record cash payment | Payment recorded | | | | |
| RO-15.17 | P0 | Cashier | Bill paid | Bill ID | Generate receipt | Receipt generated | | | | |
| RO-15.18 | P0 | Cashier | Outstanding balance | Table session | Prevent session closure with unpaid balance | Session closure blocked | | | | |

---

## Workflow RO-16: Refunds & Payment Integrity (P0)

**Goal:** Verify refund operations

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-16.1 | P0 | Owner | Payment exists | Payment ID | Create refund | Refund created | | | | |
| RO-16.2 | P0 | Owner | Refund created | Refund ID | Partial refund | Partial refund accepted | | | | |
| RO-16.3 | P0 | Owner | Refund exists | Refund ID | Full refund | Full refund accepted | | | | |
| RO-16.4 | P0 | Owner | Refund exceeds paid amount | Refund ID | Refund exceeding paid amount | Rejected | | | | |
| RO-16.5 | P0 | Owner | Unauthorized role | Refund ID | Waiter tries to issue refund | Denied | | | | |
| RO-16.6 | P0 | Owner | Refund issued | Refund ID | Audit event created | Audit event logged | | | | |

---

## Workflow RO-17: Staff Invitation Lifecycle (P1)

**Goal:** Verify staff invitation management

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-17.1 | P1 | Owner | Authenticated as Owner | None | Invite new staff | Invitation created | | | | |
| RO-17.2 | P1 | Owner | Invitation exists | Invitation ID | Resend invitation | New token issued | | | | |
| RO-17.3 | P1 | Owner | Resent invitation | Old token | Previous token invalidated | Old token no longer valid | | | | |
| RO-17.4 | P1 | Owner | Invitation exists | Expired token | Invitation expires | Cannot be accepted after expiry | | | | |
| RO-17.5 | P1 | Owner | Invitation exists | Revoked token | Revoke invitation | Revoked, cannot be accepted | | | | |
| RO-17.6 | P1 | Owner | Invitation accepted | Accepted token | Try to accept again | Already accepted, cannot reuse | | | | |

---

## Workflow RO-18: Concurrency & Duplicate Requests (P1)

**Goal:** Verify concurrent operation handling

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-18.1 | P1 | Two waiters | Same pending order | Order ID | Two waiters accept same order | Only one succeeds | | | | |
| RO-18.2 | P1 | Customer | Cart exists | Cart ID | Double-click Place Order | Only one order created | | | | |
| RO-18.3 | P1 | Customer | Network lost during submission | Cart ID | Retry submission | No duplicate order (idempotency key) | | | | |
| RO-18.4 | P1 | Two cashiers | Same bill | Bill ID | Two cashiers record payment | Only one payment accepted | | | | |
| RO-18.5 | P1 | Customer | Cart exists | Cart ID | Refresh before submitting | Cart behavior matches persistence policy | | | | |

---

## Workflow RO-19: Subscription Feature Enforcement (P0)

**Goal:** Verify backend enforces plan features and limits

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-19.1 | P0 | Owner | Plan limit exists | Limit reached | Try to exceed plan limit | Backend enforces limit | | | | |
| RO-19.2 | P0 | Owner | Downgrade plan | Lower plan | Downgrade below current usage | Blocked or grandfathered per policy | | | | |
| RO-19.3 | P0 | Owner | Feature disabled | Feature ID | Try to use disabled feature | Denied | | | | |
| RO-19.4 | P0 | Owner | Plan changed | New plan | Verify feature access changes | Features reflect new plan immediately | | | | |

---

## Workflow RO-20: Staff Session Security (P0)

**Goal:** Verify staff session security

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-20.1 | P0 | Staff | Authenticated session | Session ID | Expired token | Session invalidated | | | | |
| RO-20.2 | P0 | Staff | Logged out | Session ID | Try to use old session | Denied | | | | |
| RO-20.3 | P0 | Staff | Revoked access | Session ID | Try to access after revocation | Denied | | | | |
| RO-20.4 | P0 | Staff | Staff account deactivated | Session ID | Try to access with deactivated account | Denied | | | | |
| RO-20.5 | P0 | Staff | Forged role request | Staff ID | Staff tries to change own role via API | Denied | | | | |

---

## Workflow RO-21: Audit History (P1)

**Goal:** Verify staff actions are audited

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| RO-21.1 | P1 | Owner | Staff action performed | Staff ID | Owner invites staff | Audit event: staff invited | | | | |
| RO-21.2 | P1 | Owner | Staff action performed | Staff ID | Owner updates staff role | Audit event: staff role updated | | | | |
| RO-21.3 | P1 | Cashier | Payment recorded | Payment ID | Cashier records payment | Audit event: payment recorded | | | | |
| RO-21.4 | P1 | Owner | Sensitive data | None | Verify no passwords/TOTP in logs | No sensitive data in audit logs | | | | |

---

## Testing Execution Tracker

| Section | Total Tests | Passed | Failed | Blocked | Not Tested | % Complete |
|---------|-------------|--------|--------|---------|------------|------------|
| RO-1 Authentication & Sessions | 10 | 0 | 0 | 0 | 10 | 0% |
| RO-2 Owner Dashboard | 7 | 0 | 0 | 0 | 7 | 0% |
| RO-3 Manager Branch & Staff | 13 | 0 | 0 | 0 | 13 | 0% |
| RO-4 Waiter QR Ordering | 10 | 0 | 0 | 0 | 10 | 0% |
| RO-5 Kitchen Tickets | 11 | 0 | 0 | 0 | 11 | 0% |
| RO-6 Cashier Bills & Payments | 12 | 0 | 0 | 0 | 12 | 0% |
| RO-7 Role & Permission Management | 19 | 0 | 0 | 0 | 19 | 0% |
| RO-8 Owner Subscription | 6 | 0 | 0 | 0 | 6 | 0% |
| RO-9 Staff Invitation Acceptance | 10 | 0 | 0 | 0 | 10 | 0% |
| RO-10 Branch Isolation | 6 | 0 | 0 | 0 | 6 | 0% |
| RO-11 Order Rejection & Cancellation | 7 | 0 | 0 | 0 | 7 | 0% |
| RO-12 Multiple Customers & Sessions | 10 | 0 | 0 | 0 | 10 | 0% |
| RO-13 Kitchen Item Lifecycle | 5 | 0 | 0 | 0 | 5 | 0% |
| RO-14 Service Calls | 8 | 0 | 0 | 0 | 8 | 0% |
| RO-15 Bill Aggregation & Settlement | 8 | 0 | 0 | 0 | 8 | 0% |
| RO-16 Refunds & Payment Integrity | 6 | 0 | 0 | 0 | 6 | 0% |
| RO-17 Staff Invitation Lifecycle | 6 | 0 | 0 | 0 | 6 | 0% |
| RO-18 Concurrency & Duplicates | 5 | 0 | 0 | 0 | 5 | 0% |
| RO-19 Subscription Feature Enforcement | 4 | 0 | 0 | 0 | 4 | 0% |
| RO-20 Staff Session Security | 5 | 0 | 0 | 0 | 5 | 0% |
| RO-21 Audit History | 4 | 0 | 0 | 0 | 4 | 0% |
| **TOTAL** | **155** | **0** | **0** | **0** | **155** | **0%** |

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
**Staff URL:** `http://192.168.1.5:5173/staff/`  
**Database:** PostgreSQL `restaurant`  
**Alembic Head:** `pa0016`