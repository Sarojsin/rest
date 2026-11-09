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
| P4 | Super admin created | ☐ |
| P5 | Browser cache cleared | ☐ |
| P6 | SMTP email configured | ☐ |

---

## Section 1: Platform Admin Console (Super Admin)

**URL:** `http://192.168.1.5:5173/admin/`  
**Credentials:** platform@harbor.example / PlatformOwner!1

### ADM-1: Platform Admin Authentication & MFA

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-1.1 | Login page renders | ☐ |
| ADM-1.2 | Valid email accepted | ☐ |
| ADM-1.3 | Password masked | ☐ |
| ADM-1.4 | MFA required after valid credentials | ☐ |
| ADM-1.5 | MFA enrollment (QR + verify) | ☐ |
| ADM-1.6 | Authenticator app accepts QR | ☐ |
| ADM-1.7 | MFA login successful | ☐ |
| ADM-1.8 | Session persists on reload | ☐ |
| ADM-1.9 | Sign out clears session | ☐ |
| ADM-1.10 | Incorrect TOTP rejected | ☐ |
| ADM-1.11 | Expired TOTP rejected | ☐ |
| ADM-1.12 | Reused TOTP rejected | ☐ |
| ADM-1.13 | Recovery code usage | ☐ |

### ADM-2: Role-Based Access Control

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-2.1 | Super Admin sees all sidebar items | ☐ |
| ADM-2.2 | OPS denied plans access | ☐ |
| ADM-2.3 | Billing denied platform-users access | ☐ |
| ADM-2.4 | Support denied diagnostics access | ☐ |
| ADM-2.5 | Super Admin API access allowed | ☐ |
| ADM-2.6 | OPS API plans POST denied | ☐ |
| ADM-2.7 | Billing API refunds POST allowed | ☐ |
| ADM-2.8 | Support API refunds POST denied | ☐ |

### ADM-3: Tenants (Restaurant Management)

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-3.1 | Tenants page loads | ☐ |
| ADM-3.2 | Restaurant list displayed | ☐ |
| ADM-3.3 | Create redirects to onboarding | ☐ |
| ADM-3.4 | Status filter works | ☐ |
| ADM-3.5 | Search by name/slug works | ☐ |
| ADM-3.6 | Tenant detail opens | ☐ |
| ADM-3.7 | Cross-tenant access denied | ☐ |

### ADM-4: Tenant Onboarding Wizard

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-4.1 | Onboarding page loads | ☐ |
| ADM-4.2 | Step 1: Organization details accepted | ☐ |
| ADM-4.3 | Step 2: Owner account accepted | ☐ |
| ADM-4.4 | Step 3: Subscription plan selected | ☐ |
| ADM-4.5 | Step 4: Branches added | ☐ |
| ADM-4.6 | Step 5: Review shows all data | ☐ |
| ADM-4.7 | Create Restaurant succeeds | ☐ |
| ADM-4.8 | Invitation token generated | ☐ |

### ADM-4: Onboarding Failure Scenarios

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-4.9 | Missing required fields rejected | ☐ |
| ADM-4.10 | Duplicate slug rejected | ☐ |
| ADM-4.11 | Duplicate owner email handled | ☐ |
| ADM-4.12 | Inactive plan rejected | ☐ |
| ADM-4.13 | No branch rejected | ☐ |
| ADM-4.14 | Duplicate submission prevented | ☐ |
| ADM-4.15 | Resend invitation invalidates old token | ☐ |
| ADM-4.16 | Expired invitation denied | ☐ |
| ADM-4.17 | Already accepted invitation denied | ☐ |

### ADM-5: Plan & Subscription Lifecycle

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-5.1 | Create plan | ☐ |
| ADM-5.2 | Create plan version | ☐ |
| ADM-5.3 | Publish version | ☐ |
| ADM-5.4 | Modify published version prevented | ☐ |
| ADM-5.5 | Assign plan to tenant | ☐ |
| ADM-5.6 | Upgrade subscription | ☐ |
| ADM-5.7 | Downgrade subscription | ☐ |
| ADM-5.8 | Change billing interval | ☐ |
| ADM-5.9 | Extend trial | ☐ |
| ADM-5.10 | Expire trial | ☐ |
| ADM-5.11 | Renew subscription | ☐ |
| ADM-5.12 | Cancel immediately | ☐ |
| ADM-5.13 | Cancel at period end | ☐ |
| ADM-5.14 | Suspend subscription | ☐ |
| ADM-5.15 | Reactivate subscription | ☐ |
| ADM-5.16 | Handle past-due payment | ☐ |
| ADM-5.17 | Apply grace period | ☐ |
| ADM-5.18 | Feature access changes after plan change | ☐ |
| ADM-5.19 | Limits enforced by backend | ☐ |

### ADM-6: Billing & Payment Integrity

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-6.1 | Generate invoice | ☐ |
| ADM-6.2 | Verify invoice amount/currency | ☐ |
| ADM-6.3 | Invoice numbering unique | ☐ |
| ADM-6.4 | Record payment | ☐ |
| ADM-6.5 | Duplicate payment prevented | ☐ |
| ADM-6.6 | Failed payment recorded | ☐ |
| ADM-6.7 | Pending payment recorded | ☐ |
| ADM-6.8 | Successful payment marks paid | ☐ |
| ADM-6.9 | Partial payment accepted | ☐ |
| ADM-6.10 | Excessive payment rejected | ☐ |
| ADM-6.11 | Cross-tenant payment denied | ☐ |
| ADM-6.12 | Pay twice denied | ☐ |
| ADM-6.13 | Refund exceeding paid rejected | ☐ |
| ADM-6.14 | Audit event for financial change | ☐ |
| ADM-6.15 | Invoice/payment/subscription reconciliation | ☐ |
| ADM-6.16 | Webhook signature verification | ☐ |
| ADM-6.17 | Duplicate webhook idempotent | ☐ |

### ADM-7: Tenant Isolation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-7.1 | Open Restaurant A authorized | ☐ |
| ADM-7.2 | Restaurant A owner denied Restaurant B data | ☐ |
| ADM-7.3 | Restaurant A staff denied Restaurant B branch | ☐ |
| ADM-7.4 | Restaurant A staff denied Restaurant B subscription | ☐ |
| ADM-7.5 | Restaurant A staff denied Restaurant B invoices | ☐ |
| ADM-7.6 | Forged tenant ID denied | ☐ |
| ADM-7.7 | Cross-tenant search restricted | ☐ |
| ADM-7.8 | Export contains only one tenant's data | ☐ |

### ADM-8: Support Access & Impersonation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-8.1 | Support selects restaurant | ☐ |
| ADM-8.2 | Support enters reason | ☐ |
| ADM-8.3 | Support permissions verified | ☐ |
| ADM-8.4 | Temporary access granted | ☐ |
| ADM-8.5 | Audit event for support access | ☐ |
| ADM-8.6 | Access expires automatically | ☐ |
| ADM-8.7 | Support cannot bypass billing/isolation | ☐ |

### ADM-9: Audit Log Integrity

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-9.1 | Tenant created → audit event | ☐ |
| ADM-9.2 | Subscription changed → audit event | ☐ |
| ADM-9.3 | Refund issued → audit event | ☐ |
| ADM-9.4 | Platform user created → audit event | ☐ |
| ADM-9.5 | MFA changed → audit event | ☐ |
| ADM-9.6 | Tenant suspended → audit event | ☐ |
| ADM-9.7 | Support access → audit event | ☐ |
| ADM-9.8 | Unauthorized action → security event | ☐ |
| ADM-9.9 | Audit record cannot be edited | ☐ |
| ADM-9.10 | Audit record cannot be deleted | ☐ |
| ADM-9.11 | Audit fields correct | ☐ |
| ADM-9.12 | No sensitive data in logs | ☐ |

### ADM-10: Cancellation & Offboarding

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-10.1 | Tenant detail loads | ☐ |
| ADM-10.2 | Cancel dialog opens | ☐ |
| ADM-10.3 | Confirm slug and reason | ☐ |
| ADM-10.4 | Tenant status CANCELLED | ☐ |
| ADM-10.5 | Future effective date honored | ☐ |
| ADM-10.6 | Restaurant data retained | ☐ |
| ADM-10.7 | Anonymization requires authorization | ☐ |
| ADM-10.8 | Tenant data anonymized | ☐ |
| ADM-10.9 | Audit history preserved | ☐ |
| ADM-10.10 | Financial references preserved | ☐ |

### ADM-11: Data Export & Deletion

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-11.1 | Export tenant records | ☐ |
| ADM-11.2 | Poll export status | ☐ |
| ADM-11.3 | Download export | ☐ |
| ADM-11.4 | Export contains only one tenant's data | ☐ |
| ADM-11.5 | Export job failure and retry | ☐ |
| ADM-11.6 | Expired download link | ☐ |
| ADM-11.7 | Unauthorized download denied | ☐ |
| ADM-11.8 | Revoke export download | ☐ |

### ADM-12: Platform Users

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-12.1 | Platform users page loads | ☐ |
| ADM-12.2 | Platform admins listed | ☐ |
| ADM-12.3 | Create platform user | ☐ |
| ADM-12.4 | Invitation email sent | ☐ |
| ADM-12.5 | OPS denied billing access | ☐ |
| ADM-12.6 | Billing denied suspend | ☐ |

### ADM-13: Platform Settings

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-13.1 | Settings page loads | ☐ |
| ADM-13.2 | Settings listed | ☐ |
| ADM-13.3 | Enable MFA enrollment | ☐ |
| ADM-13.4 | Generate QR code | ☐ |
| ADM-13.5 | Verify MFA code | ☐ |
| ADM-13.6 | Copy recovery codes | ☐ |

### ADM-14: Diagnostics

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-14.1 | Diagnostics page loads | ☐ |
| ADM-14.2 | System info displayed | ☐ |

### ADM-15: Platform Security

| Test ID | Test Case | Status |
|---------|-----------|--------|
| ADM-15.1 | Platform credentials denied tenant endpoints | ☐ |
| ADM-15.2 | Tenant credentials denied platform endpoints | ☐ |
| ADM-15.3 | Platform admin denied Owner permissions | ☐ |
| ADM-15.4 | Logout clears cross-realm session | ☐ |
| ADM-15.5 | Cookie/CSRF config correct | ☐ |

---

## Section 2: Restaurant Owner Testing

**URL:** `http://192.168.1.5:5173/`  
**Backend:** `http://127.0.0.1:8000`

### RO-1: Staff Authentication & Sessions

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-1.1 | Login page renders | ☐ |
| RO-1.2 | Valid email accepted | ☐ |
| RO-1.3 | Password masked | ☐ |
| RO-1.4 | Login redirects to /staff | ☐ |
| RO-1.5 | Role shown correctly | ☐ |
| RO-1.6 | Session persists on reload | ☐ |
| RO-1.7 | Sign out clears session | ☐ |
| RO-1.8 | Unauthenticated access redirected | ☐ |
| RO-1.9 | MFA optional per policy | ☐ |
| RO-1.10 | Expired session redirected | ☐ |

### RO-2: Owner Dashboard & Overview

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-2.1 | Owner dashboard loads | ☐ |
| RO-2.2 | KPI cards shown | ☐ |
| RO-2.3 | "Needs attention" section | ☐ |
| RO-2.4 | Shortcuts shown | ☐ |
| RO-2.5 | Sales report shown | ☐ |
| RO-2.6 | Top items shown | ☐ |
| RO-2.7 | Onboarding checklist shown | ☐ |

### RO-3: Manager Branch & Staff Management

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-3.1 | Manager login | ☐ |
| RO-3.2 | Employees page loads | ☐ |
| RO-3.3 | Staff list shown | ☐ |
| RO-3.4 | Invite staff with owner authorization | ☐ |
| RO-3.5 | Invite form accepts input | ☐ |
| RO-3.6 | Invitation created | ☐ |
| RO-3.7 | New staff in list | ☐ |
| RO-3.8 | Branch list shown | ☐ |
| RO-3.9 | Create branch with authorization | ☐ |
| RO-3.10 | Edit branch with authorization | ☐ |
| RO-3.11 | Deactivate branch with authorization | ☐ |
| RO-3.12 | Invite without authorization denied | ☐ |
| RO-3.13 | Create branch without authorization denied | ☐ |

### RO-4: Waiter QR Ordering Flow

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-4.1 | Waiter login | ☐ |
| RO-4.2 | Tables page loads | ☐ |
| RO-4.3 | Tables with QR codes | ☐ |
| RO-4.4 | Order created PENDING_CONFIRMATION | ☐ |
| RO-4.5 | Order appears in queue | ☐ |
| RO-4.6 | Order accepted | ☐ |
| RO-4.7 | Dining session created | ☐ |
| RO-4.8 | Already accepted order rejected | ☐ |
| RO-4.9 | Cross-branch order denied | ☐ |
| RO-4.10 | Duplicate acceptance prevented | ☐ |

### RO-5: Kitchen Tickets

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-5.1 | Kitchen login | ☐ |
| RO-5.2 | Kitchen page loads | ☐ |
| RO-5.3 | Accepted orders only shown | ☐ |
| RO-5.4 | Ticket items shown | ☐ |
| RO-5.5 | Ticket table shown | ☐ |
| RO-5.6 | Item status IN_PROGRESS | ☐ |
| RO-5.7 | Item status READY | ☐ |
| RO-5.8 | Duplicate readiness prevented | ☐ |
| RO-5.9 | Kitchen calls waiter | ☐ |
| RO-5.10 | Kitchen denied price edit | ☐ |
| RO-5.11 | Kitchen denied payment access | ☐ |

### RO-6: Cashier Bills & Payments

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-6.1 | Cashier login | ☐ |
| RO-6.2 | Cashier page loads | ☐ |
| RO-6.3 | Orders without bills shown | ☐ |
| RO-6.4 | Bill created | ☐ |
| RO-6.5 | Bill total correct | ☐ |
| RO-6.6 | Cash payment recorded | ☐ |
| RO-6.7 | QR payment recorded | ☐ |
| RO-6.8 | Bill marked paid | ☐ |
| RO-6.9 | Duplicate payment prevented | ☐ |
| RO-6.10 | Excessive payment rejected | ☐ |
| RO-6.11 | Receipt generated | ☐ |
| RO-6.12 | Session closure blocked with unpaid balance | ☐ |

### RO-7: Role-Based Access Control

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-7.1 | Waiter login | ☐ |
| RO-7.2 | Waiter denied /staff/menu | ☐ |
| RO-7.3 | Waiter denied /staff/employees | ☐ |
| RO-7.4 | Kitchen login | ☐ |
| RO-7.5 | Kitchen denied /staff/employees | ☐ |
| RO-7.6 | Kitchen denied /staff/menu | ☐ |
| RO-7.7 | Cashier login | ☐ |
| RO-7.8 | Cashier denied /staff/employees | ☐ |
| RO-7.9 | Cashier denied /staff/menu | ☐ |
| RO-7.10 | Manager login | ☐ |
| RO-7.11 | Manager allowed /staff/employees | ☐ |
| RO-7.12 | Manager allowed /staff/menu | ☐ |
| RO-7.13 | Owner login | ☐ |
| RO-7.14 | Owner allowed /staff/employees | ☐ |
| RO-7.15 | Owner allowed /staff/menu | ☐ |
| RO-7.16 | Waiter API /staff/employees denied | ☐ |
| RO-7.17 | Waiter API /staff/menu POST denied | ☐ |
| RO-7.18 | Waiter API subscription PATCH denied | ☐ |
| RO-7.19 | Waiter API refunds POST denied | ☐ |

### RO-8: Owner Subscription Management

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-8.1 | Owner login | ☐ |
| RO-8.2 | Subscription page loads | ☐ |
| RO-8.3 | Current plan shown | ☐ |
| RO-8.4 | Trial end date shown | ☐ |
| RO-8.5 | Features & limits shown | ☐ |
| RO-8.6 | Usage vs limits shown | ☐ |

### RO-9: Staff Invitation Acceptance

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-9.1 | Invitation link loads | ☐ |
| RO-9.2 | Invitation validity verified | ☐ |
| RO-9.3 | Single-use token enforced | ☐ |
| RO-9.4 | Already accepted denied | ☐ |
| RO-9.5 | Expired invitation denied | ☐ |
| RO-9.6 | Revoked invitation denied | ☐ |
| RO-9.7 | Password set | ☐ |
| RO-9.8 | MFA if required by policy | ☐ |
| RO-9.9 | Dashboard loads after MFA | ☐ |
| RO-9.10 | Role-specific pages shown | ☐ |

### RO-10: Branch Isolation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-10.1 | Waiter authorized Branch A | ☐ |
| RO-10.2 | Waiter denied Branch B | ☐ |
| RO-10.3 | Waiter denied Branch B table | ☐ |
| RO-10.4 | Waiter denied Branch B order | ☐ |
| RO-10.5 | Manager authorized Branch A | ☐ |
| RO-10.6 | Manager denied Branch B | ☐ |

### RO-11: Order Rejection & Cancellation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-11.1 | Waiter rejects order | ☐ |
| RO-11.2 | Rejected order cannot be accepted | ☐ |
| RO-11.3 | Accepted order cancelled | ☐ |
| RO-11.4 | Customer cancels before prep | ☐ |
| RO-11.5 | Cancellation denied after prep | ☐ |
| RO-11.6 | Invalid transition denied | ☐ |
| RO-11.7 | Rejected order not in kitchen | ☐ |

### RO-12: Multiple Customers & Dining Sessions

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-12.1 | Customer A scans QR | ☐ |
| RO-12.2 | Customer B scans same QR | ☐ |
| RO-12.3 | Customer A cart items | ☐ |
| RO-12.4 | Customer B cart items | ☐ |
| RO-12.5 | Customer A submits order | ☐ |
| RO-12.6 | Customer B submits order | ☐ |
| RO-12.7 | Staff sees both orders | ☐ |
| RO-12.8 | Customer A tracks own order | ☐ |
| RO-12.9 | Customer B tracks own order | ☐ |
| RO-12.10 | Correct dining session | ☐ |

### RO-13: Kitchen Item-Level Lifecycle

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-13.1 | Kitchen sees ticket items | ☐ |
| RO-13.2 | Item 1 marked READY | ☐ |
| RO-13.3 | Item 2 NOT auto-marked | ☐ |
| RO-13.4 | Item customizations shown | ☐ |
| RO-13.5 | Item quantities shown | ☐ |

### RO-14: Service Calls

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-14.1 | Customer calls waiter | ☐ |
| RO-14.2 | Duplicate calls prevented | ☐ |
| RO-14.3 | Waiter receives notification | ☐ |
| RO-14.4 | Waiter acknowledges call | ☐ |
| RO-14.5 | Customer sees acknowledgement | ☐ |
| RO-14.6 | Unacknowledged call remains pending | ☐ |
| RO-14.7 | Kitchen calls waiter | ☐ |
| RO-14.8 | Kitchen call distinguishable | ☐ |

### RO-15: Bill Aggregation & Settlement

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-15.1 | Bill generated | ☐ |
| RO-15.2 | All orders in bill | ☐ |
| RO-15.3 | Bill calculations correct | ☐ |
| RO-15.6 | Cash payment recorded | ☐ |
| RO-15.17 | Receipt generated | ☐ |
| RO-15.18 | Session closure blocked with unpaid balance | ☐ |

### RO-16: Refunds & Payment Integrity

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-16.1 | Refund created | ☐ |
| RO-16.2 | Partial refund accepted | ☐ |
| RO-16.3 | Full refund accepted | ☐ |
| RO-16.4 | Excessive refund rejected | ☐ |
| RO-16.5 | Unauthorized refund denied | ☐ |
| RO-16.6 | Audit event for refund | ☐ |

### RO-17: Staff Invitation Lifecycle

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-17.1 | Invite staff | ☐ |
| RO-17.2 | Resend invitation | ☐ |
| RO-17.3 | Old token invalidated | ☐ |
| RO-17.4 | Expired invitation denied | ☐ |
| RO-17.5 | Revoked invitation denied | ☐ |
| RO-17.6 | Already accepted denied | ☐ |

### RO-18: Concurrency & Duplicate Requests

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-18.1 | Two waiters accept same order | ☐ |
| RO-18.2 | Double-click Place Order | ☐ |
| RO-18.3 | Network retry no duplicate | ☐ |
| RO-18.4 | Two cashiers same bill | ☐ |
| RO-18.5 | Refresh before submit | ☐ |

### RO-19: Subscription Feature Enforcement

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-19.1 | Plan limit enforced | ☐ |
| RO-19.2 | Downgrade below usage blocked | ☐ |
| RO-19.3 | Disabled feature denied | ☐ |
| RO-19.4 | Feature access changes immediately | ☐ |

### RO-20: Staff Session Security

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-20.1 | Expired token denied | ☐ |
| RO-20.2 | Old session denied after logout | ☐ |
| RO-20.3 | Revoked access denied | ☐ |
| RO-20.4 | Deactivated account denied | ☐ |
| RO-20.5 | Self role change denied | ☐ |

### RO-21: Audit History

| Test ID | Test Case | Status |
|---------|-----------|--------|
| RO-21.1 | Staff invited → audit event | ☐ |
| RO-21.2 | Staff role updated → audit event | ☐ |
| RO-21.3 | Payment recorded → audit event | ☐ |
| RO-21.4 | No sensitive data in logs | ☐ |

---

## Section 3: Customer QR Ordering (End-to-End)

**URL:** `http://192.168.1.5:5173/t/{qr_token}`

### QR-1: QR Access & Table Identification

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-1.1 | Valid QR loads correct context | ☐ |
| QR-1.2 | Invalid QR shows error | ☐ |
| QR-1.3 | Expired QR denied | ☐ |
| QR-1.4 | Another table loads correctly | ☐ |
| QR-1.5 | Another tenant no data exposed | ☐ |
| QR-1.6 | Refresh keeps context | ☐ |

### QR-2: Menu Loading & Filtering

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-2.1 | Categories displayed | ☐ |
| QR-2.2 | Category items shown | ☐ |
| QR-2.3 | Search works | ☐ |
| QR-2.4 | Filter works | ☐ |
| QR-2.5 | Empty category state | ☐ |
| QR-2.6 | Empty menu state | ☐ |

### QR-3: Item Details & Availability

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-3.1 | Item details shown | ☐ |
| QR-3.2 | Active item orderable | ☐ |
| QR-3.3 | Inactive item not orderable | ☐ |
| QR-3.4 | Out-of-stock marked | ☐ |
| QR-3.5 | Variant price shown | ☐ |
| QR-3.6 | Add-ons shown | ☐ |
| QR-3.7 | Required customization | ☐ |
| QR-3.8 | Optional customization | ☐ |
| QR-3.9 | Price change handled | ☐ |
| QR-3.10 | Disabled item handled | ☐ |

### QR-4: Cart & Quantity Management

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-4.1 | Multiple items in cart | ☐ |
| QR-4.2 | Quantity updated | ☐ |
| QR-4.3 | Item removed | ☐ |
| QR-4.4 | Item note attached | ☐ |
| QR-4.5 | Order note attached | ☐ |
| QR-4.6 | Quantity limit enforced | ☐ |
| QR-4.7 | Empty cart rejected | ☐ |
| QR-4.8 | Unavailable items rejected | ☐ |
| QR-4.9 | Price change handled | ☐ |

### QR-5: Order Submission & Idempotency

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-5.1 | Order created PENDING_CONFIRMATION | ☐ |
| QR-5.2 | Confirmation shown | ☐ |
| QR-5.3 | Order ID shown | ☐ |
| QR-5.4 | Status token shown | ☐ |
| QR-5.5 | Double-click prevented | ☐ |
| QR-5.6 | Network retry no duplicate | ☐ |
| QR-5.7 | Idempotency key same payload | ☐ |
| QR-5.8 | Idempotency key different payload | ☐ |

### QR-6: Multiple Customers & Table

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-6.1 | Customer A scans QR | ☐ |
| QR-6.2 | Customer B scans same QR | ☐ |
| QR-6.3 | Customer A cart | ☐ |
| QR-6.4 | Customer B cart | ☐ |
| QR-6.5 | Customer A submits order | ☐ |
| QR-6.6 | Customer B submits order | ☐ |
| QR-6.7 | Staff sees both orders | ☐ |
| QR-6.8 | Customer A tracks own order | ☐ |
| QR-6.9 | Customer B tracks own order | ☐ |
| QR-6.10 | Correct dining session | ☐ |

### QR-7: Staff Confirmation & Rejection

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-7.1 | Waiter login | ☐ |
| QR-7.2 | Tables page loads | ☐ |
| QR-7.3 | Table shows occupancy | ☐ |
| QR-7.4 | Order accepted | ☐ |
| QR-7.5 | Already accepted rejected | ☐ |
| QR-7.6 | Order rejected | ☐ |
| QR-7.7 | Rejected cannot be accepted | ☐ |
| QR-7.8 | Cross-branch denied | ☐ |
| QR-7.9 | Rejected not in kitchen | ☐ |

### QR-8: Dining Session & Table Occupancy

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-8.1 | First order creates session | ☐ |
| QR-8.2 | Same table joins session | ☐ |
| QR-8.3 | Two customers correct session | ☐ |
| QR-8.4 | No duplicate sessions | ☐ |
| QR-8.5 | Occupancy changes correctly | ☐ |
| QR-8.6 | Closed session | ☐ |
| QR-8.7 | New customer after session close | ☐ |
| QR-8.8 | Old token denied new session | ☐ |

### QR-9: Kitchen Ticket & Preparation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-9.1 | Kitchen login | ☐ |
| QR-9.2 | Kitchen page loads | ☐ |
| QR-9.3 | Accepted orders only | ☐ |
| QR-9.4 | Ticket items shown | ☐ |
| QR-9.5 | Ticket table shown | ☐ |
| QR-9.6 | Item quantities shown | ☐ |
| QR-9.7 | Customizations shown | ☐ |
| QR-9.8 | Item IN_PROGRESS | ☐ |
| QR-9.9 | Item READY | ☐ |
| QR-9.10 | Duplicate readiness prevented | ☐ |
| QR-9.11 | Multi-item independent status | ☐ |
| QR-9.12 | Kitchen denied price edit | ☐ |
| QR-9.13 | Kitchen denied payment access | ☐ |
| QR-9.14 | New orders appear automatically | ☐ |

### QR-10: Kitchen Calls Waiter

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-10.1 | Kitchen calls waiter | ☐ |
| QR-10.2 | Waiter receives notification | ☐ |
| QR-10.3 | Multiple calls handled | ☐ |
| QR-10.4 | Multiple calls tracked | ☐ |

### QR-11: Customer Calls Waiter

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-11.1 | Customer calls waiter | ☐ |
| QR-11.2 | Duplicate calls prevented | ☐ |
| QR-11.3 | Waiter receives notification | ☐ |
| QR-11.4 | Waiter acknowledges | ☐ |
| QR-11.5 | Customer sees acknowledgement | ☐ |
| QR-11.6 | Unacknowledged remains pending | ☐ |
| QR-11.7 | Call from correct table | ☐ |

### QR-12: Waiter Acknowledges & Delivers

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-12.1 | Waiter acknowledges call | ☐ |
| QR-12.2 | Acknowledged call removed | ☐ |
| QR-12.3 | Waiter delivers food | ☐ |
| QR-12.4 | Order marked delivered | ☐ |

### QR-13: Customer Order-Status Tracking

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-13.1 | Status page loads | ☐ |
| QR-13.2 | Order status shown | ☐ |
| QR-13.3 | Order details shown | ☐ |
| QR-13.4 | Real-time updates | ☐ |
| QR-13.5 | Invalid token denied | ☐ |
| QR-13.6 | Expired token denied | ☐ |
| QR-13.7 | Another customer's token denied | ☐ |
| QR-13.8 | Refresh persists | ☐ |
| QR-13.9 | Status changes while open | ☐ |
| QR-13.10 | Multi-item different statuses | ☐ |
| QR-13.11 | Rejected order explanation | ☐ |
| QR-13.12 | Delivered order confirmation | ☐ |

### QR-14: Billing & Payment

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-14.1 | Bill generated | ☐ |
| QR-14.2 | All orders in bill | ☐ |
| QR-14.3 | Bill calculations correct | ☐ |
| QR-14.4 | Payment methods shown | ☐ |
| QR-14.5 | Cash payment recorded | ☐ |
| QR-14.6 | QR payment recorded | ☐ |
| QR-14.7 | Receipt generated | ☐ |
| QR-14.8 | Duplicate payment prevented | ☐ |
| QR-14.9 | Excessive payment rejected | ☐ |
| QR-14.10 | Pending payment recorded | ☐ |
| QR-14.11 | Failed payment recorded | ☐ |
| QR-14.12 | Refund processed | ☐ |
| QR-14.13 | Session closure blocked unpaid | ☐ |
| QR-14.14 | Webhook signature verified | ☐ |

### QR-15: Receipt & Session Closure

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-15.1 | Receipt generated | ☐ |
| QR-15.2 | Customer views receipt | ☐ |
| QR-15.3 | Session closed | ☐ |
| QR-15.4 | New customer uses table | ☐ |
| QR-15.5 | Old token denied new session | ☐ |

### QR-16: Customer Feedback & Rating

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-16.1 | Rating submitted | ☐ |
| QR-16.2 | Another customer's order denied | ☐ |
| QR-16.3 | Duplicate rating handled | ☐ |
| QR-16.4 | Correct restaurant/branch | ☐ |

### QR-17: Security & Tenant Isolation

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-17.1 | Guess another token denied | ☐ |
| QR-17.2 | Forged order ID denied | ☐ |
| QR-17.3 | Fake price rejected | ☐ |
| QR-17.4 | Another tenant item rejected | ☐ |
| QR-17.5 | Another branch table rejected | ☐ |
| QR-17.6 | Malformed data rejected | ☐ |
| QR-17.7 | Rate limiting | ☐ |
| QR-17.8 | Revoked QR denied | ☐ |
| QR-17.9 | Staff API from customer denied | ☐ |
| QR-17.10 | Long notes limited | ☐ |
| QR-17.11 | HTML injection safely handled | ☐ |

### QR-18: Network Failures & Retry

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-18.1 | Slow network loading | ☐ |
| QR-18.2 | Network disconnect menu | ☐ |
| QR-18.3 | Network disconnect submission | ☐ |
| QR-18.4 | Large menu loads | ☐ |
| QR-18.5 | Large images load | ☐ |
| QR-18.6 | 3D model failure usable | ☐ |
| QR-18.7 | Rapid taps no duplicates | ☐ |

### QR-19: Mobile Responsiveness & Performance

| Test ID | Test Case | Status |
|---------|-----------|--------|
| QR-19.1 | Android renders | ☐ |
| QR-19.2 | iPhone renders | ☐ |
| QR-19.3 | Low-end device performance | ☐ |
| QR-19.4 | Accessibility standards | ☐ |
| QR-19.5 | Reduced motion respected | ☐ |

---

## Section 4: Testing Priorities

**P0 — Release-blocking:**
- Platform authentication and security
- Platform role isolation
- Tenant isolation
- Onboarding integrity
- Subscription and entitlement enforcement
- Billing/payment integrity
- QR security and public endpoint protection
- Order lifecycle integrity

**P1 — Required for pilot operations:**
- Tenant and branch management
- Owner invitations
- Plan changes
- Support operations
- Audit logs
- Data export
- Mobile responsiveness
- Network failure handling

**P2 — Operational quality:**
- Analytics accuracy
- Diagnostics
- Customer feedback
- Performance on low-end devices

---

## Daily Testing Checklist

| Date | Tester | Section | Passed | Failed | Notes |
|------|--------|---------|--------|--------|-------|
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

## Testing Environment

**Backend URL:** `http://127.0.0.1:8000`  
**Frontend URL:** `http://192.168.1.5:5173`  
**Admin URL:** `http://192.168.1.5:5173/admin/`  
**Customer URL:** `http://192.168.1.5:5173/t/{qr_token}`  
**Staff URL:** `http://192.168.1.5:5173/staff/`  
**Database:** PostgreSQL `restaurant`  
**Alembic Head:** `pa0016`


