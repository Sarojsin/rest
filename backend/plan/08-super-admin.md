# Super Admin (Platform) Realm

Cross-references: auth `05 §8` — endpoints `14 §3` — audit schema `03 §2` — roadmap `22 Phase 5` (thin) and optional Phase 6, Phase 10.

**Execution plans for the expanded Super Admin product:** `super_admin/00-README.md`. That folder converts `super_admin_plan.md` into a controlled PA-0 → PA-3 roadmap. This file remains the security/philosophy source; the PA-1 MVP is a superset of the Phase 5 thin build and does not change the Phase 5 realm rules.

**Philosophy:** "powerful, therefore dangerous." The super admin is a *different product* (separate app, auth, design language — denser, utilitarian — to prevent accidental context confusion), and it edits *platform* data only; tenant operational data is edited by the tenant's own staff in their dashboard. Support views; ops act; superadmin configures.

## 1. Realm hard rules

1. Auth: `platform_admins` JWT only (`realm: "platform"`); separate secret; HttpOnly access + refresh cookies host-only to `api.platform.com`; admin app served from `admin.platform.com`; never shares cookies with app or tenant subdomains.
2. Every route requires an explicit platform role; no implicit superadmin catch-all.
3. Every state-changing action: mandatory `reason` → `platform_audit_logs` with before/after; owner email notification is PA-2 (no mail transport in MVP — the audit log is the source of truth).
4. Destructive actions (delete data, force logout-all, plan change, refund approval) additionally require the right role, typed confirmation, and fresh re-auth (`auth_time` ≤ 5 minutes, configurable; else step-up).
5. Read support agents can see counters and configuration but **never** PII beyond contact data and never card data (19 T10).
6. Impersonation: **not built in the pilot** (deferred; when it comes: read-only, superadmin role, tenant-owner email notice, separate ADR).

## 1.1 Break-glass: platform-admin recovery (the "locked out of our own platform" runbook)

Bootstrap-from-env (05 §9) covers day 0 only. Four failure modes are covered:

1. **Compromised superadmin:** disabled via another superadmin (or break-glass path 3); `token_version` bump kills all sessions; password rotated; `platform_audit_logs` entry with IP/UA.
2. **Lost env vars / credentials:** `BOOTSTRAP_PLATFORM_ADMIN_*` remains functional on a running system — startup re-assert is idempotent: if the bootstrap admin is missing *or* disabled, it is re-created/re-enabled from env (audited loudly, email to all other admins). Losing the env file is a password reset, never a lockout.
3. **All superadmins locked out (true break-glass):** a sealed *Break-Glass Runbook* — offline copy, **two-person rule** (execute only with two platform-staff signatures), logged in `platform_audit_logs` post-act with both signatories. Two accepted mechanisms: (a) direct managed-Postgres access via the ops secret store to set `platform_admins.status='active'` for a designated recovery account; (b) re-deploy with fresh bootstrap env vars so the idempotent startup re-assert (path 2) restores access. Rehearsed once in staging in Phase 10 (same drill cadence as the backup-restore drill).
4. **Seat policy (prevention):** while any real tenants exist, **≥2 `superadmin` accounts are mandatory** — the admins-management UI refuses to remove/superadmin-demotion of the last active superadmin (app-level invariant + unit test); a daily ops email shows the current superadmin roster count.

Invariant across all recovery paths: **no recovery is ever silent** — every path writes `platform_audit_logs` (even the direct-SQL path, post-act with actor + two-person sign-off) and notifies the remaining admins.

## 2. Platform roles × permissions

| Code | support | billing | ops | superadmin |
|------|---------|---------|-----|------------|
| tenant.view, tenant.search, audit.view | ✅ | ✅ | ✅ | ✅ |
| tenant.suspend / tenant.reactivate / tenant.force_logout | — | — | ✅ | ✅ |
| tenant.create (incl. send invite) | — | — | ✅ | ✅ |
| plan.view | ✅ | ✅ | ✅ | ✅ |
| plan.update (affects all tenants; sensitive) | — | — | — | ✅ |
| invoice.view | ✅ | ✅ | ✅ | ✅ |
| invoice.void / invoice.refund / invoice.create (manual MVP) | — | ✅ | — | ✅ |
| subscription.override (entitlement override w/ expiry) | — | — | — | ✅ |
| billing_events.view, analytics.view | ✅ | ✅ | ✅ | ✅ |
| admins.manage, feature_flags.manage | — | — | — | ✅ |

## 3. Audit discipline

- Write occurs **in the same transaction** as the action; rollback takes the audit row down too (no phantom logs).
- Every entry: actor admin id, action code, entity ids, tenant_id when applicable, reason (mandatory non-empty for mutations), request_id, ip, ua, before/after JSONB.
- Immutable (append-only grants from M5).
- Retention 3 years (23 pending); searchable from super admin (25 §5).

## 4. Endpoint surface (thin build ⊂ full inventory in 14 §3)

```
POST /api/platform/auth/login | /refresh | /logout
GET  /api/platform/tenants?status=&plan=&q=
POST /api/platform/tenants                     # create shell + send owner invite (24 §2 door B);
                                               # body includes mandatory source: 'sales-assisted'|'self-serve'|'migrated'
                                               # (attribution for platform audit — 08 §3)
GET  /api/platform/tenants/{id}                # profile, subscription, branches, usage, recent audit
POST /api/platform/tenants/{id}/suspend        { reason }
POST /api/platform/tenants/{id}/reactivate     { reason }
POST /api/platform/tenants/{id}/force-logout   { reason }
GET  /api/platform/plans | PATCH /api/platform/plans/{id}        (superadmin)
GET  /api/platform/subscriptions?tenant_id=
POST /api/platform/invoices                    { tenant_id, amount, due_at }   # manual MVP
POST /api/platform/invoices/{id}/void|pay|refund   { reason }
GET  /api/platform/audit-logs?action=&tenant_id=
GET  /api/platform/analytics                   # read-only aggregates (25 §6)
POST /api/platform/webhooks/stripe             # optional Phase 6 (06 §3)
```

Every response includes `tenant_status` so an operator never acts out of context.

## 5. Thin-build scope cut (Phase 5 — what we DO and DON'T build)

| Build now (1 wk) | Deliberately later |
|-------------------|--------------------|
| Tenant list/search/detail, create + invite, suspend/reactivate/force-logout (reason+audit+email) | Analytics dashboards (one aggregate endpoint only) |
| Plans as rows (seeded, viewable; edit superadmin-only via console-level ADR — acceptable until Phase 6) | Plans CRUD UI, feature-flag manager |
| Manual `platform_invoices` create/void/pay | Refund flows against gateways, credits UI |
| Audit log viewer (filter+search, read-only) | Impersonation, admins management UI (bootstrap admin manages co-admins via env/SQL until superadmin UI) |

## 6. Suspension workflow (links D10)

Automated lifecycle vs manual ops suspension use different code paths (`lifecycle.py` vs `tenant_actions.py`). Manual suspension requires reason (free text, min 10 chars), shows a confirm listing in-flight dining sessions count, emails owner, and schedules graceful gates per 04 §7. Reactivate: same rigor, restores subscription/active.force-logout bumps all member `token_version`s — sessions die in ≤1 access-token lifetime.
