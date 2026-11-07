# Admin Console Testing Workflow

**File:** `TESTING_WORKFLOW_ADMIN_CONSOLE.md`  
**Target:** Platform Console (Super Admin, OPS, Billing, Support)  
**URL:** `http://192.168.1.5:5173/admin/`  
**Purpose:** Verify all platform-level admin functionality end-to-end  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete

---

## Prerequisites

- [ ] Backend running on `http://127.0.0.1:8000` (health check: `/health` returns 200)
- [ ] Frontend dev server running on `http://127.0.0.1:5173`
- [ ] Database migrated to latest Alembic head (`pa0016`)
- [ ] At least one Super Admin exists in `platform_admins` table

---

## Workflow A1: Platform Admin Login & Authentication

**Goal:** Verify platform realm authentication with MFA

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A1.1 | Navigate to `/admin/login` | Login page renders with email/password fields | ☐ |
| A1.2 | Enter email: `platform@harbor.example` | Email accepted without error | ☐ |
| A1.3 | Enter password: `PlatformOwner!1` | Password masked | ☐ |
| A1.4 | Click "Continue" | 401 response if MFA not enrolled; redirects to `/admin/mfa` | ☐ |
| A1.5 | Click "Generate authenticator secret" | Secret + QR code displayed | ☐ |
| A1.6 | Scan QR code with authenticator app | App accepts code | ☐ |
| A1.7 | Enter 6-digit code, click "Verify and finish" | Redirected to `/admin/` (Dashboard) | ☐ |
| A1.8 | Reload page | Session persists (cookie-based) | ☐ |
| A1.9 | Click "Sign out" | Redirected to `/admin/login`, session cleared | ☐ |

**Notes:** Platform login is MFA-gated. First login requires MFA enrollment.

---

## Workflow A2: Admin Dashboard

**Goal:** Verify dashboard renders and shows platform stats

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A2.1 | Navigate to `/admin` | Dashboard page loads | ☐ |
| A2.2 | Verify sidebar shows "Dashboard" as active | Highlighted navigation item | ☐ |
| A2.3 | Verify admin info displays (name, email, role, MFA status) | Correct info shown | ☐ |
| A2.4 | Verify Foundation status section | Lists platform identity realm, HttpOnly cookies, MFA, audit log | ☐ |
| A2.5 | Verify "Coming next" section | Lists plan 04 modules | ☐ |

---

## Workflow A3: Tenants (Restaurant Management)

**Goal:** CRUD operations for restaurant tenants

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A3.1 | Navigate to `/admin/tenants` | Tenants page loads | ☐ |
| A3.2 | Verify table shows restaurant list | Initially empty or shows existing tenants | ☐ |
| A3.2 | Click "Create" button | Redirects to `/onboarding` | ☐ |
| A3.3 | Filter by status (ACTIVE/SUSPENDED/CANCELLED) | Table filters correctly | ☐ |
| A3.4 | Search by name/slug | Results filter in real-time | ☐ |
| A3.5 | Click on a tenant row | Opens tenant detail page | ☐ |

**Note:** The "Create" button redirects to the onboarding wizard (`/onboarding`).

---

## Workflow A4: Onboarding Wizard (Create Restaurant)

**Goal:** Complete multi-step restaurant onboarding

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A4.1 | Navigate to `/admin/onboarding` | Onboarding page loads | ☐ |
| A4.2 | Step 1: Organization Details | Form accepts restaurant name, slug, contact email, phone, country, address, timezone, currency | ☐ |
| A4.3 | Step 2: Owner Account | Form accepts owner full name, email, phone | ☐ |
| A4.3 | Step 3: Subscription Plan | Select plan, trial days, billing interval | ☐ |
| A4.4 | Step 4: Branches | Add at least 1 branch with name, code, address | ☐ |
| A4.5 | Step 5: Review & Create | Summary shows all entered data | ☐ |
| A4.6 | Click "Create Restaurant" | Success: tenant created, subscription created, branches created, owner invitation sent | ☐ |
| A4.7 | Verify backend logs show invitation token | Check backend console for invitation token | ☐ |

---

## Workflow A5: Usage & Limits

**Goal:** View per-tenant usage vs plan limits

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A5.1 | Navigate to `/admin/usage` | Usage & Limits page loads | ☐ |
| A5.2 | Table shows restaurants | Lists all restaurants with usage | ☐ |
| A5.3 | Columns show: Restaurant, Plan, Status, Branches, Owners, Managers, Waiters, Kitchen, Cashiers, Tables | All columns populated | ☐ |
| A5.4 | Usage shows current/limit format | e.g., "2 / 3" | ☐ |
| A5.5 | "At limit" highlighted in red when current >= limit | Visual indicator present | ☐ |

---

## Workflow A6: Support Tickets

**Goal:** Create and manage support tickets

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A6.1 | Navigate to `/admin/support` | Support page loads | ☐ |
| A6.2 | Table shows existing tickets | Initially empty | ☐ |
| A6.3 | Click "New Ticket" button | Form opens | ☐ |
| A6.4 | Fill subject, restaurant ID, description, priority | Form accepts input | ☐ |
| A6.5 | Click "Create Ticket" | Ticket created, appears in list | ☐ |
| A6.6 | Filter by status (open, in_progress, resolved, closed) | Table filters correctly | ☐ |
| A6.7 | Click on a ticket | Opens edit view | ☐ |
| A6.8 | Update status to "resolved" | Status updates, resolved_at set | ☐ |

---

## Workflow A7: Analytics Summary

**Goal:** View platform-wide analytics

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A7.1 | Navigate to `/admin/analytics` | Analytics page loads | ☐ |
| A7.2 | Cards show totals | Total restaurants, new (30 days), total branches, total staff | ☐ |
| A7.3 | Tables show breakdowns | Restaurants by status, subscriptions by status, tickets by status | ☐ |
| A7.4 | Generated timestamp shows current time | Timestamp updates on refresh | ☐ |

---

## Workflow A8: Plans & Plan Versions

**Goal:** Manage subscription plans

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A8.1 | Navigate to `/admin/plans` | Plans page loads | ☐ |
| A8.2 | Table shows plans | Lists plans with code, name, price, status | ☐ |
| A8.3 | Click on a plan | Navigates to versions page | ☐ |
| A8.4 | Create new version | Form accepts price, trial days, effective date | ☐ |
| A8.5 | Publish version | Version becomes active | ☐ |
| A8.6 | Add feature/limit to version | Feature/limit added to version | ☐ |

---

## Workflow A9: Subscriptions

**Goal:** View and manage tenant subscriptions

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A9.1 | Navigate to `/admin/subscriptions` | Subscriptions page loads | ☐ |
| A9.2 | Table shows subscriptions | Lists all subscriptions with plan, status, billing info | ☐ |
| A9.3 | Filter by status | Table filters correctly | ☐ |
| A9.4 | Click on a subscription | Opens subscription detail | ☐ |

---

## Workflow A10: Invoices, Payments, Refunds

**Goal:** Manage billing operations

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A10.1 | Navigate to `/admin/invoices` | Invoices page loads | ☐ |
| A10.2 | Table shows invoices | Lists invoices with status, amount | ☐ |
| A10.3 | Navigate to `/admin/payments` | Payments page loads | ☐ |
| A10.4 | Table shows payments | Lists payments with method, amount, status | ☐ |
| A10.5 | Navigate to `/admin/refunds` | Refunds page loads | ☐ |
| A10.6 | Table shows refunds | Lists refunds with status, amount | ☐ |

---

## Workflow A11: Platform Users

**Goal:** Manage platform admins (OPS, Billing, Support roles)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A11.1 | Navigate to `/admin/platform-users` | Platform users page loads | ☐ |
| A11.2 | Table shows platform admins | Lists admins with role, status | ☐ |
| A11.3 | Create new platform user | Form accepts email, display name, role | ☐ |
| A11.4 | User receives invitation | Invitation email sent (logged in dev) | ☐ |

---

## Workflow A12: Audit Log

**Goal:** View administrative audit trail

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A12.1 | Navigate to `/admin/audit` | Audit page loads | ☐ |
| A12.2 | Table shows audit events | Lists actions, entities, actors, timestamps | ☐ |
| A12.3 | Filter by page size | Pagination works | ☐ |

---

## Workflow A13: Settings

**Goal:** Manage platform settings

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A13.1 | Navigate to `/admin/settings` | Settings page loads | ☐ |
| A13.2 | Table shows settings | Lists key-value pairs with type, description | ☐ |
| A13.2 | Enable MFA enrollment | Form accepts TOTP code | ☐ |
| A13.3 | Verify recovery codes | Codes displayed, can be copied | ☐ |

---

## Workflow A14: Diagnostics

**Goal:** View diagnostics page

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A14.1 | Navigate to `/admin/diagnostics` | Diagnostics page loads | ☐ |
| A14.2 | Page displays diagnostic info | System information displayed | ☐ |

---

## Workflow A15: Tenant Cancellation & Offboarding

**Goal:** Cancel and anonymize a tenant

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A15.1 | Navigate to a tenant detail page | Tenant detail loads | ☐ |
| A15.2 | Click "Cancel" | Cancel dialog opens | ☐ |
| A15.3 | Enter confirm slug and reason | Form accepts input | ☐ |
| A15.4 | Click "Cancel Tenant" | Tenant status changes to CANCELLED | ☐ |
| A15.5 | Set effective date in future | Subscription remains active until date | ☐ |
| A15.6 | Anonymize tenant | Tenant data anonymized (emails/names hashed) | ☐ |

---

## Workflow A16: Data Export

**Goal:** Export tenant data

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A16.1 | Navigate to tenant detail | Tenant page loads | ☐ |
| A16.2 | Click "Export Data" | Export job created, job_id returned | ☐ |
| A16.3 | Poll export job status | Status changes to "completed" | ☐ |
| A16.4 | Download export | Download URL provided, data downloadable | ☐ |

---

## Workflow A17: Platform Users (Super Admin only)

**Goal:** Manage platform admin users

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A17.1 | Navigate to `/admin/platform-users` | Platform users page loads | ☐ |
| A17.2 | Table shows platform admins | Lists admins with email, role, status | ☐ |
| A17.3 | Create new platform user | Form accepts email, display name, role | ☐ |
| A17.4 | Verify role-based permissions | OPS can't access billing, Billing can't suspend, etc. | ☐ |

---

## Workflow A18: Platform Settings

**Goal:** Configure platform-wide settings

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| A18.1 | Navigate to `/admin/settings` | Settings page loads | ☐ |
| A18.2 | Table shows platform settings | Lists keys, values, types, descriptions | ☐ |
| A18.3 | Enable MFA enrollment | MFA enrollment form displays | ☐ |
| A18.3 | Generate QR code | QR code displays with secret key | ☐ |
| A18.4 | Verify MFA code | Code accepted, recovery codes shown | ☐ |
| A18.5 | Copy recovery codes | Codes copied to clipboard | ☐ |

---
