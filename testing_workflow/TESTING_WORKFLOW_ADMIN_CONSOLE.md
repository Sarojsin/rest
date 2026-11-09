# Admin Console Testing Workflow

**File:** `TESTING_WORKFLOW_ADMIN_CONSOLE.md`  
**Target:** Platform Console (Super Admin, OPS, Billing, Support)  
**URL:** `http://192.168.1.5:5173/admin/`  
**Backend:** `http://127.0.0.1:8000`  
**Purpose:** Verify all platform-level admin functionality end-to-end  
**Status:** ☐ Not Started | ☐ In Progress | ☐ Complete  

---

## Testing Standards

### Test Format
Every test case MUST include:
| Field | Description |
|-------|-------------|
| **Test ID** | Unique identifier (e.g., ADM-001) |
| **Workflow** | Related business workflow |
| **Priority** | P0 (Critical/Release-blocking) / P1 (High/Pre-production) / P2 (Medium/Operational) |
| **Actor** | Super Admin, OPS, Billing, or Support |
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
| P1 | Backend running on `http://127.0.0.1:8000` (`/health` returns 200) | ☐ |
| P2 | Frontend dev server running on `http://127.0.0.1:5173` | ☐ |
| P3 | Database migrated to latest Alembic head | ☐ |
| P4 | Super Admin created (via bootstrap or DB seed) | ☐ |
| P5 | Browser cache cleared | ☐ |
| P6 | SMTP email configured (backend console logs tokens in dev) | ☐ |

---

## Role Permission Matrix (P0)

**Principle of Least Privilege** — Each role must have minimum necessary permissions.

| Operation | Super Admin | OPS | Billing | Support |
|-----------|-------------|-----|---------|---------|
| View tenants | Yes | Yes | Limited | Limited |
| Create restaurant | Yes | Yes | No | No |
| Edit restaurant profile | Yes | Yes | No | No |
| Manage branches | Yes | Yes | No | No |
| Manage plans | Yes | No | No | No |
| View subscriptions | Yes | Limited | Yes | Limited |
| Manage invoices | Yes | No | Yes | No |
| Verify payments | Yes | No | Yes | No |
| Issue refunds | Yes | No | Authorized | No |
| Suspend tenant | Yes | Authorized | No | No |
| Create platform users | Yes | No | No | No |
| View audit logs | Yes | Limited | Billing scope | Support scope |
| Access diagnostics | Yes | Limited | No | Authorized |

**Critical**: Hiding a UI button is NOT access control. API endpoints must reject unauthorized calls with 403.

---

## Workflow ADM-1: Platform Admin Authentication & MFA (P0)

**Goal:** Verify platform realm authentication with proper MFA state handling

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-1.1 | P0 | Super Admin | Login page accessible | None | Navigate to `/admin/login` | Login page renders with email/password fields | | | | |
| ADM-1.2 | P0 | Super Admin | Login page loaded | Email: platform-admin@example.com | Enter valid email | Email accepted without error | | | | |
| ADM-1.3 | P0 | Super Admin | Email entered | Password: valid | Enter valid password | Password masked | | | | |
| ADM-1.4 | P0 | Super Admin | Credentials valid | Same as above | Click "Continue" | Returns MFA enrollment required or MFA challenge (NOT 401) | | | | |
| ADM-1.5 | P0 | Super Admin | MFA not enrolled | Same user | Navigate to MFA enrollment | Secret + QR code displayed | | | | |
| ADM-1.6 | P0 | Super Admin | MFA enrollment started | Authenticator app available | Scan QR code | App accepts code | | | | |
| ADM-1.7 | P0 | Super Admin | MFA enrolled | Same user | Enter 6-digit TOTP code, click Verify | Redirected to `/admin/` Dashboard | | | | |
| ADM-1.8 | P0 | Super Admin | MFA verified | Same user | Reload page | Session persists (cookie-based) | | | | |
| ADM-1.9 | P0 | Super Admin | Authenticated | Same user | Click "Sign out" | Redirected to `/admin/login`, session cleared | | | | |
| ADM-1.10 | P0 | Super Admin | MFA enrolled | Wrong code | Enter incorrect TOTP code | Error: invalid code, not locked out | | | | |
| ADM-1.11 | P0 | Super Admin | MFA enrolled | Expired code | Enter expired TOTP code | Error: code expired | | | | |
| ADM-1.12 | P0 | Super Admin | MFA enrolled | Used code | Reuse previously used TOTP code | Error: code already used (if replay prevention) | | | | |
| ADM-1.13 | P0 | Super Admin | Recovery codes available | Recovery codes | Use recovery code instead of TOTP | Login succeeds, recovery code consumed | | | | |

**Notes:**
- Platform login is MFA-gated. First login requires MFA enrollment.
- Backend must distinguish: Invalid credentials / Password accepted, MFA required / MFA challenge / MFA successful.
- Never use 401 for all stages without defined API contract.

---

## Workflow ADM-2: Role-Based Access Control & Permission Matrix (P0)

**Goal:** Verify role permissions enforced at both UI and API level

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-2.1 | P0 | Super Admin | Logged in as Super Admin | None | Navigate to all sidebar items | All items visible and accessible | | | | |
| ADM-2.2 | P0 | OPS | Logged in as OPS | None | Navigate to `/admin/plans` | Access denied (403) | | | | |
| ADM-2.3 | P0 | Billing | Logged in as Billing | None | Navigate to `/admin/platform-users` | Access denied (403) | | | | |
| ADM-2.4 | P0 | Support | Logged in as Support | None | Navigate to `/admin/diagnostics` | Access denied (403) | | | | |
| ADM-2.5 | P0 | Super Admin | Authenticated API | None | `GET /api/platform/plans` | 200 OK | | | | |
| ADM-2.6 | P0 | OPS | Authenticated API | None | `POST /api/platform/plans` | 403 Forbidden | | | | |
| ADM-2.7 | P0 | Billing | Authenticated API | None | `POST /api/platform/refunds` | 200 OK | | | | |
| ADM-2.8 | P0 | Support | Authenticated API | None | `POST /api/platform/refunds` | 403 Forbidden | | | | |

---

## Workflow ADM-3: Tenants (Restaurant Management) (P0)

**Goal:** CRUD operations for restaurant tenants with proper isolation

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-3.1 | P0 | Super Admin | Authenticated | None | Navigate to `/admin/tenants` | Tenants page loads | | | | |
| ADM-3.2 | P0 | Super Admin | Tenants page loaded | None | Verify table shows restaurant list | Initially empty or shows existing tenants | | | | |
| ADM-3.3 | P0 | Super Admin | Tenants page loaded | None | Click "Create" button | Redirects to `/admin/onboarding` | | | | |
| ADM-3.4 | P0 | Super Admin | Tenants page loaded | None | Filter by status (ACTIVE/SUSPENDED/CANCELLED) | Table filters correctly | | | | |
| ADM-3.5 | P0 | Super Admin | Tenants page loaded | None | Search by name/slug | Results filter in real-time | | | | |
| ADM-3.6 | P0 | Super Admin | Tenants page loaded | Existing tenant | Click on a tenant row | Opens tenant detail page | | | | |
| ADM-3.7 | P0 | Super Admin | Tenant created | Restaurant A exists | Attempt to access Restaurant B via forged ID | Access denied (403) | | | | |

---

## Workflow ADM-4: Tenant Onboarding Wizard (P0)

**Goal:** Complete multi-step restaurant onboarding with failure scenarios

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-4.1 | P0 | Super Admin | Authenticated | None | Navigate to `/admin/onboarding` | Onboarding page loads | | | | |
| ADM-4.2 | P0 | Super Admin | Onboarding page loaded | Valid restaurant data | Step 1: Organization Details | Form accepts restaurant name, slug, contact email, phone, country, address, timezone, currency | | | | |
| ADM-4.3 | P0 | Super Admin | Step 1 complete | Valid owner data | Step 2: Owner Account | Form accepts owner full name, email, phone | | | | |
| ADM-4.4 | P0 | Super Admin | Step 2 complete | Valid plan | Step 3: Subscription Plan | Select plan, trial days, billing interval | | | | |
| ADM-4.5 | P0 | Super Admin | Step 3 complete | Valid branch data | Step 4: Branches | Add at least 1 branch with name, code, address | | | | |
| ADM-4.6 | P0 | Super Admin | Step 4 complete | All data valid | Step 5: Review & Create | Summary shows all entered data | | | | |
| ADM-4.7 | P0 | Super Admin | All steps complete | All data valid | Click "Create Restaurant" | Tenant created, subscription created, branches created, owner invitation sent | | | | |
| ADM-4.8 | P0 | Super Admin | Onboarding successful | None | Check backend console | Invitation token generated and logged | | | | |

### Onboarding Failure Scenarios (P0)

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-4.9 | P0 | Super Admin | Onboarding page loaded | Missing required fields | Create tenant with missing required fields | Validation error, tenant NOT created | | | | |
| ADM-4.10 | P0 | Super Admin | Onboarding page loaded | Duplicate slug | Create duplicate slug | Rejected: slug already taken | | | | |
| ADM-4.11 | P0 | Super Admin | Onboarding page loaded | Duplicate owner email | Create duplicate owner invitation | Handled according to account/invitation policy | | | | |
| ADM-4.12 | P0 | Super Admin | Onboarding page loaded | Inactive plan | Select inactive plan | Rejected: plan not available | | | | |
| ADM-4.13 | P0 | Super Admin | Onboarding page loaded | No branch | Create tenant without a branch | Rejected if at least one branch required | | | | |
| ADM-4.14 | P0 | Super Admin | Onboarding page loaded | Valid data | Submit create request twice | No duplicate tenant | | | | |
| ADM-4.15 | P0 | Super Admin | Onboarding page loaded | Valid invitation | Resend owner invitation | New token issued; previous token invalidated | | | | |
| ADM-4.16 | P0 | Super Admin | Invitation exists | Expired invitation | Try to accept expired invitation | Cannot be accepted | | | | |
| ADM-4.17 | P0 | Super Admin | Invitation accepted | Accepted invitation | Try to accept again | Already accepted, cannot reuse | | | | |

**Architectural Requirement:** Tenant, subscription, initial branch, owner invitation, entitlements and audit event should be created consistently using a database transaction. Email delivery should use outbox/retry strategy.

---

## Workflow ADM-5: Plan & Subscription Lifecycle (P0)

**Goal:** Manage plans, versions, and subscription lifecycle

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-5.1 | P0 | Super Admin | Authenticated | None | Create a plan | Plan created with code, name, price | | | | |
| ADM-5.2 | P0 | Super Admin | Plan created | Plan ID | Create new plan version | Version created with price, trial days, effective date | | | | |
| ADM-5.3 | P0 | Super Admin | Version created | Version ID | Publish version | Version becomes active | | | | |
| ADM-5.4 | P0 | Super Admin | Published version | Published version ID | Attempt to modify published version | Prevented: immutable published version | | | | |
| ADM-5.5 | P0 | Super Admin | Plan exists | Tenant ID, plan ID | Assign plan to new tenant | Subscription created for tenant | | | | |
| ADM-5.6 | P0 | Super Admin | Subscription exists | Subscription ID | Upgrade subscription | Subscription upgraded, new plan applied | | | | |
| ADM-5.7 | P0 | Super Admin | Subscription exists | Subscription ID | Downgrade subscription | Subscription downgraded OR blocked if below current usage | | | | |
| ADM-5.8 | P0 | Super Admin | Subscription exists | Subscription ID | Change billing interval | Billing interval updated | | | | |
| ADM-5.9 | P0 | Super Admin | Trial active | Subscription ID | Extend trial | Trial end date extended | | | | |
| ADM-5.10 | P0 | Super Admin | Trial active | Subscription ID | Expire trial | Trial status changes to expired | | | | |
| ADM-5.11 | P0 | Super Admin | Subscription exists | Subscription ID | Renew subscription | Subscription renewed | | | | |
| ADM-5.12 | P0 | Super Admin | Subscription exists | Subscription ID | Cancel immediately | Subscription cancelled immediately | | | | |
| ADM-5.13 | P0 | Super Admin | Subscription exists | Subscription ID | Cancel at period end | Subscription remains active until period end | | | | |
| ADM-5.14 | P0 | Super Admin | Subscription exists | Subscription ID | Suspend subscription | Subscription suspended | | | | |
| ADM-5.15 | P0 | Super Admin | Suspended subscription | Subscription ID | Reactivate subscription | Subscription reactivated | | | | |
| ADM-5.16 | P0 | Super Admin | Past due subscription | Subscription ID | Handle past-due payment | Payment reconciliation applied | | | | |
| ADM-5.17 | P0 | Super Admin | Grace period active | Subscription ID | Apply grace period | Grace period applied, service continues | | | | |
| ADM-5.18 | P0 | Super Admin | Plan changed | Subscription ID | Verify feature access changes | Features reflect new plan | | | | |
| ADM-5.19 | P0 | Super Admin | Plan changed | Subscription ID | Verify limits enforced | Limits enforced by backend | | | | |

**Key Test:** Tenant has 20 waiters, new plan permits 10. System must block or defer downgrade, or apply grandfathering policy — NOT silently delete employees.

---

## Workflow ADM-6: Billing & Payment Integrity (P0)

**Goal:** Verify billing operations with payment integrity

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-6.1 | P0 | Billing | Authenticated | Invoice exists | Generate invoice | Invoice created with unique number | | | | |
| ADM-6.2 | P0 | Billing | Invoice exists | Invoice ID | Verify invoice amount and currency | Correct amount and currency displayed | | | | |
| ADM-6.3 | P0 | Billing | Invoices exist | None | Verify invoice numbering uniqueness | No duplicate invoice numbers | | | | |
| ADM-6.4 | P0 | Billing | Invoice exists | Invoice ID | Submit payment | Payment recorded, balance updated | | | | |
| ADM-6.5 | P0 | Billing | Invoice paid | Invoice ID | Submit same payment again | Duplicate payment prevented | | | | |
| ADM-6.6 | P0 | Billing | Invoice exists | Invoice ID | Record failed payment | Payment marked failed | | | | |
| ADM-6.7 | P0 | Billing | Invoice exists | Invoice ID | Record pending payment | Payment marked pending | | | | |
| ADM-6.8 | P0 | Billing | Invoice exists | Invoice ID | Record successful payment | Invoice marked paid | | | | |
| ADM-6.9 | P0 | Billing | Invoice exists | Invoice ID | Record partial payment | Partial payment accepted (if supported) | | | | |
| ADM-6.10 | P0 | Billing | Invoice exists | Invoice ID | Payment exceeds outstanding balance | Rejected unless explicitly supported | | | | |
| ADM-6.11 | P0 | Billing | Invoice created | Tenant A invoice, Tenant B | Apply payment to another tenant's invoice | Denied | | | | |
| ADM-6.12 | P0 | Billing | Invoice paid | Invoice ID | Try to pay invoice twice | Denied: already paid | | | | |
| ADM-6.13 | P0 | Super Admin | Refund created | Refund ID | Refund exceeding paid amount | Rejected | | | | |
| ADM-6.14 | P0 | Billing | Sensitive change made | Invoice/payment change | Verify audit event created | Audit event logged for financial change | | | | |
| ADM-6.15 | P0 | Billing | Invoice, payment, subscription | All related | Verify reconciliation between invoice, payment and subscription state | States consistent | | | | |
| ADM-6.16 | P0 | Billing | Webhook configured | Webhook payload | Test webhook signature verification | Valid signature accepted, invalid rejected | | | | |
| ADM-6.17 | P0 | Billing | Webhook endpoint | Duplicate webhook | Send duplicate webhook delivery | Handled idempotently | | | | |

---

## Workflow ADM-7: Tenant Isolation (P0)

**Goal:** Verify multi-tenant data isolation

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-7.1 | P0 | Super Admin | Two tenants created | Restaurant A, Restaurant B | Open Restaurant A | Authorized | | | | |
| ADM-7.2 | P0 | Restaurant A Owner | Authenticated as Restaurant A owner | Restaurant B data | Restaurant A owner tries to access Restaurant B's tenant data | Denied | | | | |
| ADM-7.3 | P0 | Restaurant A Staff | Authenticated as Restaurant A staff | Restaurant B branch | Restaurant A staff requests Restaurant B's branch | Denied | | | | |
| ADM-7.4 | P0 | Restaurant A Staff | Authenticated as Restaurant A staff | Restaurant B subscription | Restaurant A requests Restaurant B's subscription | Denied | | | | |
| ADM-7.5 | P0 | Restaurant A Staff | Authenticated as Restaurant A staff | Restaurant B invoices | Restaurant A requests Restaurant B's invoices | Denied | | | | |
| ADM-7.6 | P0 | API Client | Authenticated API | Forged tenant ID | API receives forged tenant ID | Denied | | | | |
| ADM-7.7 | P0 | Super Admin | Two tenants | None | Search returns results from both tenants | Only permitted platform roles can see cross-tenant results | | | | |
| ADM-7.8 | P0 | Super Admin | Restaurant A | None | Export Restaurant A | Contains only Restaurant A's data | | | | |

---

## Workflow ADM-8: Support Access & Impersonation (P1)

**Goal:** Verify controlled support access

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-8.1 | P1 | Support | Authenticated as Support | None | Select a restaurant | Restaurant selection available | | | | |
| ADM-8.2 | P1 | Support | Restaurant selected | Valid reason | Enter reason for access | Reason accepted | | | | |
| ADM-8.3 | P1 | Support | Reason entered | None | System checks support permissions | Permission verified | | | | |
| ADM-8.4 | P1 | Support | Permissions verified | None | Temporary access granted | Access granted only for approved scope and duration | | | | |
| ADM-8.5 | P1 | Support | Access granted | None | Access recorded in audit logs | Audit event created | | | | |
| ADM-8.6 | P1 | Support | Access expired | None | Try to access after expiry | Access denied | | | | |
| ADM-8.7 | P1 | Support | Access granted | None | Try to bypass billing or tenant isolation | Denied | | | | |

---

## Workflow ADM-9: Audit Log Integrity (P0)

**Goal:** Verify audit events are complete and protected

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-9.1 | P0 | Super Admin | Tenant created | None | Create tenant | Audit event: tenant created | | | | |
| ADM-9.2 | P0 | Super Admin | Subscription changed | None | Change subscription | Audit event: subscription changed | | | | |
| ADM-9.3 | P0 | Billing | Refund issued | None | Issue refund | Audit event: refund issued | | | | |
| ADM-9.4 | P0 | Super Admin | Platform user created | None | Create platform user | Audit event: platform user created | | | | |
| ADM-9.5 | P0 | Super Admin | MFA changed | None | Change MFA settings | Audit event: MFA settings changed | | | | |
| ADM-9.6 | P0 | Super Admin | Tenant suspended | None | Suspend tenant | Audit event: tenant suspended | | | | |
| ADM-9.7 | P0 | Support | Support access granted | None | Grant support access | Audit event: support access granted | | | | |
| ADM-9.8 | P0 | API Client | Unauthorized action | None | Attempt unauthorized action | Security event logged | | | | |
| ADM-9.9 | P0 | Super Admin | Audit records exist | None | Try to edit audit record | Denied: audit records immutable | | | | |
| ADM-9.10 | P0 | Super Admin | Audit records exist | None | Try to delete audit record | Denied: audit records immutable | | | | |
| ADM-9.11 | P0 | Super Admin | Audit event exists | None | Verify actor, timestamp, action, target, outcome | All fields correct | | | | |
| ADM-9.12 | P0 | Super Admin | Sensitive operation | None | Perform sensitive operation | No passwords, TOTP secrets, or raw invitation tokens in logs | | | | |

---

## Workflow ADM-10: Tenant Cancellation & Offboarding (P0)

**Goal:** Verify cancellation and anonymization as separate operations

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-10.1 | P0 | Super Admin | Tenant exists | Restaurant ID | Navigate to tenant detail page | Tenant detail loads | | | | |
| ADM-10.2 | P0 | Super Admin | Tenant active | Tenant ID | Click "Cancel" | Cancel dialog opens | | | | |
| ADM-10.3 | P0 | Super Admin | Cancel dialog open | Confirm slug, reason | Enter confirm slug and reason | Form accepts input | | | | |
| ADM-10.4 | P0 | Super Admin | Cancel confirmed | Tenant ID | Click "Cancel Tenant" | Tenant status changes to CANCELLED | | | | |
| ADM-10.5 | P0 | Super Admin | Cancellation scheduled | Future date | Set effective date in future | Subscription remains active until date | | | | |
| ADM-10.6 | P0 | Super Admin | Tenant cancelled | Tenant ID | Verify restaurant still accessible | Restaurant data retained per policy | | | | |
| ADM-10.7 | P0 | Super Admin | Tenant cancelled | Tenant ID | Attempt anonymization without authorization | Denied | | | | |
| ADM-10.8 | P0 | Super Admin | Authorization granted | Tenant ID | Anonymize tenant | Tenant data anonymized (emails/names hashed) | | | | |
| ADM-10.9 | P0 | Super Admin | Tenant anonymized | Tenant ID | Verify audit history preserved | Audit history NOT anonymized | | | | |
| ADM-10.10 | P0 | Super Admin | Tenant anonymized | Tenant ID | Verify financial references preserved | Financial references NOT corrupted | | | | |

---

## Workflow ADM-11: Data Export & Deletion (P1)

**Goal:** Verify export completeness, isolation, and download authorization

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-11.1 | P1 | Super Admin | Tenant exists | Restaurant ID | Export one tenant's records | Export job created, job_id returned | | | | |
| ADM-11.2 | P1 | Super Admin | Export job created | Job ID | Poll export job status | Status changes to "completed" | | | | |
| ADM-11.3 | P1 | Super Admin | Export completed | Job ID | Download export | Download URL provided, data downloadable | | | | |
| ADM-11.4 | P1 | Super Admin | Export downloaded | Tenant A data | Verify export contains only Tenant A's data | Tenant isolation verified | | | | |
| ADM-11.5 | P1 | Super Admin | Export job failed | None | Trigger export job failure | Job marked failed, retry available | | | | |
| ADM-11.6 | P1 | Super Admin | Export completed | Download link | Expire download link | Link becomes invalid after expiry | | | | |
| ADM-11.7 | P1 | Unauthorized user | Export exists | Download link | Unauthorized download attempt | Denied | | | | |
| ADM-11.8 | P1 | Super Admin | Export exists | Job ID | Revoke export download | Revocation effective immediately | | | | |

---

## Workflow ADM-12: Platform Users (Merged) (P0)

**Goal:** Manage platform admin users with proper role permissions

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-12.1 | P0 | Super Admin | Authenticated | None | Navigate to `/admin/platform-users` | Platform users page loads | | | | |
| ADM-12.2 | P0 | Super Admin | Users page loaded | None | Table shows platform admins | Lists admins with email, role, status | | | | |
| ADM-12.3 | P0 | Super Admin | Users page loaded | New user data | Create new platform user | Form accepts email, display name, role | | | | |
| ADM-12.4 | P0 | Super Admin | User created | New user | User receives invitation | Invitation email sent (logged in dev) | | | | |
| ADM-12.5 | P0 | Super Admin | Multiple users | OPS user | OPS tries to access billing | Denied | | | | |
| ADM-12.6 | P0 | Super Admin | Multiple users | Billing user | Billing tries to suspend tenant | Denied | | | | |

---

## Workflow ADM-13: Platform Settings (Merged) (P1)

**Goal:** Configure platform-wide settings

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-13.1 | P1 | Super Admin | Authenticated | None | Navigate to `/admin/settings` | Settings page loads | | | | |
| ADM-13.2 | P1 | Super Admin | Settings page loaded | None | Table shows platform settings | Lists keys, values, types, descriptions | | | | |
| ADM-13.3 | P1 | Super Admin | Settings page loaded | MFA config | Enable MFA enrollment | MFA enrollment form displays | | | | |
| ADM-13.4 | P1 | Super Admin | MFA enabled | None | Generate QR code | QR code displays with secret key | | | | |
| ADM-13.5 | P1 | Super Admin | MFA enrolled | None | Verify MFA code | Code accepted, recovery codes shown | | | | |
| ADM-13.6 | P1 | Super Admin | Recovery codes | None | Copy recovery codes | Codes copied to clipboard | | | | |

---

## Workflow ADM-14: Diagnostics (P1)

**Goal:** View diagnostics page

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-14.1 | P1 | Super Admin | Authenticated | None | Navigate to `/admin/diagnostics` | Diagnostics page loads | | | | |
| ADM-14.2 | P1 | Super Admin | Diagnostics page loaded | None | Page displays diagnostic info | System information displayed | | | | |

---

## Workflow ADM-15: Platform Security (P0)

**Goal:** Verify security boundaries between platform and tenant realms

| Test ID | Priority | Actor | Preconditions | Test Data | Action | Expected Result | Actual Result | Status | Evidence | Bug ID |
|---------|----------|-------|---------------|-----------|--------|-----------------|---------------|--------|----------|--------|
| ADM-15.1 | P0 | API Client | Platform credentials | None | Platform credentials authenticate against tenant-only endpoints | Denied | | | | |
| ADM-15.2 | P0 | API Client | Tenant credentials | None | Tenant credentials access platform-only endpoints | Denied | | | | |
| ADM-15.3 | P0 | Super Admin | Platform admin session | None | Platform admin session does not grant restaurant Owner permissions | Denied | | | | |
| ADM-15.4 | P0 | Super Admin | Logged out of platform | None | Log out of platform realm | Session cleared, no cross-realm session | | | | |
| ADM-15.5 | P0 | Super Admin | Cookies configured | None | Verify cookie names, paths, scopes, CSRF protections | Correctly configured | | | | |

---

## Testing Execution Tracker

| Section | Total Tests | Passed | Failed | Blocked | Not Tested | % Complete |
|---------|-------------|--------|--------|---------|------------|------------|
| ADM-1 Authentication & MFA | 13 | 0 | 0 | 0 | 13 | 0% |
| ADM-2 Role-Based Access Control | 8 | 0 | 0 | 0 | 8 | 0% |
| ADM-3 Tenants | 7 | 0 | 0 | 0 | 7 | 0% |
| ADM-4 Onboarding | 17 | 0 | 0 | 0 | 17 | 0% |
| ADM-5 Plan & Subscription Lifecycle | 19 | 0 | 0 | 0 | 19 | 0% |
| ADM-6 Billing & Payment Integrity | 17 | 0 | 0 | 0 | 17 | 0% |
| ADM-7 Tenant Isolation | 8 | 0 | 0 | 0 | 8 | 0% |
| ADM-8 Support Access | 7 | 0 | 0 | 0 | 7 | 0% |
| ADM-9 Audit Log Integrity | 12 | 0 | 0 | 0 | 12 | 0% |
| ADM-10 Cancellation & Offboarding | 10 | 0 | 0 | 0 | 10 | 0% |
| ADM-11 Data Export & Deletion | 8 | 0 | 0 | 0 | 8 | 0% |
| ADM-12 Platform Users | 6 | 0 | 0 | 0 | 6 | 0% |
| ADM-13 Platform Settings | 6 | 0 | 0 | 0 | 6 | 0% |
| ADM-14 Diagnostics | 2 | 0 | 0 | 0 | 2 | 0% |
| ADM-15 Platform Security | 5 | 0 | 0 | 0 | 5 | 0% |
| **TOTAL** | **126** | **0** | **0** | **0** | **126** | **0%** |

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
**Database:** PostgreSQL `restaurant`  
**Alembic Head:** `pa0016`  

---

## Testing Priorities

**P0 — Must pass (Release-blocking):**
- Platform authentication and security
- Platform role isolation
- MFA and recovery
- Tenant isolation
- Onboarding integrity
- Subscription and entitlement enforcement
- Billing/payment integrity

**P1 — Required for pilot operations:**
- Tenant and branch management
- Owner invitations
- Plan changes
- Support operations
- Audit logs
- Data export
- Suspension and reactivation

**P2 — Operational quality:**
- Analytics accuracy
- Diagnostics
- Large datasets
- Concurrency
- Performance
- Error recovery