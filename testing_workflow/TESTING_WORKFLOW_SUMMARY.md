# Master Testing Checklist

**File:** `TESTING_WORKFLOW_SUMMARY.md`  
**Target:** Complete Restaurant SaaS Platform  
**URL:** `http://192.168.1.5:5173/` (Staff/Customer), `http://192.168.1.5:5173/admin/` (Platform Console)  
**Purpose:** Master checklist covering ALL workflows across all user roles  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete

---

## Pre-Deployment Checklist

| # | Task | Status |
|---|------|--------|
| P1 | Backend running on port 8000 | ☐ |
| P2 | Frontend running on port 5173 | ☐ |
| P3 | Database migrated to latest Alembic head | ☐ |
| P4 | Super admin created (platform@harbor.example) | ☐ |
| P5 | Browser cache cleared (Ctrl+Shift+R) | ☐ |

---

## Section 1: Platform Admin Console (Super Admin)

**URL:** `http://192.168.1.5:5173/admin/`  
**Credentials:** `platform@harbor.example` / `PlatformOwner!1`

| # | Test Case | Status | Notes |
|---|---------|--------|-------|
| A1 | Login with superadmin credentials | ☐ |
| A2 | MFA enrollment (QR code + verify) | ☐ |
| A3 | Login with MFA | ☐ |
| A4 | View Dashboard | ☐ |
| A5 | View Tenants list | ☐ |
| A6 | Create restaurant via onboarding wizard | ☐ |
| A6a | Step 1: Organization details | ☐ |
| A27 | Step 2: Owner account | ☐ |
| A28 | Step 3: Subscription plan | ☐ |
| A29 | Step 4: Branches | ☐ |
| A30 | Step 5: Review & Create | ☐ |
| A31 | View tenant detail page | ☐ |
| A32 | Edit tenant profile | ☐ |
| A33 | Suspend tenant | ☐ |
| A34 | Reactivate tenant | ☐ |
| A35 | Force logout tenant | ☐ |
| A36 | Create plan | ☐ |
| A37 | Create plan version | ☐ |
| A38 | Publish plan version | ☐ |
| A39 | Add plan feature | ☐ |
| A40 | Add plan limit | ☐ |
| A41 | View subscriptions | ☐ |
| A42 | Change subscription plan | ☐ |
| A43 | View invoices | ☐ |
| A44 | View payments | ☐ |
| A45 | View refunds | ☐ |
| A46 | View platform users | ☐ |
| A47 | Create platform user | ☐ |
| A48 | View audit log | ☐ |
| A49 | View platform settings | ☐ |
| A50 | Enable MFA enrollment | ☐ |
| A51 | Cancel tenant | ☐ |
| A52 | Data export tenant | ☐ |
| A53 | Anonymize tenant | ☐ |

---

## Section 2: Restaurant Owner Onboarding

**URL:** `http://192.168.1.5:5173/` (after invitation acceptance)

| # | Test Case | Status |
|---|---------|--------|
| O1 | Receive invitation email/token | ☐ |
| O2 | Click invitation link | ☐ |
| O3 | Generate MFA secret (QR code) | ☐ |
| O4 | Scan QR with authenticator app | ☐ |
| O5 | Enter 6-digit code, verify | ☐ |
| O6 | Dashboard loads | ☐ |
| O7 | View setup checklist | ☐ |
| O8 | Complete restaurant profile | ☐ |
| O9 | Create branch | ☐ |
| O10 | Configure tables | ☐ |
| O11 | Generate QR codes | ☐ |
| O12 | Configure menu categories | ☐ |
| O13 | Configure menu items | ☐ |
| O14 | Invite staff members | ☐ |
| O15 | Configure payment methods | ☐ |
| O16 | Checklist reaches 100% | ☐ |
| O17 | View subscription details | ☐ |
| O18 | View usage vs limits | ☐ |

---

## Workflow Section 3: Restaurant Staff Roles

### 3A: Manager

| # | Test Case | Status |
|---|---------|--------|
| M1 | Login as manager | ☐ |
| M2 | View dashboard | ☐ |
| M3 | View branches | ☐ |
| M4 | Create branch | ☐ |
| M5 | Edit branch | ☐ |
| M6 | Invite staff | ☐ |
| M7 | Edit staff role/branch | ☐ |
| M8 | View orders | ☐ |
| M9 | Accept order | ☐ |
| M10 | View reports | ☐ |

### 3B: Waiter

| # | Test Case | Status |
|---|---------|--------|
| W1 | Login as waiter | ☐ |
| W2 | View tables | ☐ |
| W3 | View pending orders | ☐ |
| W4 | Accept order | ☐ |
| W5 | Create dining session | ☐ |
| W6 | View kitchen tickets | ☐ |
| W7 | See service calls | ☐ |
| W8 | Acknowledge service call | ☐ |

### 3C: Kitchen

| # | Test Case | Status |
|---|---------|--------|
| K1 | Login as kitchen | ☐ |
| K2 | View kitchen tickets | ☐ |
| K3 | Mark item IN_PROGRESS | ☐ |
| K3 | Mark item READY | ☐ |
| K4 | Call waiter | ☐ |

### 3D: Cashier

| # | Test Case | Status |
|---|---------|--------|
| C1 | Login as cashier | ☐ |
| C2 | View orders without bills | ☐ |
| C3 | Issue bill | ☐ |
| C3 | Record payment | ☐ |
| C4 | Mark bill paid | ☐ |

---

## Workflow Section 4: Customer QR Ordering (End-to-End)

| # | Test Case | Status |
|---|---------|--------|
| Q1 | Scan/table QR → menu loads | ☐ |
| Q2 | Browse categories | ☐ |
| Q3 | Add items to cart | ☐ |
| Q4 | Adjust quantity | ☐ |
| Q5 | Add note to item | ☐ |
| Q6 | Submit order | ☐ |
| Q7 | Order status PENDING_CONFIRMATION | ☐ |
| Q8 | Waiter accepts order | ☐ |
| Q9 | Kitchen sees ticket | ☐ |
| Q10 | Kitchen marks item ready | ☐ |
| Q11 | Kitchen calls waiter | ☐ |
| Q12 | Waiter sees service call | ☐ |
| Q13 | Customer checks status page | ☐ |

---

## Workflow Section 5: Role-Based Access Control (RBAC)

**Verify that each role CANNOT access unauthorized pages:**

| # | Role | Page to Test | Expected Result | Status |
|---|------|--------------|-----------------|--------|
| R1 | Waiter | /staff/menu | 403 Forbidden | ☐ |
| R2 | Waiter | /staff/employees | 403 Forbidden | ☐ |
| R3 | Kitchen | /staff/employees | 403 Forbidden | ☐ |
| R4 | Kitchen | /staff/menu | 403 Forbidden | ☐ |
| R5 | Cashier | /staff/employees | 403 Forbidden | ☐ |
| R6 | Cashier | /staff/menu | 403 Forbidden | ☐ |
| R7 | Manager | /staff/menu | Allowed | ☐ |
| R8 | Manager | /staff/employees | Allowed | ☐ |
| R9 | Owner | /staff/employees | Allowed | ☐ |
| R10 | Owner | /staff/menu | Allowed | ☐ |

---

## Workflow Section 5: Self-Service Registration (Public)

**Goal:** Test public restaurant registration

| # | Test Case | Status |
|---|---------|--------|
| S1 | Navigate to `/admin/register` | Registration page loads | ☐ |
| S2 | Fill registration form | Form accepts input | ☐ |
| S3 | Submit registration | Registration created, PENDING status | ☐ |
| S4 | Admin approves registration | Registration status APPROVED | ☐ |
| S5 | Owner receives invitation | Invitation email/token generated | ☐ |
| O15.6 | Owner activates account | Dashboard loads | ☐ |

---

## Workflow Section 6: System-Wide Edge Cases

| # | Test Case | Expected Result | Status |
|---|---------|-----------------|--------|
| E1 | Login with wrong password | 401 error shown | ☐ |
| E2 | Login with expired session | Redirect to login | ☐ |
| E3 | Access protected page without login | Redirect to /login | ☐ |
| E4 | Invite staff over seat limit | 409 SEAT_LIMIT_REACHED | ☐ |
| E5 | Downgrade plan over limit | 409 DOWNGRADE_LIMIT_EXCEEDED | ☐ |
| E6 | Duplicate restaurant slug | 409 SLUG_TAKEN | ☐ |
| E7 | Duplicate owner email | 409 OWNER_EMAIL_EXISTS | ☐ |
| E8 | Cancel already cancelled tenant | 409 TENANT_ALREADY_CANCELLED | ☐ |
| E9 | Anonymize non-cancelled tenant | 409 TENANT_NOT_CANCELLED | ☐ |

---

## Test Execution Tracker

| Section | Total Tests | Passed | Failed | Skipped | % Complete |
|---------|-------------|--------|--------|---------|------------|
| Admin Console | 53 | 0 | 0 | 53 | 0% |
| Restaurant Owner | 16 | 0 | 0 | 16 | 0% |
| Staff (Owner/Manager) | 10 | 0 | 0 | 10 | 0% |
| Staff (Waiter) | 8 | 0 | 0 | 8 | 0% |
| Staff (Kitchen) | 4 | 0 | 0 | 4 | 0% |
| Staff (Cashier) | 4 | 0 | 0 | 4 | 0% |
| Customer QR | 13 | 0 | 0 | 13 | 0% |
| RBAC | 10 | 0 | 0 | 10 | 0% |
| Self-Service | 6 | 0 | 0 | 6 | 0% |
| Edge Cases | 9 | 0 | 0 | 9 | 0% |
| **TOTAL** | **145** | **0** | **0** | **145** | **0%** |

---

## Daily Testing Checklist

| Date | Tester | Section | Passed | Failed | Notes |
|------|--------|---------|--------|--------|-------|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

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

**Testing Environment:** Local Development  
**Backend URL:** `http://127.0.0.1:8000`  
**Frontend URL:** `http://192.168.1.5:5173`  
**Admin URL:** `http://192.168.1.5:5173/admin/`  
**Database:** PostgreSQL `restaurant`  
**Alembic Head:** `pa0016`

---
