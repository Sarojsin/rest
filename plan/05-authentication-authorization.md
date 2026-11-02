# Authentication & Authorization — Three Realms

**Locked (D3):** staff, customer, and platform realms share no code path and no token trust. A staff JWT must be unusable against `/api/platform/*` and vice versa; enforced by realm claim check *before* signature trust decisions and by separate secrets.

## 1. Realm overview

| Realm | Who | Access token | Refresh | Routes | Cookie/Storage |
|-------|-----|--------------|---------|--------|----------------|
| Staff | waiter, kitchen, cashier, manager, owner | JWT 15m | rotating, 7d, per (user, tenant) | `/api/v1/*` | Web: HttpOnly cookie (app.platform.com); Mobile: secure-store |
| Customer | QR diners | session token 30m, bound to table+session | none (session expiry) | `/api/qr/*` | Cookie scoped to tenant subdomain |
| Platform | platform admins | JWT 30m | rotating, 12h | `/api/platform/*` | HttpOnly cookie on admin.platform.com |

## 2. Staff access token claims

```json
{
  "sub": "<user_id>", "realm": "staff",
  "tenant_id": "<active tenant>", "membership_id": "<membership>",
  "branch_ids": ["<uuid>"],            // empty array = tenant-wide, no operational scope
  "perms": ["order.accept_qr", "..."], // snapshot for optimization only
  "pv": 3, "jti": "<uuid>", "iat": ..., "exp": ...
}
```

- **Permission source of truth is the DB.** Request path: resolve effective perms from `membership_roles → roles → role_permissions` (+ membership_branches); compare `pv`. On `pv` mismatch → `401 PERMISSION_VERSION_MISMATCH` → client refreshes and retries once; second failure ⇒ sign-out.
- `pv` is a per-membership counter on `memberships` (new column, M2 — `permission_version INT NOT NULL DEFAULT 1`). Bumped on any role/branch/permission change for that membership.
- `jti` enables per-token revocation (logout-all, forced rotation). Access tokens remain stateless; revocation lists live in Postgres (`revoked_jti` keyed by jti + exp, cleaned by cron) — no Redis (D7).

## 3. Refresh token design

- Row per `(user_id, tenant_id)` in `refresh_tokens` (existing table gains tenant binding): `token_hash`, `user_agent`, `ip`, `expires_at`, `used_at`, `revoked_at`.
- Rotation on every use; reuse of a rotated token ⇒ revoke the entire family + bump `users.token_version` (stolen-token defense). Hashed at rest.
- Password change bumps `users.token_version` and revokes the family.
- Tenant switch mints a *new* refresh bound to the target tenant; the old tenant's refresh survives independently (multi-tab, multi-tenant is supported — 15 §4).

## 4. Tenant switching

```
POST /api/v1/auth/switch-tenant { tenant_id }
  → verify memberships row (user, tenant, status='active')
  → issue new access + refresh for that tenant
  → response includes tenant profile + entitlements for fresh surface boot
```

- Login returns `tenants[]` + last-used tenant resolution (`last_used_at` column on `memberships`, M2). One tenant ⇒ straight in; many ⇒ picker (default picker only when no last-used OR user explicitly switches).
- Revoked membership ⇒ next request fails `403 MEMBERSHIP_REVOKED` within one access-token lifetime, instantly on `pv` bump.

## 5. Authorization model

Permission codes are a static, global catalog (schema.md §2.4, unchanged list + additions):

```
branch.manage, menu.manage, menu.publish, order.create, order.accept_qr,
order.cancel, order.serve, order.amend, kitchen.update, bill.manage,
bill.discount, payment.record, payment.refund, table.manage, qr.rotate,
staff.invite, staff.manage, settings.manage, tenant.export, report.view,
report.tenant_wide, tenant.manage          # + platform realm codes in 08 §2
```

Check pipeline (`require_permission(code, branch_scoped=False)` FastAPI dependency):

1. realm == staff (claim check) 2. live membership active 3. `code` ∈ effective perms (pv-verified) 4. if the resource is branch-scoped AND `branch_scoped=True`: require `resource.branch_id ∈ ctx.branch_ids` (permission `branch.unrestricted` is held by owner/manager system roles only). 5. pass `ctx` + loaded resource to the service, which re-verifies ownership (L3).

Rules:

- 404 not 403 for cross-tenant objects (do not leak existence); 403 reserved for same-tenant insufficient permission.
- No "silent admin override" of the pipeline; platform realm is a separate dependency `require_platform_role('...')` tightened in `08`.
- Owner/tenant-wide managers hold `report.tenant_wide`; operational permissions always require branch membership (`11 §1` — regional manager drills into a branch context to act).

## 6. Customer realm

- Session = signed token binding `{table_id, qr_code_id, dining_session_id, tenant_id, branch_id}`; 30m sliding, refreshed on activity; blocked at session close.
- No roles. Capability is structural: the session can only touch its own dining session's resources.
- Token + subdomain cross-check (12 §2): mismatch ⇒ specific error screen, no redirect (no leak vector).

## 7. Session invalidation matrix

| Event | Effect |
|-------|--------|
| Logout | revoke refresh + bump token_version (kills refresh family) |
| Tenant suspended | mark tenant.status + revoke every member's refresh; per-request gate still enforces D10 |
| Membership revoked | membership.status='revoked'; pv bump; next request 403 |
| Role/branch change | pv bump (immediate); token refresh picks it up |
| Password change | token_version bump + family revocation |
| QR rotated | old qr tokens `REVOKED`; active customer sessions for the old code get `QR_TOKEN_REVOKED` at next action |

## 8. Platform realm summary (detail in 08)

Separate secrets, separate router, `realm: "platform"` claim, IP allowlist optional per env, 30m access / 12h refresh, re-auth (<1h `last_auth_at`) required for destructive actions. Staff↔platform cross-use returns `401 REALM_MISMATCH`.

## 9. Bootstrap (changes from today)

Startup seeding: creates/repairs the **platform superadmin** from `BOOTSTRAP_PLATFORM_ADMIN_EMAIL/PASSWORD` env (fails fast, idempotent), seeds default plans, optionally seeds the demo tenant (flagged; 24 §5). **It never creates a tenant or restaurant** — the first tenant enters via migration (Path 1, D11) or registration (24 §2), exactly like every future one. Current `seed.py` restaurant creation is converted into the migration backfill script in `17-migration-runbook.md`.
