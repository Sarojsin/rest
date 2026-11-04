# 11 — Operations Runbook

**Audience:** platform ops and on-call engineers.
**Rule:** every recovery and every destructive action is audited. No silent fixes.

---

## 1. Bootstrap the first superadmin

### Normal first deploy

Set on the API service:

```
PLATFORM_BOOTSTRAP_EMAIL=owner@platform.example
PLATFORM_BOOTSTRAP_PASSWORD=<strong, unique>
PLATFORM_SECRET_KEY=<random 64+ chars, different from SECRET_KEY>
PLATFORM_MFA_KEY=<random 64+ chars, separate from the JWT secret>
PLATFORM_REQUIRE_MFA=true
PLATFORM_ADMIN_ORIGIN=https://admin.platform.example
PLATFORM_API_ORIGIN=https://api.platform.example
PLATFORM_TENANT_ORIGIN=https://www.platform.example
PLATFORM_COOKIE_SECURE=true
PLATFORM_COOKIE_DOMAIN=            # must stay empty (host-only)
```

`platform.example` is a placeholder. Replace it with the real domain from **PA-ADR-011**, and keep registrar/DNS/TLS credentials in the company password manager — never in this repository or a committed `.env` file. If the domain or owner is not confirmed, do not run production bootstrap.

Startup behavior:

1. Verify Alembic is at head.
2. Refuse to boot if the platform secret is missing/matches `SECRET_KEY`, the MFA key is missing, an origin is missing, `PLATFORM_COOKIE_DOMAIN` is set, or `PLATFORM_COOKIE_SECURE=false` in production.
3. If no `platform_admins` row exists, create the superadmin with `status=ACTIVE`, `mfa_enabled_at=null`.
4. Audit `PLATFORM_BOOTSTRAP_ADMIN_CREATED`.
5. The admin logs in at the **admin origin**, is forced to enroll TOTP, then gets access.
6. Invite the **real secondary Super Admin** immediately; commercial launch requires two active superadmins who are named people. Record the **emergency recovery owner** and the location of recovery/break-glass credentials before launch. Do not seed a placeholder second admin.

If the table is empty and the env vars are missing, startup **fails**. Do not create a default password.

### Re-assert after accidental disable

Startup re-asserts the bootstrap admin only when:

- the email matches `PLATFORM_BOOTSTRAP_EMAIL`, and
- the account is missing **or** disabled.

It re-enables the account, bumps `token_version`, and audits loudly. It never resets the password or MFA.

## 2. MFA enrollment and recovery

### First enrollment

1. Log in with password at the admin origin.
2. Scan the QR or copy the secret into an authenticator.
3. Verify a code.
4. Store the 10 recovery codes offline (password manager / sealed envelope). They are shown once.
5. Log in again to confirm.
6. The real secondary Super Admin must complete enrollment before launch. Both admins' recovery codes and the break-glass credentials are stored in the company-controlled password manager (or sealed offline backup), with the storage location and emergency recovery owner documented. Access to that storage is limited and audited.

### Lost authenticator (self-service)

1. Log in with password.
2. On the MFA screen, choose “recover”.
3. Enter a recovery code (single use).
4. Re-enroll a new authenticator; all old recovery codes are invalidated and new ones are issued.
5. Audit `PLATFORM_RECOVERY_CODE_USED`.

### Lost authenticator + lost recovery codes

A superadmin must:

1. Open **Platform users → [user] → Reset MFA**.
2. Enter a reason and typed confirmation; complete step-up.
3. The system clears MFA, increments `token_version`, revokes refresh tokens, audits `PLATFORM_MFA_RESET`.
4. The user logs in and re-enrolls.

If the affected user is the **only** superadmin, follow §3.

### Recovery drill (quarterly)

1. Pick a non-production test admin.
2. Use one recovery code, verify re-enrolment works.
3. Reset MFA through the superadmin flow.
4. Record the date and result; a failed drill is a launch blocker.

## 3. Break-glass recovery (locked out of the platform)

This is a two-person procedure. Never perform it alone.

### Preconditions

- At least two platform staff are available.
- The incident is recorded (ticket/incident ID).
- The person performing the DB action is not the person who will use the recovered account.

### Path A — Bootstrap re-assert (preferred)

1. Ensure `PLATFORM_BOOTSTRAP_EMAIL` points to the recovery account.
2. Set a temporary strong `PLATFORM_BOOTSTRAP_PASSWORD` in the secret store.
3. Restart the API service.
4. Startup re-enables/creates the bootstrap admin and audits it.
5. Recover access, enroll MFA, then rotate the bootstrap password.
6. Restore the original bootstrap email if needed.
7. Break-glass re-assert bumps `token_version`, so any old sessions are invalidated; the operator must log in fresh at the admin origin.

### Path B — Direct database recovery (only if Path A is unavailable)

1. Open a managed-Postgres session through the ops secret store.
2. `UPDATE platform_admins SET status='ACTIVE', locked_until=NULL WHERE email='<recovery>';`
3. Do **not** read or change password/MFA hashes.
4. Immediately write a manual audit row via the app’s audit service or a reviewed SQL insert:
   - action `PLATFORM_BREAK_GLASS`,
   - both signatories in the reason,
   - incident ID,
   - before/after status.
5. Notify all other platform admins.
6. Rotate the DB credential after the incident.

### Path C — Redeploy with fresh bootstrap env

Use only when the running system cannot be reached. Same two-person rule and post-act audit.

### Seat policy

- Keep **at least two active superadmins** while any real tenant exists.
- The UI refuses to disable/demote the last one (`LAST_SUPERADMIN`).
- A daily ops check reports the superadmin count; if it is 1, treat it as an incident.

## 4. Suspend a tenant

Use when there is a valid policy or security reason (non-payment, abuse, legal hold).

1. Open **Tenants → [tenant] → Suspend**.
2. Review the impact summary: active branches, staff, in-flight sessions (if available).
3. Enter a reason ≥10 characters and type the tenant slug.
4. Complete step-up if prompted.
5. Confirm.

Effects:

- `restaurants.status = SUSPENDED`, `suspended_at`, `suspended_reason`.
- New dining sessions, new orders, and QR session starts are blocked.
- In-flight orders created before suspension can be completed/cancelled; bills can be generated and settled (D-6).
- Staff already signed in can read reports; new exports and new writes are blocked.
- Staff sessions are not force-logged-out automatically; use force-logout if the reason is security.
- Audit `TENANT_SUSPENDED`; owner notification is manual in MVP (PL-003).

## 5. Reactivate a tenant

1. Confirm the reason for suspension is resolved.
2. **Tenants → [tenant] → Reactivate**.
3. Reason + typed slug + step-up.
4. Confirm the tenant can create a new order.
5. Audit `TENANT_REACTIVATED`.

If the subscription is still `SUSPENDED`/`EXPIRED`, reactivating the tenant does not silently grant a paid plan. Assign/extend the subscription explicitly.

## 6. Force logout a tenant

Use for credential leaks, compromised staff accounts, or a security suspension.

1. **Tenants → [tenant] → Force logout**.
2. Reason + typed slug + step-up.
3. Confirm the revoked membership count.
4. Verify an old staff token now returns `401 SESSION_REVOKED`.
5. Audit `TENANT_FORCE_LOGOUT`.

This affects staff sessions only, not platform admins.

## 7. Invoices, payments, and refunds

### Create

1. **Invoices → New**.
2. Pick the tenant and optional subscription.
3. Add lines (`PLAN`, `OVERAGE`, `DISCOUNT`, `ADJUSTMENT`); the server computes totals.
4. Set due date, notes, reason.
5. Save; status is `OPEN`. The number is assigned as `INV-{FY}-{000001}` by the server.

Numbering rules:
- sequence is per fiscal year, unique, allocated under a row lock;
- `VOID` invoices keep their number and it is never reused;
- do not hand-write, copy, or renumber invoices outside the app.

### Void

Only `DRAFT`/`OPEN` invoices can be voided. Reason + invoice number confirmation. Audit `INVOICE_VOIDED`. Keep the number.

### Confirm a payment

1. **Invoice → Pay**.
2. Match the money movement to the bank/eSewa/Khalti statement first.
3. Enter method, amount, **transaction reference**, provider reference, paid date, optional evidence, and reason.
4. The reference is normalized and must be unique; a duplicate is rejected.
5. Cash without a verifiable reference requires an exception reason and is flagged.
6. Complete step-up if prompted. Reuse the same `Idempotency-Key` on retry.
7. Audit `PAYMENT_CONFIRMED`; a `payment_confirmed` event is appended.

Maker–checker: when more than one admin exists, the verifier must not be the invoice creator. If the platform has only one admin, the confirmation is allowed but flagged.

### Correct a confirmed payment

Do **not** edit the amount, date, method, or reference. There is no endpoint for that.

- Wrong invoice / duplicate: **Void payment** (superadmin, reason, step-up), then record the correct payment. Audit `PAYMENT_VOIDED` + `payment_voided`.
- Money returned to the tenant: request a **refund**.

### Refunds

PA-1 does **not** process refunds automatically and does not call a payment provider. Refund execution is manual and may happen outside the product; the platform records the decision and the external transaction.

1. **Payment → Request refund** (`billing` or `superadmin`).
2. Enter amount (≤ confirmed minus prior refunds), reason code, note, **original payment reference**, **destination**, optional evidence, and whether execution will happen outside the platform.
3. The requester is recorded. There is **no fixed monetary dual-approval threshold** in PA-1; the policy is deferred until finance defines it.
4. **Approve** (`payment.refund.approve`, step-up) records the approver. Self-approval is allowed while the policy is deferred but is labeled `single_admin_approval`.
5. Execute the refund outside the product (bank/eSewa/Khalti) or follow the company's manual process.
6. **Complete** (`payment.refund.complete`, step-up) records the completer, the **external refund transaction reference**, completion time, destination, and `processed_outside_platform`.
7. Every step appends a `platform_payment_events` row. If the subscription should change, do it separately with a reason.
8. Reconcile refunds monthly: every `REFUNDED` row must match an external refund transaction. Investigate any mismatch.

### Payment evidence (optional)

Evidence upload is available only after the private bucket/access policy is configured. Reference-only payment recording works before that.

1. Evidence is optional. A transaction reference plus the verifier record is sufficient.
2. When evidence is supplied, upload it through the payment dialog. The server validates content type and size, ignores the original filename, and stores the object in the private bucket.
3. View evidence only through the short-lived signed URL from the payment detail. Do not copy the URL into tickets, chat, or logs.
4. Never download evidence to a shared drive or attach it to an email. If a bank/auditor needs it, use the approved secure channel and record the disclosure.
5. Never confirm a payment from a screenshot alone; match the statement. Never mark an invoice paid because a file was uploaded.

### Payment reference rules

- One reference per payment, unique across the platform (normalized: trimmed, uppercased).
- Match the money movement to the bank/eSewa/Khalti statement before confirming.
- Reconcile monthly: compare statements against `platform_payments` and investigate unmatched rows.
- Never confirm a payment with “no reference, no evidence” except the audited cash exception.
- SaaS subscription payments and restaurant customer QR payments are reconciled separately; never merge their statements or evidence.

## 8. Plan changes

- Price changes affect **new** subscriptions only. Existing subscriptions keep `price_snapshot_minor` until renewal.
- Do not edit `code`; create a new plan if the product identity changes.
- Archiving is blocked while live subscriptions exist. Migrate tenants first.
- Every change requires a reason; audit records before/after.

## 9. Platform admin lifecycle

### Invite

1. **Platform users → Invite**.
2. Email, name, role, reason.
3. Copy the one-time link and send it through an approved channel.
4. The link expires in 72 hours. The invitee opens `https://admin.{platform_domain}/invite/{token}`, sets a password, enrolls MFA, and signs in.

### Change role

Reason + step-up. Review the permission matrix before granting `superadmin`.

### Disable / offboard

1. Disable the account (reason + confirmation).
2. Confirm `token_version` bumped and refresh tokens revoked.
3. Reassign any operational ownership.
4. Keep the row for audit; do not hard-delete.
5. If the person was a superadmin, verify at least two active superadmins remain.

## 10. Settings changes

- Only allowlisted keys accepted.
- Every change requires a reason + step-up and is audited.
- `platform.invoice_prefix` changes do not renumber existing invoices.
- `platform.fiscal_year_start_month` changes apply to **new** invoices only; existing numbers keep their FY.
- `platform.default_trial_days` affects new subscriptions only.
- `platform.trial_extension_max_days_*`, invoice issuer/tax fields, and evidence limits apply to new actions only; record the reason.
- There is no refund-threshold setting in PA-1; the second-approval policy is deferred until finance defines it.
- Changing invoice issuer/PAN/VAT fields does not rewrite existing invoices (they keep their snapshot) and does not by itself make the template legally compliant.
- `platform.export_retention_days` changes do not extend already-created exports.
- Do not set `platform.default_currency` to anything other than NPR in MVP.

## 11. Monitoring and health

MVP exposes:

- `GET /health` (process),
- `GET /ready` (readiness),
- `GET /api/platform/diagnostics/health` (DB + migration head).

Alert on:

- 5xx rate > 1% for 5 minutes,
- login failure spike,
- audit insert failures (should block the action),
- database connection saturation,
- migration head mismatch at startup.

No fake Redis/worker alerts; those components do not exist in MVP.

### Session and cookie troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Login succeeds but every call is 401 | `Set-Cookie` has the right `Path` and host-only scope; request is `credentials: include` | Correct the API origin/cookie path config; do not add a `Domain` attribute |
| `403 CSRF_INVALID` on a valid UI action | `platform_csrf` cookie present; `X-CSRF-Token` header matches; `Origin` matches `PLATFORM_ADMIN_ORIGIN` | Clear cookies, log in again; fix the origin/proxy config |
| CORS preflight fails | `Access-Control-Allow-Origin` echoes the admin origin and `Allow-Credentials: true` | Fix the allowlist; never use `*` with credentials |
| Admin loop-redirects to login | `/auth/refresh` returns 401 `REFRESH_INVALID` (expired/reused/revoked) | Expected after 12 h or revocation; log in again |
| Refresh reuse alert | A rotated token was replayed | Family is already revoked; investigate the client or token theft, rotate secrets if needed |
| Step-up modal appears constantly | `auth_time` older than `platform_step_up_minutes` | Expected; complete step-up; do not extend the window for convenience |

## 12. Backup and restore

- Postgres daily full backup + point-in-time recovery in production.
- Before a platform migration, take an on-demand backup.
- **Monthly restore test** into a scratch database: restore, run row-count and checksum queries, confirm Alembic head, record the result. A failed restore is a launch blocker.
- Platform audit logs and payment evidence references are included; payment evidence files have their own backup policy in the private evidence store.
- Retention is category-specific (see `04-data-model.md` §4.4 and `09-risks-and-decisions.md` §2.4). Do not apply one blanket period. Backup expiry must be documented so deleted data does not silently resurrect.
- Never restore a backup into production without replaying the audit of the restore action.

### Restore verification queries

```sql
SELECT count(*) FROM platform_admins;
SELECT count(*) FROM platform_invoices;
SELECT count(*) FROM platform_payments;
SELECT count(*) FROM platform_payment_events;
SELECT max(created_at) FROM platform_audit_logs;
```

Compare against the pre-restore snapshot; investigate any mismatch before declaring success.

## 13. Secret rotation

| Secret | Cadence | Procedure |
|--------|---------|-----------|
| `PLATFORM_SECRET_KEY` | 90 days or on incident | Rotate, deploy, all platform sessions invalidated; staff sessions unaffected |
| `PLATFORM_MFA_KEY` | 180 days or on incident | Re-encrypt MFA secrets in a maintenance window; users keep authenticators |
| Bootstrap password | after every use | Rotate immediately; audit the re-assert |
| DB credential | 90 days or on incident | Rotate via secret store; restart API |
| Refresh tokens | continuous | Rotate on use; revoke family on reuse |

After rotating the platform secret, announce a forced re-login. Do not rotate it during an active incident unless the incident is a credential compromise.

## 14. Audit and data export

- **Audit → Export**, range ≤31 days in MVP.
- Export is itself audited (`AUDIT_EXPORTED`).
- Store exports in the approved secure location; they contain actor emails and reasons.
- Do not paste exports into public tickets.
- Tenant data exports (PA-2) use the approved scope in `09-risks-and-decisions.md` D-10, are audited (`TENANT_EXPORTED`), and expire after `platform.export_retention_days`.
- Verify the manifest tenant id and row counts before handing an export to anyone.
- Never export “everything” and filter in a spreadsheet; the server must filter by `restaurant_id`.

## 15. Incident checklist (platform admin realm)

1. Declare severity and incident ID.
2. Preserve audit logs and relevant request IDs.
3. If credential compromise is suspected: disable the admin, bump token version, rotate secrets, force logout affected tenants.
4. If tenant data exposure is suspected: contain, assess scope, notify per policy, write a post-incident ADR.
5. If billing is wrong: stop payments, reconcile against bank statements, issue refunds/corrections, audit every change.
6. Write a post-incident report within 5 business days.
7. Add a regression test for the failure mode.

## 16. What not to do

- Do not create a second “temporary” superadmin and leave it active; the second admin must be a real named person.
- Do not invent a production domain, DNS owner, or TLS owner; record it in PA-ADR-011 first.
- Do not edit `platform_audit_logs` or `platform_payment_events`.
- Do not delete a tenant row to “clean up”; archive it.
- Do not share admin accounts.
- Do not confirm a payment without a matching transaction reference (unless the audited cash exception applies).
- Do not mark an invoice paid because evidence was uploaded; an authorised person must verify receipt.
- Do not mix SaaS subscription payments/evidence with restaurant QR payments/evidence.
- Do not edit a confirmed payment amount; void and re-record, or refund.
- Do not approve your own refund.
- Do not disable MFA “just for testing” in production.
- Do not put platform cookies on a shared parent domain.
- Do not serve the admin bundle from the tenant origin.
- Do not run the test suite against a shared database; it wipes data.
