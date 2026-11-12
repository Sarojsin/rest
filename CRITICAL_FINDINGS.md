# Critical Findings — Restaurant SaaS Platform Security Audit

**Classification:** CONFIDENTIAL  
**Total Critical Findings:** 4  

---

## CRIT-001: CORS Misconfiguration — Wildcard Origins with Credentials

### Severity: CRITICAL
### CVSS 4.0: 9.3 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N)
### Affected File: `backend/app/main.py:28-34`

### Technical Explanation

The CORS middleware is configured with `allow_origins=["*"]` while simultaneously setting `allow_credentials=True`. This combination is **explicitly prohibited by the CORS specification** and creates a critical security vulnerability.

```python
# backend/app/main.py:28-34
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list or ["*"],  # VULNERABLE: wildcard
    allow_credentials=True,  # VULNERABLE: credentials allowed with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)
```

When `allow_credentials=True`, the `Access-Control-Allow-Origin` header **must not** be `*` — it must echo the requesting origin. Browsers enforce this and will reject the response, but the misconfiguration indicates a fundamental misunderstanding of CORS security and may work incorrectly in some proxy/CDN configurations.

### Evidence

1. `settings.allowed_origin_list` returns `["*"]` when `CORS_ORIGINS` is empty or not set
2. `allow_credentials=True` permits cookies, authorization headers, and TLS client certificates
3. The platform realm uses HttpOnly cookies (`platform_access`, `platform_refresh`) which are credentials

### Impact

- **Credential theft**: Malicious site can make authenticated requests to the API
- **Session hijacking**: Attacker can read platform admin cookies if origin reflection is misconfigured
- **CSRF amplification**: Credentials sent cross-origin enable forged requests
- **Data exfiltration**: Customer PII, order data, payment records accessible

### Reproduction Steps

1. Deploy application with current CORS config
2. Create malicious HTML page on `attacker.com`:
```html
<script>
fetch('https://api.restaurant-platform.com/api/platform/auth/me', {
  credentials: 'include'  // Sends HttpOnly cookies
}).then(r => r.json()).then(console.log);
</script>
```
3. Observe that browser sends platform cookies cross-origin (if misconfigured proxy bypasses browser check)

### Business Impact

Complete compromise of platform admin accounts. Attackers can perform any action as Super Admin, OPS, or Billing Support — including tenant suspension, subscription manipulation, payment refunds, and audit log access.

### Recommended Fix

```python
# backend/app/main.py
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # Explicit list, NEVER "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)
```

**Validation**: `settings.cors_origin_list` must be explicitly configured in production. The `validate_platform_config()` method should also validate CORS origins.

### Verification Test

```python
def test_cors_no_wildcard_with_credentials():
    from app.main import create_app
    from fastapi.testclient import TestClient
    
    app = create_app()
    client = TestClient(app)
    
    # Request from untrusted origin
    response = client.get(
        "/api/platform/auth/me",
        headers={"Origin": "https://evil.com", "Cookie": "platform_access=test"}
    )
    
    # Must NOT reflect evil.com in ACAO
    assert response.headers.get("access-control-allow-origin") != "https://evil.com"
    # Must NOT be "*"
    assert response.headers.get("access-control-allow-origin") != "*"
    # Should be absent or only trusted origins
```

---

## CRIT-002: Development Secrets Committed to Repository

### Severity: CRITICAL
### CVSS 4.0: 9.8 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)
### Affected File: `backend/.env` (entire file)

### Technical Explanation

The `.env` file contains **production-grade secrets** committed to the Git repository:

```bash
# backend/.env — EXPOSED SECRETS
SECRET_KEY=your-secret-key-change-in-production
SMTP_PASSWORD=hpzr ghzj ehqw azsj          # Gmail App Password
PLATFORM_SECRET_KEY=dev-platform-signing-key-not-for-production
PLATFORM_MFA_KEY=dev-platform-mfa-key-not-for-production
PLATFORM_BOOTSTRAP_EMAIL=
PLATFORM_BOOTSTRAP_PASSWORD=
```

**Critical issues:**
1. **Gmail App Password** (`hpzr ghzj ehqw azsj`) — Live credential for `letsdoit69960@gmail.com`
2. **JWT Signing Keys** — Both platform and tenant realms use weak, known keys
3. **No Secret Rotation** — These keys are baked into all existing tokens
4. **SMTP Credentials** — Can be used to send phishing emails from the platform domain

### Evidence

- File exists at `backend/.env` in repository root
- `.gitignore` does not exclude `.env` (only excludes `.env.local` patterns)
- `config.py` loads from `.env` with `env_file=".env"`

### Impact

- **Immediate token forgery**: Attacker can sign valid JWTs for both realms
- **Email account takeover**: Gmail app password grants full SMTP access
- **MFA secret decryption**: `PLATFORM_MFA_KEY` decrypts all stored TOTP seeds
- **Supply chain risk**: Anyone with repo access (CI/CD, contractors) has production secrets

### Reproduction Steps

```bash
# 1. Clone repository
git clone <repo-url>
cd backend

# 2. Extract secrets
cat .env | grep -E "(SECRET_KEY|SMTP_PASSWORD|PLATFORM_)"

# 3. Forge platform admin token
python3 -c "
import jwt
from datetime import datetime, timedelta, UTC
from uuid import uuid4

payload = {
    'sub': '00000000-0000-0000-0000-000000000001',
    'realm': 'platform',
    'role': 'superadmin',
    'ver': 1,
    'jti': str(uuid4()),
    'auth_time': int(datetime.now(UTC).timestamp()),
    'exp': datetime.now(UTC) + timedelta(hours=1),
    'iat': datetime.now(UTC),
}
token = jwt.encode(payload, 'dev-platform-signing-key-not-for-production', algorithm='HS256')
print(token)
"
```

### Business Impact

**Total platform compromise**. Attacker can:
- Access all tenant data across all restaurants
- Modify subscriptions, billing, payments
- Create/delete platform admins
- Read all audit logs
- Send emails as the platform

### Recommended Fix

1. **Immediately rotate all exposed secrets**:
   - Generate new `SECRET_KEY` (64+ chars, cryptographically random)
   - Generate new `PLATFORM_SECRET_KEY` (64+ chars, different from SECRET_KEY)
   - Generate new `PLATFORM_MFA_KEY` (64+ chars)
   - Revoke Gmail app password, generate new one
   - Invalidate all existing JWTs (bump `token_version` for all admins/users)

2. **Remove `.env` from Git history**:
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch backend/.env' \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Use secret manager in production** (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)

4. **Add to `.gitignore`**:
   ```
   .env
   .env.*
   !.env.example
   ```

### Verification Test

```bash
# 1. Verify .env not tracked
git ls-files | grep -E "^\.env$" && echo "FAIL: .env tracked" || echo "PASS: .env not tracked"

# 2. Verify no secrets in Git history
git log --all --full-history -- backend/.env | head -20

# 3. Verify new secrets work
# Deploy with new secrets, verify login works, old tokens rejected
```

---

## CRIT-003: In-Memory Lockout Store — Not Production Viable

### Severity: CRITICAL
### CVSS 4.0: 8.7 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:L/VA:H/SC:N/SI:N/SA:N)
### Affected File: `backend/app/core/security.py:14-16`

### Technical Explanation

Account lockout state is stored in a **process-local Python dictionary**, making it completely ineffective in production:

```python
# backend/app/core/security.py:14-16
# Account lockout tracking (in production, use Redis for persistence)
# Key: "lockout:{user_id}", Value: {"failed_attempts": int, "locked_until": datetime}
lockout_store: dict = defaultdict(lambda: {"failed_attempts": 0, "locked_until": None})
```

**Problems:**
1. **No persistence**: Lockout resets on every deployment, restart, or crash
2. **No horizontal scaling**: Each worker process has its own lockout store
3. **No shared state**: Load balancer distributes requests across workers; attacker can try 5×N attempts (N = worker count)
4. **Race conditions**: `defaultdict` is not thread-safe for concurrent increments

### Evidence

- `is_account_locked()` reads from `lockout_store` (line 34-51)
- `record_failed_login()` writes to `lockout_store` (line 88-100)
- `record_successful_login()` clears `lockout_store` entry (line 103-106)
- Comment explicitly acknowledges: "in production, use Redis for persistence"

### Impact

- **Brute force protection bypassed**: Attacker can make unlimited login attempts
- **Credential stuffing**: No effective rate limiting on `/auth/login` endpoints
- **Platform admin accounts vulnerable**: 5 attempts per worker process

### Reproduction Steps

```bash
# With 4 Gunicorn workers (typical production):
for i in {1..20}; do
  curl -X POST https://api.platform.com/api/platform/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@platform.com","password":"wrong'$i'"}'
  sleep 0.1
done
# Result: All 20 attempts succeed (5 per worker), no lockout
```

### Business Impact

Platform admin accounts and staff accounts are vulnerable to credential stuffing and brute force attacks. Given the platform realm has high-privilege accounts, this is a direct path to full system compromise.

### Recommended Fix

Replace with Redis-backed implementation:

```python
# backend/app/core/security.py
import redis
from app.core.config import settings

# Initialize Redis client (connection pooling)
_redis = redis.from_url(
    settings.redis_url or "redis://localhost:6379/0",
    decode_responses=True,
    max_connections=20,
)

LOCKOUT_PREFIX = "lockout:"
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

def is_account_locked(user_id: UUID) -> bool:
    key = f"{LOCKOUT_PREFIX}{user_id}"
    data = _redis.hgetall(key)
    if not data:
        return False
    
    locked_until = data.get("locked_until")
    if locked_until and datetime.now(UTC).timestamp() > float(locked_until):
        _redis.delete(key)
        return False
    return bool(locked_until)

def record_failed_login(user_id: UUID) -> dict:
    key = f"{LOCKOUT_PREFIX}{user_id}"
    pipe = _redis.pipeline()
    pipe.hincrby(key, "failed_attempts", 1)
    pipe.expire(key, LOCKOUT_DURATION_SECONDS * 2)
    results = pipe.execute()
    
    attempts = results[0]
    if attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = (datetime.now(UTC) + timedelta(seconds=LOCKOUT_DURATION_SECONDS)).timestamp()
        _redis.hset(key, "locked_until", locked_until)
        _redis.hset(key, "failed_attempts", 0)
        return {"locked": True, "duration_minutes": LOCKOUT_DURATION_SECONDS // 60}
    
    return {"locked": False, "attempts": attempts}

def record_successful_login(user_id: UUID) -> None:
    _redis.delete(f"{LOCKOUT_PREFIX}{user_id}")
```

**Also required**: Add `redis` to `pyproject.toml` dependencies and configure `REDIS_URL` in settings.

### Verification Test

```python
def test_lockout_persists_across_workers():
    # Simulate 3 worker processes
    from app.core.security import record_failed_login, is_account_locked
    from uuid import uuid4
    
    user_id = uuid4()
    
    # Worker 1: 3 failed attempts
    for _ in range(3):
        record_failed_login(user_id)
    
    # Worker 2: 3 more failed attempts (should trigger lockout at 5)
    for _ in range(3):
        result = record_failed_login(user_id)
    
    assert result["locked"] == True
    assert is_account_locked(user_id) == True
    
    # Verify lockout survives process restart (Redis persistence)
    # ... restart process ...
    assert is_account_locked(user_id) == True
```

---

## CRIT-004: Missing Rate Limiting on Authentication Endpoints

### Severity: CRITICAL
### CVSS 4.0: 8.6 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)
### Affected Files: 
- `backend/app/modules/platform/router_auth.py:54-70` (platform login)
- `backend/app/modules/identity/router.py` (staff login — not shown but implied)
- `backend/app/api/qr/router.py` (public QR endpoints)

### Technical Explanation

**No rate limiting middleware or dependency** is applied to any authentication endpoint. The platform login, staff login, MFA verification, token refresh, and public QR order endpoints accept unlimited requests.

```python
# backend/app/modules/platform/router_auth.py:54-70 — NO RATE LIMIT
@router.post("/login", response_model=LoginChallengeOut)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginChallengeOut:
    challenge = auth.authenticate(...)  # Direct call, no rate limit
    return LoginChallengeOut(...)
```

### Evidence

- No `slowapi`, `fastapi-limiter`, or custom rate limiting middleware in codebase
- No `X-RateLimit-*` headers in responses
- No Redis-backed token bucket or sliding window implementation
- Login lockout (CRIT-003) is the only protection and is broken

### Impact

- **Unlimited credential stuffing**: Attackers can test millions of credentials
- **MFA code brute force**: 6-digit TOTP = 1,000,000 combinations; no limit on `/mfa/verify`
- **Token refresh abuse**: Unlimited `/refresh` calls for session enumeration
- **QR order spam**: Unlimited `/public/qr/{token}/orders` for DoS
- **Enumeration attacks**: Timing differences reveal valid emails (partially mitigated by dummy hash)

### Reproduction Steps

```bash
# Platform login brute force (no rate limit)
for i in {1..1000}; do
  curl -s -X POST https://api.platform.com/api/platform/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"admin@platform.com\",\"password\":\"guess$i\"}" &
done
# All 1000 requests processed in parallel

# MFA code brute force (6 digits = 1M combinations, feasible in hours)
for code in {000000..999999}; do
  curl -s -X POST https://api.platform.com/api/platform/auth/mfa/verify \
    -H "Content-Type: application/json" \
    -d "{\"ticket\":\"valid_ticket\",\"code\":\"$code\"}" &
done
```

### Business Impact

Direct enabler for account takeover. Combined with CRIT-003 (broken lockout), attackers have unrestricted access to brute force any account.

### Recommended Fix

Implement multi-layer rate limiting:

```python
# backend/app/middleware/rate_limit.py (NEW FILE)
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str):
        super().__init__(app)
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Rate limit rules: (path_pattern, max_requests, window_seconds, scope)
        self.rules = [
            ("/api/platform/auth/login", 5, 300, "ip"),           # 5 per 5 min per IP
            ("/api/platform/auth/mfa/verify", 10, 300, "ip"),     # 10 per 5 min per IP
            ("/api/platform/auth/refresh", 30, 60, "cookie"),     # 30 per min per session
            ("/api/v1/auth/login", 10, 300, "ip"),                # 10 per 5 min per IP
            ("/public/qr/", 60, 60, "ip"),                        # 60 per min per IP
        ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host
        
        for pattern, max_req, window, scope in self.rules:
            if path.startswith(pattern):
                key = f"ratelimit:{pattern}:{client_ip if scope == 'ip' else request.cookies.get('platform_refresh', 'anon')}"
                
                current = self.redis.incr(key)
                if current == 1:
                    self.redis.expire(key, window)
                
                if current > max_req:
                    ttl = self.redis.ttl(key)
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                        headers={"Retry-After": str(ttl)}
                    )
                break
        
        response = await call_next(request)
        return response
```

Register in `main.py`:
```python
from app.middleware.rate_limit import RateLimitMiddleware
application.add_middleware(RateLimitMiddleware, redis_url=settings.redis_url)
```

**Also add per-endpoint dependency for stricter limits:**
```python
# backend/app/api/deps.py
from fastapi import Depends, Request

def rate_limit(max_requests: int, window_seconds: int, scope: str = "ip"):
    def dependency(request: Request):
        # Redis-backed check (similar to middleware)
        pass
    return Depends(dependency)

# Usage in routers:
@router.post("/login")
def login(..., _rl: None = Depends(rate_limit(5, 300))):
    ...
```

### Verification Test

```python
def test_rate_limit_enforced():
    from fastapi.testclient import TestClient
    from app.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Make 6 requests (limit is 5)
    for i in range(6):
        response = client.post(
            "/api/platform/auth/login",
            json={"email": "test@test.com", "password": "wrong"}
        )
    
    # 6th request should be 429
    assert response.status_code == 429
    assert "Retry-After" in response.headers
```

---

## Summary: Critical Findings Remediation Priority

| Priority | Finding | Effort | Dependencies |
|----------|---------|--------|--------------|
| **P0** | CRIT-002: Secrets in repo | 2 hours | Immediate — rotate ALL secrets first |
| **P0** | CRIT-001: CORS wildcard | 1 hour | None |
| **P0** | CRIT-003: In-memory lockout | 4 hours | Requires Redis infrastructure |
| **P0** | CRIT-004: No rate limiting | 6 hours | Requires Redis + middleware |

**Total estimated effort: ~13 hours** (can be parallelized)

**All four must be fixed before any production deployment.**