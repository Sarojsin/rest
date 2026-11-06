# 10 — Admin Console: Missing Navigation Sections

**File:** `backend/plan/workflow/10_admin_console_sections.md`
**Area:** Admin Console frontend — missing navigation sections and pages
**Status:** Proposed

---

## 1. Overview

The Admin Console navigation specifies 13 sections. Several are already built
(Restaurants, Plans, Subscriptions, Invoices & Payments, Platform Users,
Overview, Audit Logs, Platform Settings partially). This plan adds the missing
frontend pages and wires them into the admin navigation shell:

- Onboarding (track new restaurant setup)
- Usage & Limits (monitor seats, branches, resource usage)
- Support (handle customer issues)
- Analytics (revenue, growth, usage)

It also reviews the Platform Settings page for completeness.

---

## 2. Current State

Admin pages in `apps/web/src/pages/admin/`:
- AdminDashboardPage.tsx ✅
- AdminTenantsPage.tsx ✅ (Restaurants)
- AdminPlansPage.tsx ✅ (Subscription Plans)
- AdminPlanVersionsPage.tsx ✅
- AdminSubscriptionsPage.tsx ✅
- AdminInvoicesPage.tsx ✅ (Invoices & Payments)
- AdminPaymentsPage.tsx ✅
- AdminRefundsPage.tsx ✅
- AdminPlatformUsersPage.tsx ✅
- AdminTenantEntitlementsPage.tsx ✅
- AdminAuditPage.tsx ✅ (Audit Logs)
- AdminSettingsPage.tsx ⚠️ (Platform Settings — partial)
- AdminTrialLifecyclePage.tsx ✅
- AdminRegisterSuccessPage.tsx ✅
- AdminPublicRegisterPage.tsx ✅
- AdminPublicPlansPage.tsx ✅

Missing entirely:
- Onboarding page
- Usage & Limits page
- Support page
- Analytics page

---

## 3. Desired State

### 3.1 Onboarding Page

Track new restaurant setup from registration to first order.

**Data shown per onboarding task:**
- Restaurant name, slug, tenant_id
- Owner email, invitation status (pending/accepted)
- Plan assigned, trial end date
- Branches created (count / plan limit)
- Onboarding stage: `registered` → `owner_invited` → `owner_activated` → `profile_complete` → `tables_configured` → `menu_configured` → `staff_invited` → `payments_configured` → `operational`
- Actions: resend invitation, mark complete, reset

**Backend endpoint:** `GET /api/platform/onboarding` → list of tenant onboarding
statuses; `PATCH /api/platform/onboarding/{tenant_id}/stage` → update stage.

### 3.2 Usage & Limits Page

Show per-tenant usage against plan limits, sourced from `platform_tenant_usage`
and `platform_usage_events`.

**Columns:** Restaurant | Plan | Branches (used/limit) | Owner (1/1) | Managers (x/limit) | Waiters (x/limit) | Kitchen (x/limit) | Cashiers (x/limit) | Tables (x/limit) | Status

**Backend endpoint:** `GET /api/platform/tenants/{id}/usage` (exists) + list
endpoint aggregating all tenants' usage.

### 3.3 Support Page

Customer issue tracking: list open/closed support tickets linked to tenants.

**Fields:** ticket_id, tenant_id, restaurant_name, subject, status, priority,
created_at, assigned_to.

**Backend:** New `platform_support_tickets` table + CRUD endpoints
(`GET /api/platform/support/tickets`, `POST`, `PATCH`).

### 3.4 Analytics Page

Revenue, growth, usage charts:
- MRR by plan
- New restaurants per month
- Active vs trial vs past-due subscriptions
- Top restaurants by order volume

**Backend:** `GET /api/platform/analytics/summary` (aggregated, no tenant
scope required — Super Admin only).

### 3.5 Platform Settings (review)

Ensure these settings exist: platform domain, self-service toggle, trial default
days, MFA requirement, support email, SMTP config, maintenance mode.

Most already exist via `platform_settings` table; verify the UI exposes them.

---

## 4. API Changes

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/platform/onboarding` | GET | List tenant onboarding statuses | tenant.view |
| `/api/platform/onboarding/{id}/stage` | PATCH | Update onboarding stage | tenant.manage |
| `/api/platform/support/tickets` | GET/POST | List/create support tickets | support + tenant.view |
| `/api/platform/support/tickets/{id}` | PATCH | Update ticket status/assignment | support |
| `/api/platform/analytics/summary` | GET | Platform-wide analytics | analytics.view |

---

## 5. Frontend Changes

- `apps/web/src/pages/admin/AdminOnboardingPage.tsx` (new)
- `apps/web/src/pages/admin/AdminUsagePage.tsx` (new)
- `apps/web/src/pages/admin/AdminSupportPage.tsx` (new)
- `apps/web/src/pages/admin/AdminAnalyticsPage.tsx` (new)
- Update `AdminLayout.tsx` sidebar to include all 13 sections.
- Update `src/App.tsx` admin routes if not using lazy loading.

---

## 6. Acceptance Criteria

- [ ] All 13 nav sections render in Admin Console.
- [ ] Onboarding page lists tenants with stage and actions.
- [ ] Usage & Limits shows per-tenant counters vs plan limits.
- [ ] Support page can create and update tickets.
- [ ] Analytics page shows platform-wide aggregates.
- [ ] Both `npm run build` and `npm run build:admin` pass.

---

## 7. Related Files

- `apps/web/src/pages/admin/AdminLayout.tsx` — navigation
- `apps/web/src/App.tsx` — admin routes
- `backend/app/api/platform/router_tenants.py` — onboarding endpoints
- `backend/app/modules/platform/models.py` — support ticket model + migration
