# 08 — Testing and Acceptance

**Gate rule:** no phase exits on a demo. It exits when the tests below pass, the acceptance script is executed, and the evidence is linked in the PR/phase note.

---

## 1. Test layers

| Layer | Tool | Scope | Runs |
|-------|------|-------|------|
| Unit | pytest | permission map, status transitions, TOTP, invoice totals, metric formulas, redaction | every PR |
| API integration | pytest + TestClient | auth, CRUD, lifecycle, billing, audit | every PR |
| Cross-realm / cross-tenant | pytest | isolation and authorization | every PR |
| Structure | pytest | import boundaries, no naive datetimes | every PR |
| Frontend build | `tsc -b && vite build` + `vite build --config vite.admin.config.ts` | type safety, bundles | every PR |
| Frontend unit (optional in PA-1.4) | Vitest + Testing Library | permission gates, dialogs, money, CSRF header | every PR if added |
| Manual browser smoke | browser/Playwright | every admin route, 401/403/409/CSRF paths | phase gate |
| Load smoke (PA-1.4) | script | dashboard + list endpoints with 10k tenants | phase gate |

No Redis/Celery/gateway test infrastructure is needed for MVP.

## 2. Test fixtures

Add to `backend/tests/conftest.py` or `tests/fixtures/platform.py`:

```python
platform_admin(role="superadmin", mfa=True, status="ACTIVE")
platform_admin_2(role="superadmin")            # dev/test fixture only; production second admin is a real invitee
platform_cookies(admin)                        # access + refresh + csrf cookie set
expired_platform_cookies(admin)
platform_client(admin)                         # cookie jar + automatic X-CSRF-Token
platform_client_without_csrf(admin)
platform_mfa_code(secret)                      # current TOTP
platform_plan(code="growth", ...)
tenant(status="ACTIVE", ...)
subscription(tenant, plan, status="ACTIVE")
invoice(tenant, lines=[...], status="OPEN")    # allocates FY sequence
payment(invoice, reference="BANK-001", evidence=None)  # evidence optional
staff_token(tenant, role="owner")
customer_token(table)
```

Rules:

- Fixtures must not depend on the demo seed; the test DB is wiped by `drop_all`.
- Cleanup order respects FKs: payment events → payments → invoice lines → invoices → invoice sequences → subscription events → subscriptions → plans → refresh tokens → audit → admins.
- Use one shared `platform_secret_key` for the test process; never the production value.
- Freeze time or use explicit timestamps for period/overdue tests.
- Generate TOTP codes with the same library and a fixed secret; do not mock the algorithm.
- Tests assert cookie flags by inspecting `Set-Cookie`, not by reading a body token.

## 3. Unit test matrix

### 3.1 Permissions

For every role in `{support, billing, ops, superadmin}` and every permission:

- allowed routes return 2xx,
- denied routes return 403 `PLATFORM_FORBIDDEN`,
- unknown role returns 403,
- platform routes reject staff tokens with 401 `WRONG_REALM`,
- staff routes reject platform tokens with 401.

### 3.2 TOTP / MFA

- valid code within ±1 step accepted,
- code outside window rejected,
- reused code rejected,
- recovery code accepted once, rejected on reuse,
- enrollment verifies and stores encrypted secret,
- reset clears MFA + bumps token version,
- missing MFA on a `platform_require_mfa=true` login returns `MFA_REQUIRED`.

### 3.3 Status machines

- subscription: every legal transition accepted; every illegal transition returns `INVALID_STATUS_TRANSITION`,
- invoice: DRAFT→OPEN→PAID; VOID only from DRAFT/OPEN; PAID cannot be voided; `VOID` keeps its number; `(fiscal_year, sequence_number)` is unique,
- payment: PENDING→CONFIRMED/FAILED; CONFIRMED→VOIDED only before activation; refund is a separate row in `REFUND_PENDING`→`REFUND_APPROVED`→`REFUNDED` or `REFUND_PENDING`→`REJECTED`; original never mutated; completion requires the external refund reference,
- tenant: ACTIVE↔SUSPENDED; CANCELLED cannot reactivate without a new subscription.

### 3.4 Money and metrics

- invoice line totals = quantity × unit,
- subtotal = sum(lines), total = subtotal − discount,
- no float arithmetic,
- MRR excludes trials, normalizes annual to monthly,
- collections only confirmed payments,
- pending = OPEN/OVERDUE with no confirmed payment,
- date-range boundaries inclusive/exclusive as documented,
- empty dataset returns zeros, not null.

## 4. API integration matrix

### 4.1 Auth

| Case | Expected |
|------|----------|
| valid password + valid TOTP | 200, no tokens in body, three cookies set with correct flags |
| access cookie flags | `HttpOnly; Secure; SameSite=Strict; Path=/api/platform` |
| refresh cookie flags | `HttpOnly; Secure; SameSite=Strict; Path=/api/platform/auth` |
| CSRF cookie | readable, `Secure; SameSite=Strict`, random |
| valid password + invalid TOTP ×5 | 401, then 429 lockout |
| disabled admin | 403 `ACCOUNT_DISABLED` |
| expired access cookie | 401 `TOKEN_EXPIRED` |
| revoked token version | 401 `SESSION_REVOKED` |
| refresh rotation | new cookies; old refresh rejected |
| refresh reuse | family revoked, `REFRESH_REUSE_DETECTED` audit |
| sign out everywhere | all refresh families revoked, access cookie rejected |
| logout | cookies cleared, refresh rejected |
| mutation without `X-CSRF-Token` | 403 `CSRF_INVALID`, no state change |
| mutation with wrong CSRF token | 403 `CSRF_INVALID` |
| request from non-allowlisted Origin | 403 `ORIGIN_NOT_ALLOWED` |
| CORS preflight with credentials | only allowlisted origins echo `Access-Control-Allow-Origin` |
| step-up with stale `auth_time` | 401 `STEP_UP_REQUIRED` |
| step-up with fresh auth | 200, action retried |
| step-up does not extend refresh cap | refresh still expires at 12 h from login |
| owner invitation accept | 200, user + membership active, token consumed |
| owner invitation reused | 404 |
| owner invitation expired | 404 |
| admin invitation accept | 200, admin active, token consumed |
| password reset token reused | 404 |
| invite accept with weak password | 422, token not consumed |

### 4.2 Tenants

| Case | Expected |
|------|----------|
| create with unique slug/email | 201, tenant + trial subscription + invitation |
| duplicate slug | 409 `SLUG_TAKEN` |
| duplicate owner email | 409 `OWNER_EMAIL_EXISTS` |
| suspend with reason + confirm | 200, status SUSPENDED, audit row |
| suspend twice | 409 |
| reactivate | 200, status ACTIVE |
| force logout | memberships bumped; old staff token 401 |
| create without reason | 422 |
| create with wrong confirm | 422 |
| cross-tenant detail by guessed ID | 404 |
| suspended tenant new order | 403 `TENANT_SUSPENDED` |
| suspended tenant complete existing bill | 200 (D-6) |
| suspended tenant start new dining session | 403 |
| suspended tenant read report | 200 (D-6) |
| export tenant A | artefact contains only A; manifest counts match |
| export includes tenant B row | test fails (isolation) |
| hard delete in PA-1 | 404/405 (route absent) |

### 4.3 Plans and subscriptions

| Case | Expected |
|------|----------|
| create plan | 201 |
| duplicate code | 409 |
| edit price with live subs | 200; existing snapshot unchanged |
| archive plan with live subs | 409 `PLAN_IN_USE` |
| assign plan to tenant with live sub | 409 `LIVE_SUBSCRIPTION_EXISTS` |
| extend trial +7 | trial_ends_at +7, event |
| extend trial > 30 in one call | 422 |
| cancel at period end | flag set, status unchanged |
| reactivate cancelled | new period, event |
| change to archived plan | 409 `PLAN_ARCHIVED` |

### 4.4 Billing

Core payment tests must pass with **no evidence store configured**. Evidence upload/URL cases are conditional on PA-1.3.4b being enabled (P-9 complete); skip them explicitly rather than failing the phase when storage is not ready.

| Case | Expected |
|------|----------|
| create invoice with lines | totals computed server-side; `INV-{FY}-{seq}` allocated |
| two invoices in the same FY | consecutive sequence numbers |
| new fiscal year | sequence restarts at 1 for the new FY |
| client sends `total_minor` | 422 (must not be accepted) |
| void OPEN invoice | 200, status VOID, number preserved, audit |
| void PAID invoice | 409 |
| pay OPEN invoice with reference, no evidence | 200; invoice PAID; subscription extended; payment row; event; audit |
| pay OPEN invoice with optional evidence object key | 200; only key stored; no public URL in response |
| pay without any reference (non-cash) | 422 `PAYMENT_REFERENCE_REQUIRED` |
| pay cash without reference but with exception reason | 200, flagged |
| evidence upload with disallowed type | 422 `EVIDENCE_TYPE_INVALID` |
| evidence upload above size limit | 413 `EVIDENCE_TOO_LARGE` |
| request signed evidence URL as support role | 403 |
| request signed evidence URL as billing/superadmin | 200, short expiry; access audited |
| pay twice | second returns 409 or original idempotent result |
| same idempotency key | same payment id, no duplicate event |
| different key, same normalized reference | 409 `PAYMENT_REFERENCE_EXISTS` |
| reference differing only by case/whitespace | 409 (normalized) |
| edit confirmed payment amount | 404/405 (route absent) |
| void confirmed payment | 200, event appended, invoice recalculated |
| refund ≤ paid, with original reference + destination | 201 `REFUND_PENDING`, original unchanged |
| refund without destination | 422 `REFUND_DESTINATION_REQUIRED` |
| refund > paid | 409 `REFUND_EXCEEDS_PAID` |
| requester approves own refund (policy deferred) | 200 `REFUND_APPROVED`, flagged `single_admin_approval` |
| complete without approval | 409 `REFUND_NOT_APPROVED` |
| complete with external reference | 200 `REFUNDED`, completer recorded, events appended |
| complete without external reference | 422 `EXTERNAL_REFUND_REFERENCE_REQUIRED` |
| refund rejected | original stays CONFIRMED, event appended |
| edit/delete payment event | 404/405 |
| pay void invoice | 409 |
| invoice for tenant A paid via tenant B path | 404 |
| restaurant QR callback attempts to mark platform invoice paid | 404/409; no platform payment row |
| platform payment record exposed through a restaurant bill route | 404 |

### 4.5 Platform users

| Case | Expected |
|------|----------|
| invite support | 201, one-time token |
| change role to billing | 200, audit |
| disable last superadmin | 409 `LAST_SUPERADMIN` |
| demote last superadmin | 409 |
| reset MFA | 200, token version bumped, next login requires enrollment |
| duplicate email | 409 |

### 4.6 Audit

| Case | Expected |
|------|----------|
| every mutation writes exactly one row | count + fields |
| rejected mutation writes no row | count unchanged |
| reason missing | 422, no row |
| before/after snapshots | redacted, no secrets |
| update/delete audit route | 405 |
| export | streamed, `AUDIT_EXPORTED` row |
| tenant filter | only that tenant’s rows |
| actor filter / date filter | correct |

## 5. Cross-tenant isolation tests

Use the existing two-tenant fixture pattern.

1. Platform admin lists tenants → sees both, but tenant detail of an inaccessible ID returns 404.
2. Invoice/payment/subscription IDs from tenant A cannot be mutated via tenant B’s path.
3. Diagnostics for tenant A never returns tenant B counts.
4. Audit filter by tenant A never returns tenant B rows.
5. Export for tenant A never includes tenant B rows.
6. A staff token from tenant A cannot call any platform route.
7. A platform token cannot call staff routes, even with a valid `restaurant_id`.
8. Force logout for tenant A does not revoke tenant B sessions.
9. Suspend tenant A does not change tenant B status.

## 6. Security tests (must be automated)

- **No token in JS or responses:** login/refresh/MFA bodies contain no `access_token`/`refresh_token`; the admin bundle contains no `localStorage`/`sessionStorage` credential writes.
- **Cookie hygiene:** access/refresh are `HttpOnly; Secure; SameSite=Strict` with the documented paths; no `Domain` attribute; production rejects `Secure=false`.
- **CSRF:** every non-GET platform route except `/auth/refresh` rejects a missing/mismatched `X-CSRF-Token`; a valid token from another session is rejected. `/auth/refresh` still enforces `SameSite=Strict` + Origin.
- **Origin/CORS:** non-allowlisted origins cannot preflight with credentials; wildcard with credentials is never emitted.
- **Secret leakage:** login/refresh/audit responses contain no `password_hash`, `mfa_secret`, `refresh_token`, `csrf_token`, or raw invitation token after creation.
- **Log redaction:** a request with password/token/cookie fields produces no secret in captured logs.
- **Realm confusion:** every platform route rejects a staff token; every staff route rejects a platform token.
- **MFA bypass:** cannot obtain cookies without `mfa_verified`; tickets are single-use and expire; recovery codes are single-use.
- **Recovery exhaustion:** using all recovery codes returns `MFA_RECOVERY_EXHAUSTED` and requires a superadmin reset.
- **Step-up bypass:** destructive routes reject a token with stale `auth_time`; step-up does not extend the 12-hour session cap.
- **Refresh theft:** replaying a rotated refresh token revokes the family and writes `REFRESH_REUSE_DETECTED`; the attacker and victim both lose the session.
- **Reason bypass:** all mutations reject missing/short reason; no endpoint defaults a reason.
- **Last superadmin:** disable/demote/delete returns 409; the two-superadmin launch gate is asserted.
- **Audit immutability:** no update/delete; DB grant check documented in the runbook.
- **Payment integrity:** no route edits a confirmed amount; duplicate reference rejected; transaction reference required (or audited cash exception); evidence optional and private with signed-URL access; refund records requester/approver/completer and external reference; payment events append-only.
- **Idempotency:** payment replay cannot double-charge or double-extend.
- **Rate limit:** 6th login attempt in a minute returns 429.
- **Error hygiene:** auth failures do not reveal whether the email exists.
- **SQL injection:** search/filter parameters are parameterized (SQLAlchemy text with bind params).
- **XSS:** no `dangerouslySetInnerHTML` in admin pages; invitation tokens and evidence refs rendered as text/links, not HTML.
- **Open redirect:** no `return_to` parameter accepted without an allowlist.
- **Export isolation:** export for tenant A contains no tenant B rows; manifest row counts match.
- **Background job context (PA-2):** a job with a missing/mismatched tenant context fails loudly.

## 7. Manual browser acceptance script

Run against a seeded dev database with at least two tenants, one suspended tenant, one trial, one paid invoice, one overdue invoice, and two active superadmins (dev fixtures; production uses real people).

1. Open the admin origin while logged out → redirected to `/login`.
2. Check DevTools → Application: no `localStorage`/`sessionStorage` credentials. Cookies show `HttpOnly` on access/refresh and a readable CSRF cookie.
3. Log in with wrong password 5× → lockout message.
4. Log in with correct password → MFA screen; wrong code → error; correct code → dashboard.
5. Inspect the login/refresh responses: no `access_token`/`refresh_token` in the body.
6. Open each nav item allowed for the role; confirm others are hidden.
7. Create a tenant; copy the invitation link; verify it is not shown again after reload.
8. Open the invitation link in a private window; set a password; sign in as the owner; verify the tenant dashboard loads.
9. Suspend the tenant with reason + typed slug; verify status badge and audit row.
10. As the tenant owner (separate browser), verify a new order is blocked, an existing bill can complete, and reports still load.
11. Reactivate; verify the owner can create a new order.
12. Force logout; verify the owner’s existing session is rejected.
13. Create a plan; edit price; verify warning about existing subscriptions.
14. Assign plan / extend trial / cancel at period end / reactivate; verify event timeline.
15. Extend a trial beyond the configured total → superadmin override path; verify reason + audit.
16. Create an invoice; verify the number matches `INV-{FY}-{seq}` and the next invoice increments.
17. Pay it with a transaction reference (no evidence); verify invoice PAID, payment row, event timeline, subscription period extended, dashboard collections increased. Repeat on another invoice with an optional evidence upload and verify the signed-URL view.
18. Try to pay another invoice with the same reference (case/whitespace variation); verify `PAYMENT_REFERENCE_EXISTS`.
19. Replay the same payment request; verify no duplicate.
20. Confirm there is no edit control/route for the confirmed amount.
21. Request a refund as `billing` with amount, reason, original reference, and destination; verify it lands in the refund queue with no threshold warning.
22. Approve it as the same admin; verify it is permitted and labeled `single_admin_approval`.
23. Complete it with an external refund reference; verify `REFUNDED`, completer recorded, and the original payment unchanged. Repeat a separate refund executed outside the platform and verify `processed_outside_platform`.
24. Reject a separate refund request; verify the original stays `CONFIRMED`.
25. Void an unpaid invoice; verify the reason is required and the number is not reused.
26. Invite a support admin; log in as support; verify write buttons are hidden and direct API calls return 403.
27. Try to disable the last superadmin; verify 409 and a clear UI explanation. With two real superadmins, verify the second can be disabled.
28. Open audit; filter by tenant/action; export; verify the export row.
29. Open settings; change a value with reason + step-up; verify audit. Verify there is no refund-threshold field.
30. Open diagnostics; verify checks and no tenant PII beyond contact.
31. Wait for step-up to expire; attempt suspend; verify the step-up dialog and retry.
32. Remove the CSRF header in a dev console request; verify `403 CSRF_INVALID`.
33. Send a state-changing request with a foreign `Origin`; verify rejection.
34. Sign out everywhere from Profile; verify other tabs are logged out.
35. Check browser console: zero errors on every route.
36. Check network: no token in URLs; no secrets in responses or logs.
37. Resize to 375 px: dialogs usable, tables scroll, nav collapsible.
38. Restore a backup into a scratch DB and verify row counts/checksums (runbook procedure).

## 8. Acceptance checklist (phase gate)

Copy this into the phase note and check each item.

### Security

- [ ] Staff token rejected on every platform route.
- [ ] Platform token rejected on every staff route.
- [ ] MFA required for all platform admins; recovery codes single-use.
- [ ] Access/refresh cookies are `HttpOnly; Secure; SameSite=Strict`, host-only.
- [ ] CSRF enforced on every non-GET platform route.
- [ ] Origin/CORS allowlist enforced; no wildcard with credentials.
- [ ] No credential in JS storage or response bodies.
- [ ] Refresh rotation + reuse detection + sign-out-everywhere work.
- [ ] Step-up enforced on all destructive routes; does not extend the session cap.
- [ ] Reason enforced on all mutations.
- [ ] Last-superadmin invariant holds; two **real** active superadmins exist; recovery owner and credential location documented.
- [ ] Audit rows append-only and complete.
- [ ] Payment reference uniqueness, optional private evidence with signed URLs, maker–checker, refund participant/reference fields, immutable events.
- [ ] SaaS subscription payments cannot be created or viewed through restaurant QR payment routes (and vice versa).
- [ ] No secrets in responses, logs, or audit snapshots.
- [ ] Rate limiting works.
- [ ] Production startup rejects missing/matching secrets, missing origins, non-host-only cookies, `Secure=false`.

### Functional

- [ ] Dashboard metrics match fixtures.
- [ ] Tenant create/suspend/reactivate/force-logout.
- [ ] Suspension D-6 behavior (new orders blocked, in-flight bill allowed).
- [ ] Plan create/edit/archive rules.
- [ ] Subscription lifecycle rules; configurable trial limits.
- [ ] Invoice numbering per fiscal year.
- [ ] Invoice create/void/pay/refund.
- [ ] Payment idempotency, duplicate-reference rejection, optional evidence, signed-URL access, void.
- [ ] Refund request/approve/complete/reject with participants and external reference; no fixed threshold.
- [ ] Invoice issuer/PAN/VAT snapshot fields and `UNCONFIRMED` tax treatment warning.
- [ ] Payment instructions are read-only and cannot mark an invoice paid.
- [ ] Platform user roles and invariants.
- [ ] Settings allowlist.
- [ ] Diagnostics read-only.
- [ ] Audit filters/export.
- [ ] Export scope/retention defined and isolated.

### Quality

- [ ] Backend suite green.
- [ ] Structure tests green (no baseline growth except ADR-009).
- [ ] Tenant frontend build green.
- [ ] Admin frontend build green (`build:admin`).
- [ ] No console errors in the smoke script.
- [ ] Every page has loading/empty/error/forbidden states.
- [ ] Money formatted with currency.
- [ ] Accessibility basics pass.
- [ ] Runbook updated; restore drill recorded.
- [ ] OpenAPI updated.
- [ ] Plan files updated for any deviation.

## 9. CI gates

Add to the pipeline (or document the manual equivalent if CI is not yet wired):

```bash
# backend
cd backend
./venv/Scripts/python.exe -m pytest -q --no-header
./venv/Scripts/python.exe -m pytest tests/structure -q

# frontend
cd apps/web
npm run build
npm run build:admin
```

Phase-gate extras:

- `ruff check` on changed files,
- migration up/down on a scratch database,
- cookie/CSRF/origin verification in a staging environment,
- two real active superadmins + recovery drill evidence,
- domain/DNS/TLS owner confirmed (PA-ADR-011) and evidence store live,
- Nepali tax-professional invoice sign-off recorded,
- category-specific retention policy approved,
- backup restore drill evidence,
- manual smoke script evidence attached,
- no new cross-module imports (structure test),
- no naive `datetime.now()`.

## 10. Performance smoke (PA-1.4)

Seed 10,000 tenants, 10,000 subscriptions, 50,000 invoices. Verify:

- `GET /tenants?page=1` < 300 ms p95 on local Postgres,
- `GET /dashboard` < 800 ms p95,
- `GET /invoices?page=1` < 300 ms p95,
- no N+1 queries (inspect SQL count; target ≤ 5 queries per list request),
- indexes used for status/created filters.

If the dashboard exceeds the target, add a materialized daily rollup in PA-2; do not denormalize ad hoc.

## 11. Test data hygiene

- Never run the acceptance script against production.
- The test suite wipes the database; do not point it at a shared environment.
- Demo platform credentials must be printed only in dev.
- Screenshots/logs used as evidence must not contain real owner emails, tokens, or bank references.
