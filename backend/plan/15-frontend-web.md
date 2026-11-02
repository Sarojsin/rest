# Frontend (Web) — Dashboard, Customer, Super Admin

## 1. App surfaces

| App | Host | Notes |
|-----|------|-------|
| Restaurant dashboard (staff+owner) | `app.platform.com` | Multi-tenant; tenant/branch switcher in header |
| Customer web | `{tenant}.platform.com` | Tenant resolved from hostname + QR token; no auth |
| Super admin | `admin.platform.com` | Separate Vite app `apps/admin`; separate everything (08) |

Customer web stays a route of the same SPA bundle but boots "customer mode" purely from hostname — zero staff-only code paths reachable on a tenant subdomain.

## 2. Tenant/branch context (the two rules that prevent 90% of SaaS frontend bugs)

1. **URL is the context:** the current tenant is never trusted from a cookie alone; tenant and branch are in the URL (`?branch=<slug>`; tenant visually via subdomain for customer, via token+header state for staff).
2. **Cache keys are tenant+branch-scoped:** every React Query key includes `{tenantId, branchId}` (provided via a context factory); switching context ⇒ `queryClient.clear()` + cancel in-flight + reset server-derived Zustand stores + full refetch. A "loading branch/tenant" screen marks the reset as intentional (≤250ms).
3. Zustand rule: stores derived from server data are keyed or cleared on context switch; only pure-UI state (open drawers, draft forms) persists — and forms prompt before discard.

## 3. Auth wiring

- Access token in memory only; refresh in HttpOnly Secure cookie scoped to app.platform.com; 401 → refresh → retry once → else clean sign-out flow.
- Login response: tenants[] + last-used resolution; implicit picker UI only when needed.
- `TENANT_SUSPENDED` (restore CTA), `ENTITLEMENT_EXCEEDED` (upgrade prompt inline in creator flows — *disable+tooltip before form fill*, never error-after-submit), `PERMISSIONS_CHANGED`, `MEMBERSHIP_REVOKED` (14 §4).

### 3.1 Client-side entitlements snapshot (the exact behavioral contract)

The "disable before form fill" rule needs data before interaction; here is where it lives:

1. **Source:** the boot payload (`GET /api/v1/tenant` ⊕ `GET /tenant/usage`, also embedded in the switch-tenant response — 05 §4) provides `{ metrics: { branches: {used, limit, soft_mode}, staff_users: {...}, orders_per_month: {...} }, features: { online_payments, inventory, ... }, upgrade_hints: { branches: "growth", ... } }`.
2. **Caching:** React Query key `['tenant-usage', tenantId]` (tenant-scoped, not branch — branch UI doesn't consume limits), `staleTime: 60s`, refetch on window focus, and **mutation-linked invalidation**: any mutation that can change usage (`POST /branches`, `POST /memberships`, order creation) invalidates the key on success.
3. **Optimism rules:** optimistic *decrement* is allowed after a successful mutation (button state catches up fast); optimistic *re-enable* is **forbidden** — a disabled button re-enables only from fresh server data; the server stays the sole authority (client staleness can only over-disable, never over-enable).
4. **Compute:** disable-state = `used >= limit && !soft_mode`; tooltip copy comes from `upgrade_hints` + server-provided strings (07 §2 contract) — plan names are never hardcoded client-side. Soft-limit metrics render the ≥90% banner (07 §4) from the same snapshot.
5. **Degraded state:** if the snapshot fetch fails, forms render enabled and errors defer to the dedicated `ENTITLEMENT_EXCEEDED` screen — degraded behavior errs toward server enforcement, never toward blocking revenue unilaterally.

## 4. Multi-tab & notifications

- Multi-tab, multi-tenant supported (tenant from URL); BroadcastChannel syncs tokens between tabs.
- Notifications deep-link with tenant+branch parameters (13 §3); open refetches first, trusts nothing from payload except id.

## 5. Dashboard surface changes

- Header: tenant name + branch switcher (member branches with quick stats per 09 §1); tenant-wide context indicator (subtle colored edge strip — prevents "edited the wrong restaurant's menu").
- New screens: Tenant settings (profile/branding/billing-lite), Branch settings, Memberships (invite/roles/branch scoping), Usage banner (07 §6), Menu draft/publish manager (10 §3), Audit viewer (owner), Onboarding checklist (24 §3), Reports (25).
- Entitlement-aware components: `<Can perm="...">`, `<Feature flag="online_payments">` backed by ctx entitlements snapshot — display only (07 §1).

## 6. Kitchen / cashier / waiter views per branch

- Kitchen board, cashier and waiter surfaces and route to home branch automatically; switcher absent unless multi-branch member (09 §5).

## 7. Super admin app (separate)

- `apps/admin` Vite app with its own auth, design language, deploy; thin-build scope in 08 §5. Reuses `packages/ui` primitives but no dashboard layouts.

## 8. Customer-web changes

- Branding: tenant display_name + branch subtitle from session boot payload; platform footer only.
- Handles: QR errors as screens (12 §1), PRICE_CHANGED confirm sheet, SSE order tracking + polling fallback, waiter-request states, bill→pay flow with "Verifying…" state (12 §7).
- PWA-grade offline behavior: readonly cached menu view + "offline — orders disabled" honest banners; no silent mutations.
