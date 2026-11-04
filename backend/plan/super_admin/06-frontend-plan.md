# 06 — Frontend Plan (Admin app)

**Principle:** the Super Admin UI is a **different product**. It must look and behave differently from the tenant dashboard so an operator cannot confuse “I am managing the platform” with “I am managing my restaurant”. See plan `08-super-admin.md` §Philosophy.

**Origin:** production admin UI is `https://admin.{platform_domain}`, a separate build entry in the same repo. The actual domain is **open** in PA-ADR-011; do not hard-code it. Local dev serves it from the same Vite server at `/admin`; that is a dev convenience, not a production topology (PA-ADR-003).

**Existing app:** `apps/web/src` — React 18, React Router 6, no state library, no CSS framework. Staff pages use `useAuth()`, `apiFetch`, and the shared `@rest/api-client` types.

---

## 1. Route tree

```
/login                        AdminLoginPage         public
/mfa                          AdminMfaPage           mfa_ticket in memory
/invite/:token                AdminAcceptInvitePage  public
/                             AdminLayout            guard: platform session cookie
  index                       AdminDashboardPage
  tenants                     AdminTenantsPage
  tenants/:tenantId           AdminTenantDetailPage
  plans                       AdminPlansPage
  plans/:planId               AdminPlanDetailPage
  subscriptions               AdminSubscriptionsPage
  subscriptions/:id           AdminSubscriptionDetailPage
  invoices                    AdminInvoicesPage
  invoices/:invoiceId         AdminInvoiceDetailPage
  payments                    AdminPaymentsPage
  refunds                     AdminRefundQueuePage
  platform-users              AdminUsersPage
  audit                       AdminAuditPage
  settings                    AdminSettingsPage
  diagnostics                 AdminDiagnosticsPage
  profile                     AdminProfilePage
*                             → / or /login
```

Local dev keeps the `/admin` prefix through the Vite proxy. The route table is defined with a configurable `basename` so production is `/` on the admin origin and dev is `/admin`.

Rules:

- The admin app is a **separate root** (`AdminRoot`), not nested under the staff app. It has its own auth context, layout, router, and CSS.
- The staff `AuthProvider` does not wrap the admin root, and the admin provider does not wrap `/staff`.
- A platform session cookie must never be accepted by the staff API client; the admin client is a separate instance with a separate base path.
- A tenant owner who opens the admin origin is redirected to login, not shown a “forbidden” page that confirms the route exists.

## 2. Auth architecture

### 2.1 Files and build entry

```
apps/web/admin.html                     # separate HTML entry
apps/web/vite.admin.config.ts           # separate Vite config/base
apps/web/src/admin.tsx                  # separate React root
apps/web/src/lib/platformApi.ts         # fetch wrapper for /api/platform
apps/web/src/lib/platformAuth.tsx       # AdminAuthProvider + usePlatformAuth
apps/web/src/pages/admin/AdminGuard.tsx
apps/web/src/pages/admin/AdminLayout.tsx
apps/web/src/pages/admin/...
```

`vite.admin.config.ts` sets the admin base path, a distinct output directory (`dist-admin`), and the admin-origin proxy for local dev. The tenant build (`vite.config.ts`) must not include the admin entry.

`platformApi.ts`:

- base URL from `VITE_PLATFORM_API_URL` (defaults to `""` for local proxy),
- `credentials: "include"` on every request,
- reads the `platform_csrf` cookie and sends `X-CSRF-Token` on every non-GET request,
- **no token state, no storage access**,
- on `401 STEP_UP_REQUIRED` → dispatch a step-up event; do not log out,
- on `401 TOKEN_EXPIRED` → call `/auth/refresh` once, then retry the original request once,
- on `401 SESSION_REVOKED` / `REFRESH_INVALID` → clear in-memory admin state and route to login,
- never logs cookies, CSRF tokens, request bodies, or credentials to console.

`platformAuth.tsx`:

- state: `admin`, `loading`, `mfaTicket` (memory only), `stepUpOpen`,
- `login(email, password)` → sets `mfaTicket`, routes to `/mfa`,
- `verifyMfa(code)` → server sets cookies, then loads `/me`,
- `has(permission)` → checks `admin.permissions`,
- `logout()` → calls `/auth/logout` (clears cookies server-side), resets state,
- `refresh()` on mount to recover an existing session cookie.

### 2.2 Credential storage

- **No token is stored in JS.** Access and refresh tokens are HttpOnly cookies set by the server.
- The only JS-readable value is the non-secret `platform_csrf` cookie, used for the double-submit header.
- No `localStorage`. No `sessionStorage`. No token in URL, hash, `postMessage`, or analytics.
- The access cookie is 15 minutes; the admin app refreshes transparently before it expires (or on a 401) and routes to login after the 12-hour absolute session cap.
- `mfa_ticket` and `enrollment_ticket` live in component memory only; a page reload restarts login.

### 2.3 Guards

`AdminGuard`:

1. `loading` → skeleton.
2. no session (first `/me` 401 and refresh fails) → `<Navigate to="/login" replace />`.
3. `/me` fails for a non-auth reason → error state with request id, not a login loop.
4. `admin.mfa_enabled === false` → force enrollment route.
5. route permission missing → `AdminForbidden` component (not a redirect loop).

The guard never inspects a token; it only uses the `/me` response.

## 3. Visual and interaction language

| Tenant app | Platform app |
|------------|--------------|
| Branded, warm, customer-facing | Dense, neutral, utilitarian |
| `data-theme="management"` | `data-theme="platform"` |
| Restaurant name in sidebar | “Platform Console” + environment badge |
| Large cards, friendly copy | Compact tables, explicit status badges |
| Tenant navigation | Platform navigation with permission gating |

Layout:

- Fixed left sidebar (240 px), collapsible on mobile.
- Top bar: breadcrumb, environment badge (`LOCAL` / `STAGING` / `PRODUCTION`), date/time in UTC, admin menu.
- Content max-width 1400 px, tables full width.
- Color semantics: green = active/paid, amber = trial/past due/grace, red = suspended/void/failed, gray = archived/cancelled.
- No tenant branding, logos, or theme colors inside `/admin`.

## 4. Pages

### 4.1 Login + MFA

- `AdminLoginPage`: email, password, generic error, lockout message with retry time.
- `AdminMfaPage`: 6-digit input, auto-submit at 6, “use a recovery code” toggle, back to login. Recovery-code use warns that re-enrolment is required.
- `AdminEnrollMfaPage`: QR + manual secret, recovery codes download/copy (shown once), verify code.
- `StepUpDialog`: password + TOTP, triggered by `STEP_UP_REQUIRED`, retries the original action once on success.
- Never prefill credentials; never store the password.

### 4.1a Accept-invite pages

- `/invite/:token` (tenant owner, served by the tenant app): validates the token, shows tenant name + email, collects display name + password + confirmation, submits, then routes to `/login` with a success message.
- `/invite/:token` (platform admin, served by the admin app): same flow, then routes to `/login`.
- Expired/used token: a clear “this invitation is no longer valid” state with a support contact; never reveal whether the email exists.
- Password rules are shown inline and validated server-side.
- The token is never placed in `localStorage`, `sessionStorage`, analytics, or the URL after acceptance.

### 4.2 Dashboard

- Date-range selector: today, 7d, 30d, this month, custom (max 366 days).
- KPI cards: tenants (total/active/trial/suspended), active subscriptions, MRR, ARR, collections, pending payments, failed payments, trial conversion, churn.
- Each card is a link to the filtered list where applicable (`tenant.suspend` → suspended tenants).
- Health card: API/DB/migrations, last checked.
- Recent activity: last 10 audit entries, link to audit page.
- Empty state when there are no tenants: “No tenants yet. Create the first tenant.”
- Every number shows its definition in a tooltip/popover (`definitions_version`).

### 4.3 Tenants

- List: search, status filter, plan filter, sort by created/name, pagination.
- Row actions: view, suspend/reactivate (permission + step-up), force logout.
- Create drawer: name, slug (auto from name, editable), owner email, plan, trial days, contact fields, source, reason. Shows the one-time invitation link after success with a copy button and a warning that it will not be shown again.
- Detail tabs: Overview, Subscription, Usage, Audit, Diagnostics.
- Suspend dialog: reason (min 10), typed slug confirmation, summary of active sessions/branches, warning about D-6 behavior.
- Reactivate dialog: reason + confirmation.
- Force logout: reason + confirmation; shows revoked membership count.

### 4.4 Plans

- List: code, name, monthly/annual price, trial days, live subscriptions, status.
- Detail/edit: prices, trial, entitlements editor (limits and toggles), public flag, sort order.
- Save requires reason. Show a warning when editing a plan with live subscriptions: “Existing subscriptions keep their current price until renewal.”
- Archive action is disabled with a tooltip when live subscriptions exist.

### 4.5 Subscriptions

- List: tenant, plan, status, period end, trial end, cancel flag.
- Detail: timeline of events, current period, plan snapshot, linked invoices.
- Actions: change plan, extend trial, cancel at period end, reactivate. All require reason; destructive ones require step-up.
- Status changes are not free-form. No “set status to ACTIVE” dropdown.

### 4.6 Invoices and payments

- Invoice list: number (`INV-{FY}-{sequence}`), tenant, total, status, due date, paid date, refunded amount.
- Create invoice: tenant picker, optional subscription, dynamic line items (kind, description, qty, unit amount), discount, due date, notes, reason. Totals computed live but server-authoritative. The number is assigned by the server; the UI never proposes one.
- Detail: line items, totals, issuer snapshot (name/PAN/VAT status), `tax_treatment`, payment history, **append-only payment-event timeline**, actions (void, pay, request refund). If `tax_treatment` is `UNCONFIRMED`, show an amber “tax template not yet approved” notice; do not imply legal compliance.
- Payment instructions: a read-only panel with the company QR/bank instructions and a copy button, plus a print/PDF-friendly view the operator can send to the owner through the approved channel (email is PA-2). There is no “mark as paid” action visible to the owner.
- Pay dialog: method, amount, reference, provider reference, **optional evidence upload**, paid date, reason. The transaction reference is required unless the audited cash exception is used. Evidence is uploaded to the private store; the UI receives an object key, never a public URL, and shows the detected type/size. Cash without a reference requires an explicit exception reason and shows a warning. Generates an idempotency key client-side per attempt and reuses it on retry. Duplicate reference errors are shown inline on the reference field.
- Evidence viewing: the detail page requests `GET /payments/{id}/evidence-url` on demand and opens the short-lived signed URL in a new tab. No evidence is embedded or cached by the SPA. If evidence is absent, show “No evidence attached — verified by reference” rather than an error.
- Refund dialog: amount, reason code, note, original payment reference, destination, external refund reference (if already known), optional evidence, and `processed outside platform`. It does **not** show a threshold; while the risk policy is deferred it explains “Second approval policy not yet defined; this action will be recorded as single approval.”
- Refund queue (`/refunds`): pending/approved requests, requester, approver, amount, reason, destination, external reference. Approve and Complete are separate actions, permission-gated, each requiring step-up. The queue shows `single_admin_approval` as a neutral label, not as an error. There is no threshold-based disable state in PA-1.
- Confirmed payments have **no edit control**. The only corrective actions are void (superadmin, reason) and refund.
- Money formatting: reuse `formatMoney(minor, currency)` from the shared lib; never hand-format, always show the currency code.

### 4.7 Platform users

- List: email, display name, role, status, MFA status, last login, recovery-codes remaining.
- A persistent banner when fewer than two active superadmins exist: “Commercial launch requires two real, named superadmins. Invite the secondary admin; do not create a placeholder.”
- Invite: email, name, role, reason; returns a one-time invitation link with a copy button and a “shown once” warning.
- Change role / disable / reset MFA / reset password: reason + step-up; disable shows a warning that all sessions are revoked.
- The last active superadmin row has destructive actions disabled with an explanation (`409 LAST_SUPERADMIN` on the server too).
- Reset MFA shows the emergency procedure link and requires typed confirmation of the admin email.

### 4.8 Audit

- Filters: action, tenant, actor, date range, free-text in entity/reason.
- Table: time, actor, action, target, tenant, reason (truncated), request id.
- Detail drawer: full before/after JSON, IP, UA, request id, link to tenant.
- Read-only. No edit/delete controls.
- Export button (CSV/NDJSON) with a confirmation; export is audited.

### 4.9 Settings

- Grouped allowlisted fields: company, support email, default currency (NPR), invoice prefix, fiscal-year start month, invoice issuer name/address/PAN/VAT status/VAT number/template version/tax treatment, payment instructions text + QR asset, default trial days, trial extension limits, grace days, export retention, evidence max size/allowed types/signed-URL TTL, session/step-up/login limits.
- Numeric limits show the current value and the consequence of changing it (for example, a new evidence size cap applies to new uploads only).
- The refund second-approval threshold is **not** a field in PA-1; show a read-only note that the policy is deferred.
- Invoice issuer/tax fields show a warning that changes affect new invoices only and do not constitute legal/tax advice.
- Save requires reason + step-up. Show “last changed by / when”.
- No arbitrary key/value editor.

### 4.10 Diagnostics

- Platform health card.
- Tenant picker → check list with status icons, details, and a “copy support summary” button (no PII beyond contact fields).
- Link to the tenant’s audit.

### 4.11 Profile

- Display name, email (read-only), role (read-only), MFA status, last auth.
- Change password, re-enroll MFA, view/revoke own sessions, sign out everywhere, sign out.

## 5. Shared components

Create under `apps/web/src/pages/admin/components/`:

| Component | Purpose |
|-----------|---------|
| `AdminPageHeader` | Title, subtitle, actions |
| `MetricCard` | Label, value, delta, definition tooltip, link |
| `DataTable` | Columns, sorting, empty/loading/error states, pagination |
| `StatusBadge` | Consistent color semantics |
| `ReasonDialog` | Reason textarea + validation + confirm |
| `DangerDialog` | Reason + typed confirmation + step-up handling |
| `Money` | `formatMoney` wrapper |
| `DateRangePicker` | Presets + custom, capped at 366 days |
| `PermissionGate` | Hides children when permission missing |
| `ForbiddenState` | Clear 403 page |
| `ErrorState` | Problem+json detail + request id |
| `LoadingSkeleton` | Table/card skeletons |
| `CopyOnceField` | One-time invitation token with copy + warning |
| `StepUpProvider` | Global step-up modal + retry queue |

Do not introduce a UI framework or state library for this. Use the existing CSS conventions and add a `platform.css` scoped by `[data-theme="platform"]`.

## 6. Data fetching and state

- One small `usePlatformQuery` hook (or page-local `useEffect`/`AbortController`) — no React Query dependency.
- Every list page supports: loading, empty, error, forbidden, and stale-data refresh.
- Mutations are explicit: button → dialog → submit → disable while pending → success toast + refetch.
- No optimistic updates for destructive actions. Optimistic updates are allowed only for non-destructive toggles if rollback is implemented.
- Cancel in-flight requests on unmount.
- Never swallow errors silently; show `problem.detail` and `request_id` for support.
- Cache is per-page; no global cache in MVP.

## 7. Permission-gated navigation

```ts
const ADMIN_NAV = [
  { to: "/", label: "Dashboard", permission: "platform.dashboard.view", end: true },
  { to: "/tenants", label: "Tenants", permission: "tenant.view" },
  { to: "/plans", label: "Plans", permission: "plan.view" },
  { to: "/subscriptions", label: "Subscriptions", permission: "subscription.view" },
  { to: "/invoices", label: "Invoices", permission: "invoice.view" },
  { to: "/payments", label: "Payments", permission: "invoice.view" },
  { to: "/refunds", label: "Refunds", permission: "payment.refund.approve" },
  { to: "/platform-users", label: "Platform users", permission: "platform_user.view" },
  { to: "/audit", label: "Audit log", permission: "audit.view" },
  { to: "/settings", label: "Settings", permission: "settings.view" },
  { to: "/diagnostics", label: "Diagnostics", permission: "diagnostics.view" },
];
```

The nav hides unauthorized links, but the route guard still checks. Hiding is UX; the server is security.

## 8. Security and UX rules

1. No tenant data is rendered in a platform page beyond the explicitly allowed fields (contact, counts, subscription, invoices).
2. No “login as tenant” button, link, or hidden route in MVP.
3. Destructive dialogs always show the target name/slug/number and require typed confirmation.
4. Step-up is handled centrally; a failed step-up cancels the action and leaves the page intact.
5. One-time tokens (invitations, password resets) are shown once with a copy button and a warning; they are never placed in the URL hash or logs.
6. All timestamps display in UTC with a `UTC` label; tenant-local times are labeled when shown.
7. Money always shows the currency code.
8. No secrets, API keys, or password hashes in any response or UI.
9. The environment badge is always visible in production (`PRODUCTION`) to reduce operator mistakes.
10. Session expiry shows a re-login prompt, not a silent redirect mid-form.
11. **No credential is ever written to JS storage.** The admin client uses HttpOnly cookies + `X-CSRF-Token`; a lint rule or code review check rejects `localStorage`/`sessionStorage` usage for auth.
12. The admin app is served only from the admin origin in production, with its own CSP; `connect-src` is limited to the API origin.
13. Payment evidence is fetched through a short-lived signed URL on demand; the admin app never embeds untrusted HTML, never stores the URL, and never executes uploaded files.
14. Refund UI shows requester, approver, and completer separately, and labels `single_admin_approval` honestly; there is no threshold control in PA-1.

## 9. Accessibility

- Keyboard reachable: all dialogs trap focus, `Esc` closes, first field autofocuses.
- Labels for every input; errors linked with `aria-describedby`.
- Status is never conveyed by color alone (badge text + icon).
- Tables have captions and sortable headers with `aria-sort`.
- Contrast meets WCAG AA in the platform theme.
- Reduced-motion support for transitions.

## 10. Responsive behavior

- Desktop-first (operators use laptops).
- Sidebar collapses under 1024 px; tables scroll horizontally rather than hiding columns.
- Dialogs become full-screen sheets under 640 px.
- No mobile-specific feature set in MVP; the app must remain usable for an emergency suspension from a phone.

## 11. Build and verification

- `npm run build` must stay clean (`tsc -b && vite build`) for the **tenant** app.
- `npm run build:admin` runs `vite build --config vite.admin.config.ts` and must stay clean.
- The two builds are independent: the tenant bundle must not contain admin pages, and the admin bundle must not include tenant staff pages.
- Route-level code splitting inside each app keeps initial bundles small.
- The admin build sets `VITE_PLATFORM_API_URL` and rejects a build where the API URL is not HTTPS in production mode.
- Manual smoke script in `08-testing-and-acceptance.md`.
- If a frontend test runner is added during PA-1.4, cover: permission gating, step-up retry, reason validation, CSRF header presence, money formatting, and one list/detail render per page. Do not block MVP on a full E2E suite.
- Browser verification: 0 console errors on every admin route, including 401/403/409/CSRF paths, with no credential values in `localStorage`/`sessionStorage`.
