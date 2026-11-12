# Plan: Single shared customer domain for all restaurant QR menus

## Goal
Deploy the customer-facing menu frontend **once** on one domain (e.g. `menu.platform.com`). Every restaurant's QR code points to `https://<shared-domain>/t/{qr_token}`, and the backend resolves the token to the correct restaurant menu. No per-restaurant domain purchase or DNS required.

## Why this works (current code supports it)
- Frontend route: `/t/:qrToken` → `CustomerMenuPage` (E:\rest\apps\web\src\App.tsx:115)
- `CustomerMenuPage` calls `GET /api/v1/public/qr/{token}/menu` on the backend (CustomerMenuPage.tsx:153), which resolves the QR token → table → restaurant (orders.py:173 `resolve_qr`). The restaurant is identified by the token, **not** the hostname.
- QR URL is built in `TablesPage.tsx` `buildUrl()` from `customer_hostname` (restaurant settings). Currently it builds per-restaurant hostnames; we change it to always use one shared domain.

## Decisions
1. **One shared domain**: `customer_domain_base` from settings (default `platform.com`), or a new `customer_qr_domain` setting. QR URLs: `https://<shared-domain>/t/{qr_token}`.
2. **Hostname enforcement relaxed**: `assert_qr_hostname` currently 403s if the Host isn't the restaurant's own subdomain/custom domain. Change so the shared domain is valid for every restaurant (token owns the restaurant; hostname no longer gates tenancy).
3. **Restaurants with custom domains**: keep them working — if a restaurant sets `custom_domain`, its QR can still use that domain, but it's optional, not required.
4. **Frontend deployed once**: single Static Site / SPA on the shared domain. Backend stays one service.
5. **Dev/local**: `localhost:5173/t/{token}` works without DNS (existing dev behavior).

## Affected files (implementation targets)
- `apps/web/src/pages/staff/TablesPage.tsx` — `buildUrl()`: always emit `https://<shared-domain>/t/{token}` (or `${window.location.origin}/t/{token}` in dev).
- `backend/app/modules/tenancy/services/hostname.py` — `assert_qr_hostname()`: allow the shared domain for all restaurants; keep custom-domain check for restaurants that set one.
- `backend/app/core/config.py` — optional new setting `customer_qr_domain` if you want it separate from `customer_domain_base`.
- `apps/web/src/pages/staff/TablesPage.tsx` — comment (lines 95-98) references per-restaurant hostname; update to reflect shared domain.

## Not in scope
- Per-restaurant DNS / custom domain purchase (optional only).
- Multi-tenant data isolation changes (token already scopes to restaurant).
- Backend/frontend infra beyond existing Render deploy plan (`deploy.md`).

## Validation checklist
1. Backend starts with shared domain config; `POST /api/v1/menu/items/{id}/image` (Cloudinary) still works.
2. Create a restaurant + table → QR URL shows `https://<shared-domain>/t/{token}`.
3. Scan/open `https://<shared-domain>/t/{token}` → loads `CustomerMenuPage` and fetches menu for that restaurant.
4. Two different restaurants' QR codes on the same domain load different menus.
5. Restaurant with a custom domain still works on that custom domain.
6. Wrong hostname on a restaurant *without* custom domain → still allowed (shared domain). Wrong custom-domain host → 403 (fail closed).

## Open question (needs your answer before implementation)
Should the shared domain be `settings.customer_domain_base` (`platform.com` → QR URLs on `platform.com`), or a new dedicated setting `customer_qr_domain`? Recommended: new `customer_qr_domain` setting so the QR surface can differ from other `platform.com` uses.