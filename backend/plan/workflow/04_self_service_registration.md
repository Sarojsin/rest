# 04 — Self-Service Registration

**File:** `04_self_service_registration.md`
**Area:** Restaurant owner self-registration (Option C)
**Status:** Draft

---

## 1. Overview

Support both OPS-created restaurants AND restaurant owner self-registration. Self-service owners can register, select a plan, start a trial, and pay. OPS retains manual creation for direct sales.

---

## 2. Current State

- Tenant creation only via `/api/platform/tenants` (requires platform admin auth).
- No public restaurant registration endpoint.
- No self-service plan selection.
- No public invoice/payment flow for tenants.

---

## 3. Desired State

| Flow | Actor | Endpoint |
|------|-------|----------|
| Register restaurant | Restaurant owner | `POST /api/public/restaurants/register` |
| Select plan | Restaurant owner | `GET /api/public/plans` |
| Start trial/pay | Restaurant owner | `POST /api/public/restaurants/{id}/subscribe` |
| Accept owner invite | Invited owner | `POST /api/platform/auth/invitations/{token}/accept` (exists) |

---

## 4. Implementation Steps

### 4.1. Public plan listing
- `GET /api/public/plans` — Returns active, public plans with features/limits (no auth required).
- `GET /api/public/plans/{code}` — Returns single plan details.

### 4.2. Restaurant registration
- `POST /api/public/restaurants/register` — Creates restaurant + subscription + owner invitation.
- Body: `{ name, slug, owner_email, owner_name, plan_code, trial_days, ... }`
- Validates slug uniqueness, email uniqueness.
- Creates `restaurants` row (status: ACTIVE).
- Creates `platform_subscriptions` row (status: TRIALING if trial_days > 0, else ACTIVE).
- Creates `platform_one_time_token` (purpose: OWNER_INVITE) for owner.
- Sends invitation email (or returns token for manual delivery).

### 4.3. Self-service subscription
- `POST /api/public/restaurants/{id}/subscribe` — Owner converts trial to paid.
- Body: `{ plan_code, billing_interval, payment_method }`
- Generates invoice.
- Owner pays via manual reference.

---

## 5. Security Considerations

- **Rate limiting:** Limit registration attempts per IP/email to prevent spam.
- **Slug reservation:** Reserve `www`, `api`, `admin`, `staff`, `platform`, `public` subdomains.
- **Email verification:** Owner invitation token is single-use, time-limited (72 hours).
- **No sensitive data in public endpoints:** Never return platform admin data, payment references, or internal IDs.

---

## 6. Acceptance Criteria

- [ ] Restaurant owner can register without platform admin involvement.
- [ ] Self-registered restaurant gets a trial subscription.
- [ ] Owner receives invitation email with token.
- [ ] Owner can set password and access restaurant dashboard.
- [ ] Rate limiting prevents abuse.

---

## 7. Risks & Mitigations

- **Risk:** Spam registrations.
  - **Mitigation:** Rate limit, CAPTCHA (future), email verification required.
- **Risk:** Owner registers with existing email.
  - **Mitigation:** Check email uniqueness before creating; return clear error.

---

## 8. Related Files

- `backend/app/modules/tenancy/services/platform_directory.py` — Existing `create_tenant`
- `backend/app/modules/platform/router_auth.py` — Existing invitation endpoints
- `backend/app/api/platform/router_plans.py` — Existing plans router (public version needed)
