# API Contracts & Error Catalog

**Versioning:** `/api/v1/*` (staff+customer), `/api/qr/*` (customer), `/api/platform/*` (super admin) — separate OpenAPI documents, generated clients on merge to main, breaking change ⇒ ADR + deprecation policy.

## 1. Staff surface (`/api/v1`, staff realm)

```
POST /auth/login            → tokens + tenants[] (or single-tenant straight-in)
POST /auth/refresh          → rotating per (user, tenant)
POST /auth/switch-tenant    { tenant_id }            (05 §4)
POST /auth/logout
GET  /tenant                → profile + entitlements
GET  /tenant/usage          → (07 §6)
GET  /branches | POST /branches | PATCH /branches/{id} | POST /branches/{id}/archive
GET  /menu/categories | POST/PATCH/...            (tenant catalog, 10)
POST /menu/items/{id}/draft|publish|discard      (10 §3)
GET  /menu/public?branch_id=                       (merged view)
POST /menu/overrides/{item}/{branch}             (availability/price/hide)
GET  /tables?branch_id=    (required)
POST /tables | POST /tables/{id}/qr/rotate
GET  /dining-sessions?branch_id=&status=
POST /orders                    (waiter; branch derived from session/table)
POST /orders/{id}/accept|reject|serve-items|amend|cancel
GET  /orders/pending-qr         (branch queue)
POST /kitchen/tickets/{id}/start|ready|cancel
GET  /bills?branch_id=&status= | POST /bills/{id}/issue
POST /bills/{id}/payments      (cash/card/online-init)
POST /bills/{id}/discount|void-item       (permission + reason)
GET  /service-calls?branch_id= | POST /service-calls | POST /{id}/acknowledge
GET  /reports/...              (25)
GET  /memberships | POST /memberships | PATCH /{id}  (invite/role/branch-scope/disable)
GET  /audit-events?...         (tenant's own audit view, owner/manager)
```

## 2. Customer surface (`/api/qr`, token realm)

```
POST /qr/sessions          { qr_token }   → session token + public menu + branch/tenant branding
POST /qr/{session}/orders  (idempotent, PENDING_CONFIRMATION)
GET  /qr/{session}         → order states, bill when surfaced
POST /qr/{session}/waiter-request          (Phase 8)
POST /qr/{session}/bill/payment-init       (online_payments entitlement)
```

## 3. Platform surface (`/api/platform`) — inventory in `08 §4`; every response includes `tenant_status`.

## 4. Error-code catalog (UI switches on code; full contract `21 §5`)

| Code | HTTP | Meaning / client behavior |
|------|------|---------------------------|
| `TENANT_SUSPENDED` | 403 | suspended gate hit by mutation; show restore-CTA screen |
| `TENANT_EXPIRED` | 403 | read-only state surface |
| `ENTITLEMENT_EXCEEDED` | 409 | show upgrade prompt (coupon of details in 07 §2) |
| `FEATURE_DISABLED` | 409 | plan feature false |
| `PRICE_CHANGED` | 409 | re-confirm with new prices |
| `ORDER_ITEM_UNAVAILABLE` | 409 | remove/replace item in cart |
| `QR_TOKEN_INVALID` / `QR_TOKEN_REVOKED` | 404/Gone | dedicated entry-error screens |
| `SESSION_CLOSED` | 409 | customer session ended; restart scan |
| `MEMBERSHIP_REVOKED` | 403 | access lost; sign-out with message |
| `PERMISSION_VERSION_MISMATCH` | 401 | refresh + retry once, else sign-out |
| `PERMISSIONS_CHANGED` | 403 | demotion mid-shift end-of-session message |
| `CONCURRENT_MODIFICATION` | 409 | stale aggregate version; reload |
| `REALM_MISMATCH` | 401 | token used in wrong realm (bug/attack signal — alert) |
| `VALIDATION_ERROR` | 422 | field errors |
| `RATE_LIMITED` | 429 | backoff |
| `IDEMPOTENT_REPLAY` | 200 | replay result body (see 21 §7) |
| `IDEMPOTENT_CONFLICT` | 409 | same key, different payload |
| `UNAUTHORIZED` | 401 | missing/invalid/expired token; refresh flow |
| `FORBIDDEN` | 403 | same-tenant, insufficient permission (the 05 §5 403 case) |
| `NOT_FOUND` | 404 | generic absence — incl. cross-tenant 404s, deliberately indistinguishable |
| `CONFLICT` | 409 | generic state conflict not covered by a specific code |
| `INTERNAL_ERROR` | 500 | scrubbed; incident id in `details` |

The catalog is exhaustive: the UI must never fall back to message matching, so every client code path maps to a listed code. Any response code missing from this table is a bug (asserted in the API contract tests, 18 §1).

Rules: no string-matching on messages; every error carries `code`, stable `details`, `request_id`; 500s get scrubbed messages + internal incident id.

## 5. Deprecation policy

- Old endpoint keeps working and emits `Deprecation: <date>` header + usage log from the stage where a replacement ships.
2. Sunset = ≥90 days or "all logged clients migrated", whichever later; internal clients tracked in `docs/api-contracts.md` table.
3. Customer QR URL shape `/:token`-based deep link unchanged through the whole migration (11 backward-compat concern).

## 6. Request conventions

- Idempotency: `Idempotency-Key` on all POST mutations that create business objects (orders, payments, sessions, invites). Uniqueness `(branch_id, scope, key)` (04 §6).
- Pagination: cursor-based (`?cursor=&limit=50`, max 200).
- All mutations carry `If-Match`/version where aggregates allow optimistic checks (bills).
- Sorting/filtering whitelisted per endpoint; unknown params ignored, never passed to SQL.
