# Super Admin (Platform) Realm

Cross-references: auth `05 §8` — endpoints `14 §3` — audit schema `03 §2` — roadmap `22 Phase 5` (thin) and optional Phase 6, Phase 10.

**Philosophy:** "powerful, therefore dangerous." The super admin is a *different product* (separate app, auth, design language — denser, utilitarian — to prevent accidental context confusion), and it edits *platform* data only; tenant operational data is edited by the tenant's own staff in their dashboard. Support views; ops act; superadmin configures.

## 1. Realm hard rules

1. Auth: `platform_admins` JWT only (`realm: "platform"`); separate secret; HttpOnly cookie at `admin.platform.com`; never shares cookies with app or tenant subdomains.
2. Every route requires an explicit platform role; no implicit superadmin catch-all.
3. Every state-changing action: mandatory `reason` → `platform_audit_logs` with before/after → owner email notification (except purely read views).
4. Destructive actions (delete data, force logout-all, plan change) additionally require role ≥ `superadmin` and fresh re-auth (`last_auth_at` ≤ 60m; else step-up login).
5. Read support agents can see counters and configuration but **never** PII beyond contact data and never card data (19 T10).
6. Impersonation: **not built in the pilot** (deferred; when it comes: read-only, superadmin role, tenant-owner email notice, separate ADR).

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
POST /api/platform/tenants                     # create shell + send owner invite (24 §2 door B)
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
