# Authentication Security Audit — Restaurant SaaS Platform

**Classification:** CONFIDENTIAL  
**Scope:** Platform realm, Staff realm, Customer QR surface  

---

## Executive Summary

The platform implements **three distinct authentication realms** with varying security postures. The **platform realm** demonstrates strong security architecture (HttpOnly cookies, rotating refresh tokens with reuse detection, TOTP MFA, step-up authentication). The **staff realm** has significant gaps (no refresh token rotation, bearer tokens in Authorization header, no MFA). The **customer QR surface** uses a token-based approach with inadequate binding.

**Overall Authentication Rating: MODERATE — Platform realm STRONG, Staff realm WEAK**

---

## 1. Platform Realm Authentication (Super Admin / OPS / Billing Support)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLATFORM REALM AUTH FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. POST /api/platform/auth/login                                │
│     ├── Email + Password                                        │
│     ├── Argon2id verification (timing-safe)                     │
│     ├── Account lockout check (BROKEN - CRIT-003)               │
│     └── Returns: LoginChallenge {enrollment_required, ticket}   │
│                                                                  │
│  2a. If MFA not enrolled:                                       │
│      POST /api/platform/auth/mfa/enroll/start                   │
│      ├── Validates enrollment ticket                            │
│      ├── Generates TOTP secret (base32, 20 bytes)               │
│      ├── Encrypts with Fernet (AES-128-CBC + HMAC-SHA256)       │
│      ├── Stores encrypted secret in DB                          │
│      └── Returns: secret + provisioning URI (otpauth://)        │
│                                                                  │
│  2b. If MFA enrolled:                                           │
│      POST /api/platform/auth/mfa/verify                         │
│      ├── Validates verification ticket                          │
│      ├── Verifies TOTP (RFC 6238, ±1 window)                    │
│      ├── Supports recovery codes (SHA-256 hashed, single-use)   │
│      └── On success: Creates session + sets HttpOnly cookies    │
│                                                                  │
│  3. Session Management:                                         │
│     ├── Access Token: 15 min, HS256, platform_signing_key       │
│     │   ├── Claims: sub, realm=platform, role, ver, jti,        │
│     │   │         auth_time, step_up_at, exp, iat               │
│     │   └── Delivered via: platform_access cookie (HttpOnly)    │
│     │                                                           │
│     ├── Refresh Token: 12 hrs absolute, rotating, family-based  │
│     │   ├── Stored: SHA-256 hash in platform_refresh_tokens     │
│     │   ├── Family ID tracks rotation chain                     │
│     │   ├── Reuse detection: burns entire family on replay      │
│     │   └── Delivered via: platform_refresh cookie (HttpOnly)   │
│     │                                                           │
│     ├── CSRF Token: 32 bytes, per-session                       │
│     └── Step-up: 5 min window for sensitive actions             │
│                                                                  │
│  4. Logout / Revocation:                                        │
│     ├── POST /api/platform/auth/logout → revokes family         │
│     ├── POST /api/platform/auth/sessions/{family_id}/revoke     │
│     └── POST /api/platform/auth/sessions/revoke-all             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Strengths

| Control | Implementation | Rating |
|---------|---------------|--------|
| Password Hashing | Argon2id (PasswordHasher default params) | ✅ STRONG |
| Timing Attack Mitigation | Dummy hash verification for unknown emails | ✅ GOOD |
| MFA | TOTP (RFC 6238) + Recovery Codes | ✅ STRONG |
| MFA Secret Storage | Fernet encryption at rest | ✅ STRONG |
| Refresh Token Rotation | Per-request rotation with family tracking | ✅ STRONG |
| Refresh Token Reuse Detection | Burns entire family on replay | ✅ STRONG |
| Token Version Invalidation | `token_version` bump on role change, password change, logout | ✅ STRONG |
| Step-up Authentication | Re-auth + MFA for sensitive ops | ✅ GOOD |
| Audit Logging | Comprehensive (login, MFA, refresh, logout, reuse) | ✅ GOOD |
| Cookie Security | HttpOnly, Secure (prod), SameSite=Lax | ✅ GOOD |
| Account Lockout | 5 attempts → 15 min lockout (design) | ⚠️ BROKEN (CRIT-003) |

### Vulnerabilities

#### AUTH-PLAT-001: Weak Default Signing Keys in Development
**Severity:** HIGH  
**Location:** `config.py:116-136`, `main.py:152-159`

```python
# config.py:116-136
@property
def platform_signing_key(self) -> str:
    if self.platform_secret_key:
        return self.platform_secret_key
    if self.is_production:
        raise RuntimeError("PLATFORM_SECRET_KEY is not configured")
    return sha256(f"platform-dev-signing::{self.secret_key}".encode()).hexdigest()
```

Development derives keys from `SECRET_KEY` using SHA-256. If `SECRET_KEY` is the default (`dev-only-change-me-not-for-production`), all development tokens are forgeable. The bootstrap process in `main.py` creates a platform admin with these weak keys.

**Impact:** Development tokens forgeable; if dev environment exposed, leads to admin compromise.

**Fix:** Generate unique per-installation dev keys; document clearly.

---

#### AUTH-PLAT-002: MFA Enrollment Secret Returned in Response
**Severity:** MEDIUM  
**Location:** `router_auth.py:73-84`

```python
@router.post("/mfa/enroll/start", response_model=MfaEnrollStartOut)
def start_mfa_enrollment(...):
    secret, uri = auth.start_enrollment(...)
    return MfaEnrollStartOut(
        secret=secret,  # RAW TOTP SECRET IN RESPONSE BODY
        provisioning_uri=uri,
        issuer=settings.platform_totp_issuer,
    )
```

The raw base32 TOTP secret is returned in the JSON response body. While this is necessary for QR code display, it creates risk if:
- Response logged by proxy/CDN
- Browser history/extensions capture it
- Developer tools expose it

**Fix:** Return only the provisioning URI; secret used client-side via QR scan only. Or implement WebAuthn as primary.

---

#### AUTH-PLAT-003: No Rate Limiting on MFA Verification
**Severity:** HIGH (part of CRIT-004)
**Location:** `router_auth.py:165-182`

6-digit TOTP = 1,000,000 combinations. With ±1 window, 3 valid codes at any time. No rate limit allows ~300 req/sec → full space searchable in ~1 hour.

**Fix:** Implement strict rate limiting (5 attempts per 5 min per IP + account).

---

#### AUTH-PLAT-004: Refresh Token Absolute Expiry Not Enforced on Rotation
**Severity:** MEDIUM  
**Location:** `auth.py:589-593`

```python
absolute_expiry = row.session_started_at + timedelta(
    minutes=settings.platform_refresh_token_minutes  # 720 min = 12 hrs
)
new_expiry = min(now + timedelta(minutes=settings.platform_refresh_token_minutes), absolute_expiry)
```

The absolute expiry is correctly calculated, but if `platform_refresh_token_minutes` is changed in config, existing sessions may exceed new limit.

**Fix:** Store `absolute_expiry` in the token row at creation; validate against stored value.

---

#### AUTH-PLAT-005: Password Reset Token Reuse Possible
**Severity:** MEDIUM  
**Location:** `router_auth.py:389-426`

Password reset uses `PlatformOneTimeToken` with purpose `ADMIN_PASSWORD_RESET`. The token is consumed (`used_at` set) but the `token_hash` remains in DB. No explicit check prevents re-use of same token hash if `used_at` is somehow cleared (unlikely but possible via direct DB manipulation).

**Fix:** Add unique constraint on `(token_hash, purpose)` where `used_at IS NULL`, or hard-delete consumed tokens.

---

#### AUTH-PLAT-006: Invitation Token Exposure in Auto-Approve Flow
**Severity:** MEDIUM  
**Location:** `self_service.py:269-436`

When `auto_approve=True`, the raw invitation token is returned in the API response:

```python
return {
    "invitation_token": raw_token,  # RAW TOKEN IN RESPONSE
    "invitation_expires_at": now + timedelta(hours=72),
}
```

This is intended for dev/test but could be enabled in production via platform setting.

**Fix:** Never return raw token in API response. Send via email only.

---

## 2. Staff Realm Authentication (Restaurant Employees)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      STAFF REALM AUTH FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /api/v1/auth/login                                        │
│  ├── Email + Password                                           │
│  ├── Argon2id verification                                      │
│  ├── Account lockout check (BROKEN - CRIT-003)                  │
│  ├── Finds first ACTIVE membership                              │
│  ├── Tenant suspension check                                    │
│  └── Returns: {access_token, user: Me}                          │
│                                                                  │
│  Token: JWT (HS256, SECRET_KEY)                                 │
│  ├── Claims: sub, mid, rid, tenant_id, realm=staff, ver, exp   │
│  ├── Expiry: 480 minutes (8 hours) — EXCESSIVE                 │
│  └── Transport: Authorization: Bearer <token> header            │
│                                                                  │
│  NO REFRESH TOKEN — Token expiry = session expiry               │
│  NO MFA SUPPORT                                                 │
│  NO TOKEN ROTATION                                              │
│  NO REUSE DETECTION                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Critical Vulnerabilities

#### AUTH-STAFF-001: No Refresh Token Mechanism
**Severity:** HIGH  
**Location:** `security.py:117-137`, `identity/auth.py:41-81`

Staff tokens are **long-lived (8 hours)** with **no refresh mechanism**. This forces a trade-off:
- Short expiry → frequent re-login (poor UX)
- Long expiry → high impact if token stolen

**Impact:** Stolen access token valid for 8 hours. No way to revoke except bumping `token_version` on membership (force logout all sessions).

**Fix:** Implement refresh token rotation similar to platform realm.

---

#### AUTH-STAFF-002: Excessive Access Token Lifetime (8 Hours)
**Severity:** HIGH  
**Location:** `config.py:26`, `security.py:126`

```python
# config.py:26
access_token_minutes: int = 480  # 8 HOURS
```

8-hour tokens violate OWASP recommendation (15-30 min for access tokens). Combined with no refresh token, this is a significant exposure window.

**Fix:** Reduce to 15-30 minutes; add refresh token rotation.

---

#### AUTH-STAFF-003: Bearer Token in Authorization Header (Not HttpOnly Cookie)
**Severity:** MEDIUM  
**Location:** `api.ts:12-19`, `platformApi.ts` (web), `auth.tsx` (mobile)

```typescript
// apps/web/src/lib/api.ts:12-19
export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);  // XSS ACCESSIBLE
}
```

Tokens stored in `sessionStorage` (web) or `SecureStore` (mobile). Web storage is accessible via XSS.

**Fix:** Move to HttpOnly cookies for web; keep SecureStore for mobile (acceptable).

---

#### AUTH-STAFF-004: No MFA Support for Staff
**Severity:** HIGH  
**Location:** `tenancy/permissions.py`, `identity/models.py`

Staff roles (Owner, Manager, Waiter, Kitchen, Cashier) have **no MFA capability**. High-privilege roles (Owner, Manager) can perform financial operations, staff management, configuration changes without second factor.

**Fix:** Add TOTP MFA to staff realm, mandatory for Owner/Manager roles.

---

#### AUTH-STAFF-005: Login Returns First Active Membership Only
**Severity:** MEDIUM  
**Location:** `identity/auth.py:61-63`

```python
membership = next((m for m in user.memberships if m.status == "ACTIVE"), None)
```

Users with multiple restaurant memberships always get the first one. No tenant selection during login.

**Impact:** User cannot choose which restaurant to access; must log out/in or use tenant switching (not implemented).

**Fix:** Return all active memberships; let user select; issue token for selected membership.

---

#### AUTH-STAFF-006: No Concurrent Session Limit
**Severity:** LOW  
**Location:** N/A

No limit on simultaneous sessions per user. No session listing/revocation UI for staff.

**Fix:** Add session management (list, revoke) similar to platform realm.

---

## 3. Customer QR Surface Authentication

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CUSTOMER QR AUTH FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Customer scans QR code on table                             │
│     QR contains: https://{subdomain}.platform.com/qr/{token}   │
│                                                                  │
│  2. GET /public/qr/{qr_token}/menu                              │
│     ├── Resolves QR token → table + restaurant                  │
│     ├── Hostname enforcement (assert_qr_hostname)               │
│     └── Returns menu (no auth required)                         │
│                                                                  │
│  3. POST /public/qr/{qr_token}/orders                           │
│     ├── Idempotency-Key required                                │
│     ├── Creates order with status_token                         │
│     │   ├── status_token = URL-safe random 32 bytes             │
│     │   ├── Stored: SHA-256 hash in order.customer_status_token_hash
│     │   └── Returned in response                                │
│     └── Returns: order + status_token                           │
│                                                                  │
│  4. GET /public/orders/{status_token}                           │
│     ├── Looks up order by status_token hash                     │
│     ├── Hostname enforcement                                    │
│     └── Returns order status (no auth)                          │
│                                                                  │
│  5. POST /public/orders/{status_token}/cancel|rate              │
│     ├── Uses status_token as proof of ownership                 │
│     └── No additional verification                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Vulnerabilities

#### AUTH-QR-001: Status Token Not Bound to Session/IP/Device
**Severity:** HIGH  
**Location:** `orders.py:210-220`, `qr/router.py:73-101`

```python
# orders.py:210
status_token = new_token()  # 32 bytes URL-safe
# orders.py:219
customer_status_token_hash=hash_token(status_token),
```

The `status_token` is a **bearer token** — anyone with the token can:
- View order status
- Cancel the order
- Rate the order
- View the bill

**No binding to:** IP address, User-Agent, device fingerprint, session.

**Impact:** Token leakage (referrer, logs, shoulder surfing) = full order control.

**Fix:** Bind status_token to client fingerprint (IP + UA hash) on first use; reject mismatches.

---

#### AUTH-QR-002: QR Token Predictability / Enumeration
**Severity:** MEDIUM  
**Location:** `operations/models.py:32-33`, `orders.py:173-187`

```python
# TableQrCode model
token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
token_preview: Mapped[str] = mapped_column(String(16), nullable=False)
raw_token: Mapped[str] = mapped_column(String(64), nullable=True)  # STORED IN DB!
```

The `raw_token` is stored in plaintext in the database (nullable but populated). QR tokens use `secrets.token_urlsafe(32)` (256 bits entropy — good), but storage of raw token is unnecessary risk.

**Fix:** Remove `raw_token` column; only store hash + preview.

---

#### AUTH-QR-003: No Rate Limiting on Public Order Submission
**Severity:** HIGH (part of CRIT-004)
**Location:** `qr/router.py:48-70`

Unlimited order submission per QR code. Can be used for:
- Kitchen DoS (flooding with orders)
- Menu enumeration
- Bill manipulation

**Fix:** Rate limit per QR token (e.g., 10 orders per 5 min).

---

#### AUTH-QR-004: Hostname Enforcement Bypass in Development
**Severity:** MEDIUM  
**Location:** `hostname.py:56, 122-124`

```python
_DEV_MODE = settings.app_env != "production"
_DEV_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "testserver"}

# In assert_qr_hostname:
if _DEV_MODE and normalized in _DEV_HOSTS:
    return  # BYPASSES HOSTNAME CHECK
```

In development, any `localhost` variant bypasses hostname check. If development instance is exposed to LAN (common), cross-tenant access possible.

**Fix:** Never bypass hostname enforcement. Use proper dev domains (e.g., `tenant1.localhost`, `tenant2.localhost` via `/etc/hosts`).

---

## 4. Cross-Realm Authentication Issues

### AUTH-CROSS-001: Realm Confusion Possible via Token Reuse
**Severity:** MEDIUM  
**Location:** `security.py:140-152`, `security.py:196-222`

Both `decode_access_token` and `decode_platform_access_token` validate `realm` claim, but:
- Different signing keys (good)
- Same algorithm (HS256)
- No audience (`aud`) claim differentiation

If `SECRET_KEY == PLATFORM_SECRET_KEY` (possible in dev), cross-realm token validation could pass realm check but fail signature. Currently mitigated by different keys.

**Fix:** Add `aud` claim: `aud: "platform"` vs `aud: "staff"`.

---

### AUTH-CROSS-002: Staff Token Accepted on Platform Endpoints (Theoretical)
**Severity:** LOW  
**Location:** `deps.py:79-118` vs `platform/deps.py:58-95`

Platform realm reads from **cookies only**; staff realm reads from **Authorization header**. No cross-contamination possible in current implementation.

**Status:** ✅ PROPERLY ISOLATED

---

## 5. Password Policy Analysis

### Current Policy (`security.py:61-85`)

| Requirement | Value | OWASP Recommended |
|-------------|-------|-------------------|
| Min Length | 8 | 12+ |
| Max Length | 128 | 64-128 |
| Uppercase | Required | Required |
| Lowercase | Required | Required |
| Number | Required | Required |
| Special Char | Required | Required |
| Breach Check | ❌ None | ✅ Required (HIBP) |

**Gap:** No compromised password checking (HaveIBeenPwned API).

**Fix:** Integrate `pwned-passwords` check on registration/password change.

---

## 6. Session Management Summary

| Feature | Platform Realm | Staff Realm | Customer QR |
|---------|---------------|-------------|-------------|
| Access Token Expiry | 15 min | 8 hours | N/A (status_token) |
| Refresh Token | ✅ 12 hrs rotating | ❌ None | ❌ None |
| Reuse Detection | ✅ Family burn | ❌ None | ❌ None |
| HttpOnly Cookies | ✅ Yes | ❌ Bearer header | ❌ URL param |
| MFA | ✅ TOTP + Recovery | ❌ None | ❌ None |
| Step-up Auth | ✅ 5 min window | ❌ None | ❌ None |
| Session Listing | ✅ Yes | ❌ None | ❌ None |
| Session Revocation | ✅ Per-family + All | ❌ Force logout only | ❌ None |
| Concurrent Session Limit | ❌ None | ❌ None | ❌ None |
| Device Fingerprinting | ❌ None | ❌ None | ❌ None |
| Account Lockout | ✅ Design (broken impl) | ✅ Design (broken impl) | ❌ None |

---

## 7. Recommendations Priority Matrix

| Priority | Finding | Realm | Effort |
|----------|---------|-------|--------|
| P0 | CRIT-003: Fix lockout store (Redis) | Both | 4h |
| P0 | CRIT-004: Rate limit auth endpoints | All | 6h |
| P0 | AUTH-STAFF-001: Add refresh tokens | Staff | 8h |
| P0 | AUTH-STAFF-002: Reduce token expiry | Staff | 1h |
| P1 | AUTH-PLAT-003: Rate limit MFA verify | Platform | 2h |
| P1 | AUTH-QR-001: Bind status_token | QR | 4h |
| P1 | AUTH-STAFF-004: Add MFA for Owner/Manager | Staff | 12h |
| P2 | AUTH-PLAT-002: Don't return raw MFA secret | Platform | 2h |
| P2 | AUTH-QR-002: Remove raw_token column | QR | 1h |
| P2 | AUTH-STAFF-003: Move to HttpOnly cookies | Staff (web) | 6h |
| P3 | AUTH-PLAT-001: Unique dev keys | Platform | 2h |
| P3 | Password breach checking | Both | 4h |

---

## 8. Verification Test Suite

```python
# tests/test_auth_security.py

def test_platform_refresh_reuse_detection():
    """Replay of rotated refresh token burns entire family."""
    # 1. Login → get refresh token
    # 2. Refresh → get new refresh token
    # 3. Replay old refresh token
    # 4. Assert: 401 TOKEN_REUSE, family revoked
    pass

def test_staff_token_expiry_short():
    """Staff access token expires in 15-30 min, not 8 hours."""
    token = create_access_token(...)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    exp_delta = payload["exp"] - payload["iat"]
    assert exp_delta <= 30 * 60  # 30 minutes max

def test_qr_status_token_binding():
    """Status token bound to client fingerprint."""
    # 1. Submit order → get status_token
    # 2. Request status from different IP
    # 3. Assert: 403 Forbidden
    pass

def test_mfa_rate_limit():
    """MFA verification limited to 5 attempts per 5 min."""
    for i in range(6):
        response = client.post("/api/platform/auth/mfa/verify", 
            json={"ticket": valid_ticket, "code": f"{i:06d}"})
    assert response.status_code == 429
    pass

def test_no_raw_mfa_secret_in_logs():
    """MFA enrollment secret not in response body."""
    response = client.post("/api/platform/auth/mfa/enroll/start", ...)
    assert "secret" not in response.json()  # Or only in QR code
    pass
```

---

## Conclusion

The **platform realm** authentication is well-architected with modern patterns (rotating refresh tokens, reuse detection, MFA, step-up). However, **critical infrastructure gaps** (in-memory lockout, no rate limiting) undermine it.

The **staff realm** is significantly weaker — no refresh tokens, 8-hour access tokens, no MFA, bearer tokens in headers. This realm handles financial operations and staff management; it should be hardened to near-platform standards.

The **customer QR surface** has a clever token design but lacks binding and rate limiting.

**Immediate focus:** Fix CRIT-003, CRIT-004, AUTH-STAFF-001, AUTH-STAFF-002 before production.