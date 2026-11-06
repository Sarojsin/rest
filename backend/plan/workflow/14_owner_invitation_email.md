# 14 — Owner Invitation Email Delivery

**File:** `backend/plan/workflow/14_owner_invitation_email.md`
**Area:** Email delivery for owner and staff invitations
**Status:** Proposed

---

## 1. Overview

When an admin creates a restaurant and invites the owner, the backend must
deliver the invitation via email — not return a raw token to the admin or set a
password on the owner's behalf. The flow:

1. Admin enters owner's email during onboarding.
2. Backend generates a cryptographically secure, single-use invitation token.
3. System emails the owner an invitation link containing the token.
4. Owner opens the link, verifies email, creates a password.
5. Backend hashes and stores the password; account becomes ACTIVE.
6. Owner may enable MFA if required by policy.

Administrators never know or share customer passwords.

---

## 2. Current State

- `platform_directory.create_tenant()` creates an owner user with
  `status='INVITED'` and a random unusable password hash.
- `platform_one_time_token` (purpose: OWNER_INVITE) is created with the token
  hash; raw token is returned by `POST /api/platform/tenants` (for testing).
- `POST /api/platform/auth/invitations/{token}/accept` activates the owner and
  sets their password (PA-0.0 / PA-07 extended for STAFF_INVITE).
- **No email sending is wired.** The raw token is returned in the API response
  (acceptable for dev/manual delivery, not production).

---

## 3. Desired State

### 3.1 Email sending abstraction

Add a thin email service interface with two implementations:

| Implementation | Use | Notes |
|----------------|-----|-------|
| `SmtpEmailService` | Production | SMTP connection from settings |
| `LogEmailService` | Dev / tests | Writes invitation token to log (no real email) |

Settings:
- `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`
- `email_backend` (`smtp` | `log`)
- `invitation_base_url` (e.g., `https://www.{platform_domain}/accept-invitation`)

### 3.2 Invitation email content

**To:** owner@example.com
**Subject:** Set up your account for {restaurant_name}

```
Hello {owner_name},

{restaurant_name} has been registered on our restaurant management platform.

Your owner account is ready for setup:
- Restaurant: {restaurant_name}
- Account: {owner_email}
- Role: Owner

Click the secure link below to verify your email and create your password:
{invitation_base_url}?token={raw_token}

This link expires after {TTL} hours and can be used only once.

If you did not sign up for this, you can ignore this email.
```

### 3.3 API changes

**`POST /api/platform/onboarding/restaurants`** (plan 08):
- After creating the tenant + owner invite, send the email asynchronously
  (fire-and-forget or background task).
- The response **must not** include the raw token in production. Include only
  `invitation_sent: true` and `invitation_expires_at`.
- In dev (email_backend=log), the token may be logged for manual testing.

**`POST /api/v1/restaurant_memberships/invite`** (plan 09):
- Same email flow for staff invitations (STAFF_INVITE token).

### 3.4 Acceptance flow (already implemented)

`POST /api/platform/auth/invitations/{token}/accept`:
- Consumes the STAFF_INVITE or OWNER_INVITE token.
- Validates password policy.
- Sets password_hash, status=ACTIVE.
- Bumps token_version (force-logout any old sessions).
- Audit event `OWNER_INVITE_ACCEPTED` / `STAFF_INVITE_ACCEPTED`.

---

## 4. Acceptance Criteria

- [ ] Invitation email is sent when a tenant is onboarded (not raw token in response).
- [ ] Email contains a single-use token link with TTL.
- [ ] Admin never receives or sees the owner's password.
- [ ] Token acceptance activates the account and sets the password.
- [ ] Expired or used tokens cannot be accepted (404, no info leakage).
- [ ] Dev mode logs the token instead of sending real email.
- [ ] Both owner and staff invitations use the same email flow.

---

## 5. Related Files

- `backend/app/modules/platform/services/email.py` (new) — email service interface + implementations
- `backend/app/core/config.py` — SMTP + email_backend settings
- `backend/app/modules/platform/services/platform_directory.py` — create_tenant (call email after create)
- `backend/app/api/v1/router_memberships.py` — invite endpoint (call email after create)
- `backend/app/modules/platform/router_auth.py` — invitation accept (already implemented)
- `backend/app/modules/platform/services/bootstrap.py` — dev seed may use log backend
