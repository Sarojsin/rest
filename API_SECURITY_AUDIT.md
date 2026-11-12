# API Security Audit — Restaurant SaaS Platform

**Classification:** CONFIDENTIAL  
**Scope:** REST API endpoints, input validation, rate limiting, error handling, security headers  

---

## Executive Summary

The API is built on **FastAPI** with **Pydantic v2** for validation. It has **good foundational security** (input validation, dependency injection, structured error handling) but **critical gaps** in rate limiting, security headers, and public endpoint protection.

**Overall API Security Rating: MODERATE — Good validation, missing runtime protections**

---

## 1. API Surface Mapping

| Realm | Base Path | Auth | Endpoints | Risk Level |
|-------|-----------|------|-----------|------------|
| Platform Admin | `/api/platform/*` | HttpOnly Cookie + CSRF | ~35 | HIGH |
| Staff (Restaurant) | `/api/v1/*` | Bearer Token | ~80 | HIGH |
| Public QR Ordering | `/public/qr/*`, `/public/orders/*` | Status Token (URL) | ~12 | MEDIUM |
| Health/Metrics | `/health`, `/metrics` | None | 3 | LOW |

---

## 2. Input Validation Analysis

### Strengths

| Control | Implementation | Coverage |
|---------|---------------|----------|
| **Pydantic Models** | All request/response bodies | ✅ 100% |
| **UUID Validation** | `UUID` type in path/query params | ✅ All IDs |
| **Email Validation** | `EmailStr` type | ✅ All email fields |
| **Enum Validation** | `Literal` / `Enum` for status fields | ✅ All enums |
| **Numeric Bounds** | `Field(ge=0, le=999999)` | ✅ Prices, quantities |
| **String Length** | `Field(min_length=1, max_length=255)` | ✅ Most strings |
| **Idempotency Keys** | Required header on mutating endpoints | ✅ Orders, payments |

### Gaps

#### API-VAL-001: No Request Size Limits
**Severity:** MEDIUM  
**Location:** `main.py` (no middleware)

FastAPI default: **no body size limit**. Large payloads can cause:
- Memory exhaustion (DoS)
- Slow request processing
- Deserialization attacks

**Fix:** Add middleware:
```python
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 1024 * 1024):  # 1MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return Response("Payload too large", status_code=413)
        return await call_next(request)
```

---

#### API-VAL-002: Missing Input Sanitization for Rich Text Fields
**Severity:** LOW  
**Location:** Menu descriptions, order notes, review text

Fields like `menu_item.description`, `order.notes`, `review.comment` accept raw strings. No XSS sanitization (though rendered in React — client-side escaping helps).

**Fix:** Add server-side sanitization (bleach) for any field rendered in HTML context.

---

#### API-VAL-003: UUID Path Parameter Not Validated for Existence (Sometimes)
**Severity:** LOW  
**Location:** Various routers

FastAPI validates UUID format but not existence. Returns 404 vs 400 correctly, but some endpoints return 500 if DB error.

**Fix:** Consistent 404 for not-found; use `get_object_or_404` pattern.

---

## 3. Rate Limiting — CRITICAL GAP

### Current State: **NO RATE LIMITING ANYWHERE**

| Endpoint Category | Rate Limit | Status |
|-------------------|------------|--------|
| Platform login | None | ❌ CRIT-004 |
| Platform MFA verify | None | ❌ CRIT-004 |
| Staff login | None | ❌ CRIT-004 |
| QR order submission | None | ❌ CRIT-004 |
| Payment webhooks | None | ❌ HIGH |
| API mutations (POST/PUT/DELETE) | None | ❌ HIGH |
| API reads (GET) | None | ❌ MEDIUM |

**Impact:** Unlimited brute force, DoS, enumeration, scraping.

**Required Implementation:** See CRIT-004 fix in CRITICAL_FINDINGS.md

---

## 4. Security Headers

### Current State: **MISSING**

```python
# main.py — NO security headers middleware
application = FastAPI(...)
# Missing: SecurityHeadersMiddleware
```

### Required Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'` | XSS mitigation |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing prevention |
| `X-Frame-Options` | `DENY` | Clickjacking prevention |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage control |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Feature policy |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | HTTPS enforcement (prod) |
| `Cross-Origin-Opener-Policy` | `same-origin` | Cross-origin isolation |
| `Cross-Origin-Resource-Policy` | `same-origin` | Resource isolation |

**Implementation:**
```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response
```

---

## 5. Error Handling & Information Leakage

### Current State: **GOOD — Structured errors, but stack traces in dev**

```python
# main.py:130-150
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.error(f"Unhandled error [{request_id}]: {exc}", exc_info=True)
    
    if settings.app_env == "production":
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "An unexpected error occurred", "request_id": request_id}
        )
    else:
        # DEV: Returns full traceback — RISK if dev exposed
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": str(exc), "traceback": traceback.format_exc(), "request_id": request_id}
        )
```

### Issues

#### API-ERR-001: Dev Mode Stack Traces Leak Internals
**Severity:** MEDIUM  
**Location:** `main.py:145-150`

If development environment exposed (common in staging), full tracebacks reveal:
- File paths, function names
- Library versions
- SQL queries (sometimes)
- Internal architecture

**Fix:** Never return tracebacks in HTTP response. Log only.

---

#### API-ERR-002: Validation Errors Leak Field Names (Acceptable)
**Severity:** INFORMATIONAL  
**Location:** FastAPI default

Pydantic validation errors return field names and constraint details. This is acceptable for API usability but could aid enumeration.

**Status:** ✅ ACCEPTABLE (standard practice)

---

#### API-ERR-003: 404 vs 403 Distinction Leaks Resource Existence
**Severity:** LOW  
**Location:** Various endpoints

```python
# Current: Different responses
# Not found: 404 {"detail": "Not found"}
# No permission: 403 {"detail": "Permission denied"}
```

Attacker can enumerate valid resource IDs by checking 403 vs 404.

**Fix:** Normalize to 404 for both (or 403 for both) on authorization-protected resources.

---

## 6. Idempotency Implementation

### Current State: **GOOD — Required on Mutating Endpoints**

```python
# api/deps.py:30-45
def require_idempotency_key(
    idempotency_key: str = Header(..., alias="Idempotency-Key")
) -> str:
    if not idempotency_key or len(idempotency_key) < 16:
        raise HTTPException(400, "Invalid Idempotency-Key")
    return idempotency_key
```

**Usage:**
```python
@router.post("/orders")
def create_order(
    ...,
    idempotency_key: str = Depends(require_idempotency_key)
):
    # Check redis for existing key
    # If exists: return cached response
    # If not: process, store response with 24hr TTL
```

### Gap: **No Idempotency Key Storage Backend Shown**
**Severity:** MEDIUM  
**Location:** `api/deps.py` (dependency exists but storage not verified)

The dependency validates format but **actual deduplication logic** must be in each endpoint. Not centralized.

**Fix:** Create reusable `IdempotencyService` with Redis backend; apply as dependency.

---

## 7. CORS Configuration — CRITICAL (CRIT-001)

### Current State: **WILDCARD WITH CREDENTIALS**

```python
# main.py:28-34
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**See CRIT-001 for full analysis.**

---

## 8. API Versioning & Deprecation

### Current State: **NO VERSIONING STRATEGY**

- All endpoints under `/api/v1/` or `/api/platform/`
- No `Accept` header versioning
- No deprecation headers (`Sunset`, `Deprecation`)
- Breaking changes deployed without notice

**Fix:** Implement URL versioning (`/api/v1/`, `/api/v2/`) with deprecation policy.

---

## 9. Public QR API Security

### Endpoints

| Endpoint | Auth | Risk |
|----------|------|------|
| `GET /public/qr/{qr_token}/menu` | None (QR token in path) | Menu scraping |
| `GET /public/qr/{qr_token}/tables` | None | Table enumeration |
| `POST /public/qr/{qr_token}/orders` | Idempotency-Key | **Order spam (DoS)** |
| `GET /public/orders/{status_token}` | Status token in path | Order tracking |
| `POST /public/orders/{status_token}/cancel` | Status token | Order cancellation |
| `POST /public/orders/{status_token}/rate` | Status token | Rating manipulation |

### Vulnerabilities

#### API-QR-001: No Rate Limiting on Public Endpoints
**Severity:** HIGH (part of CRIT-004)

Unlimited order submission, menu scraping, status polling.

**Fix:** Per-QR-token rate limits (10 orders/5min, 60 menu loads/min).

---

#### API-QR-002: QR Token in URL Path — Referer Leakage
**Severity:** MEDIUM  
**Location:** `qr/router.py`

QR token in path: `GET /public/qr/abc123/menu`
- Leaked in `Referer` header to external resources (images, analytics)
- Logged in proxy/access logs
- Browser history

**Fix:** Use POST with token in body for sensitive operations; keep GET for menu but accept token in header.

---

#### API-QR-003: Status Token Not Rotated
**Severity:** MEDIUM  
**Location:** `orders.py:210-220`

Single `status_token` per order, valid indefinitely. No rotation on view.

**Fix:** Rotate status_token on each status check; invalidate old.

---

## 10. Webhook Security (Stripe)

### Current State: **SIGNATURE VERIFICATION ONLY**

```python
# payments/router.py (inferred)
@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    # Process event...
```

### Gaps

#### API-WEB-001: No Replay Protection
**Severity:** MEDIUM  
**Location:** `payments/router.py`

Stripe includes `event.id` but no check for duplicate processing. Same event delivered twice = double fulfillment.

**Fix:** Store processed `event.id` in Redis with 30-day TTL; reject duplicates.

---

#### API-WEB-002: Webhook Tenant Resolution Trusts Metadata
**Severity:** MEDIUM (MT-009)

```python
tenant_id = event.data.object.metadata.get("tenant_id")
# No verification this matches the Stripe account
```

**Fix:** Map `stripe_account_id` → `tenant_id` in DB; verify webhook `account` parameter.

---

## 11. Request/Response Logging

### Current State: **BASIC REQUEST ID LOGGING**

```python
# main.py:100-120
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### Gaps

#### API-LOG-001: No Structured Audit Logging for Sensitive Operations
**Severity:** MEDIUM  
**Location:** Various routers

No consistent logging of:
- Who (user ID, role)
- What (action, resource ID)
- When (timestamp)
- Where (IP, user agent)
- Result (success/failure)

**Fix:** Implement `audit_log` dependency for sensitive endpoints.

---

#### API-LOG-002: Sensitive Data in Logs (Potential)
**Severity:** MEDIUM  
**Location:** `main.py:135` (exc_info=True logs full request)

Exception logs may include request body with passwords, tokens, PII.

**Fix:** Sanitize request logging (filter `password`, `token`, `secret`, `credit_card` fields).

---

## 12. API Documentation Exposure

### Current State: **SWAGGER UI ENABLED IN ALL ENVIRONMENTS**

```python
# main.py
application = FastAPI(
    docs_url="/docs",      # ENABLED in production!
    redoc_url="/redoc",    # ENABLED in production!
    openapi_url="/openapi.json"
)
```

### Issues

#### API-DOC-001: Swagger UI Exposes All Endpoints in Production
**Severity:** LOW  
**Location:** `main.py`

Reveals:
- All endpoint paths, methods, parameters
- Request/response schemas
- Authentication requirements
- Internal model structures

**Fix:** Disable in production or protect with authentication.

---

## 13. Recommendations Priority Matrix

| Priority | Finding | Effort |
|----------|---------|--------|
| P0 | CRIT-001: Fix CORS wildcard | 1h |
| P0 | CRIT-004: Implement rate limiting | 6h |
| P0 | API-VAL-001: Request size limits | 1h |
| P1 | Security headers middleware | 2h |
| P1 | API-ERR-001: Remove dev tracebacks | 1h |
| P1 | API-QR-001: Rate limit public QR endpoints | 3h |
| P1 | API-WEB-001: Webhook replay protection | 2h |
| P2 | Idempotency service centralization | 4h |
| P2 | Structured audit logging | 8h |
| P2 | Sanitize exception logging | 2h |
| P3 | API versioning strategy | 8h |
| P3 | Disable Swagger in production | 1h |

---

## 14. Verification Test Suite

```python
# tests/test_api_security.py

def test_rate_limit_enforced():
    """All auth endpoints return 429 after threshold."""
    for endpoint in ["/api/platform/auth/login", "/api/v1/auth/login", "/public/qr/token/orders"]:
        for i in range(6):  # limit is 5
            response = client.post(endpoint, json={...})
        assert response.status_code == 429

def test_security_headers_present():
    """All responses include security headers."""
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers

def test_request_size_limit():
    """Payloads > 1MB rejected with 413."""
    large_payload = "x" * (2 * 1024 * 1024)  # 2MB
    response = client.post("/api/v1/orders", data=large_payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 413

def test_no_stacktrace_in_production():
    """Production errors don't leak tracebacks."""
    with patch("app.core.config.settings.app_env", "production"):
        response = client.get("/trigger-500")
        assert "traceback" not in response.json()
        assert "file" not in response.text.lower()

def test_cors_no_wildcard_credentials():
    """CORS doesn't allow credentials with wildcard origin."""
    response = client.options("/api/platform/auth/me", headers={"Origin": "https://evil.com"})
    assert response.headers.get("access-control-allow-origin") != "*"
    assert response.headers.get("access-control-allow-credentials") != "true"

def test_idempotency_key_required():
    """Mutating endpoints reject requests without Idempotency-Key."""
    response = client.post("/api/v1/orders", json={...})  # No header
    assert response.status_code == 400

def test_webhook_replay_protection():
    """Duplicate Stripe events rejected."""
    event = {"id": "evt_123", "type": "payment_intent.succeeded", ...}
    client.post("/webhook/stripe", json=event, headers={"stripe-signature": "..."})
    response = client.post("/webhook/stripe", json=event, headers={"stripe-signature": "..."})
    assert response.status_code == 200  # But idempotent - no double processing
    # Verify only one fulfillment created
```

---

## Conclusion

The API has **strong validation foundations** (Pydantic, FastAPI) but **lacks runtime protections** (rate limiting, security headers, request size limits). The **CORS misconfiguration (CRIT-001)** and **missing rate limiting (CRIT-004)** are critical and must be fixed immediately.

**Priority order:**
1. CRIT-001 (CORS) + CRIT-004 (Rate limiting) — P0
2. Security headers + Request size limits — P1
3. Public QR rate limiting + Webhook replay protection — P1
4. Audit logging + Error sanitization — P2