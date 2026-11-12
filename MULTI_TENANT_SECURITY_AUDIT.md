# Multi-Tenant Security Audit — Restaurant SaaS Platform

**Classification:** CONFIDENTIAL  
**Scope:** Tenant isolation, data separation, cross-tenant access prevention  

---

## Executive Summary

The platform implements **multi-tenancy via shared database with application-level isolation** using `x-tenant-id` header and SQLAlchemy query filters. **No Row-Level Security (RLS) policies** are enforced at the database layer. Tenant context is derived from the **staff JWT** (platform realm uses separate admin model).

**Overall Multi-Tenant Rating: MODERATE — Application-layer isolation only; no defense-in-depth**

---

## 1. Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-TENANT ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SHARED DATABASE (PostgreSQL)                                   │
│  ├── tenants                                                    │
│  ├── platform_admins (separate table)                           │
│  ├── staff_users (global)                                       │
│  ├── staff_memberships (user ↔ tenant + role)                   │
│  ├── restaurant_* tables (tenant-scoped via restaurant_id FK)   │
│  └── platform_* tables (global)                                 │
│                                                                  │
│  ISOLATION LAYERS:                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. MIDDLEWARE: TenantContextMiddleware                   │    │
│  │    - Extracts x-tenant-id header OR from staff JWT       │    │
│  │    - Validates tenant exists & is ACTIVE                 │    │
│  │    - Sets request.state.tenant_context                   │    │
│  │    - File: tenancy/middleware.py                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                      │
│                            ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 2. DEPENDENCY: get_tenant_context()                      │    │
│  │    - Returns TenantContext {tenant, actor, permissions}  │    │
│    - Enforces tenant status = ACTIVE                       │    │
│    - Builds StaffActor with permissions from membership    │    │
│    - File: api/deps.py                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                      │
│                            ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 3. QUERY FILTER: TenantAwareQuery / BaseModelMixin       │    │
│  │    - Auto-filters queries by tenant_id                   │    │
│    - BaseModelMixin.tenant_id column on all tenant models  │    │
│    - Usage: db.query(Model).filter(Model.tenant_id==...)   │    │
│    - File: tenancy/models.py, tenancy/query.py             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ❌ MISSING: Database RLS Policies                              │
│  ❌ MISSING: Tenant ID validation on all write paths            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Tenant Context Establishment

### Staff Realm Flow (`tenancy/middleware.py:20-65`)

```python
class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Try x-tenant-id header (explicit)
        tenant_id_header = request.headers.get("x-tenant-id")
        
        # 2. Fallback: extract from staff JWT
        auth_header = request.headers.get("Authorization")
        if not tenant_id_header and auth_header:
            try:
                payload = decode_access_token(auth_header.replace("Bearer ", ""))
                tenant_id_header = payload.get("tenant_id")
            except:
                pass
        
        # 3. Validate tenant exists and is ACTIVE
        if tenant_id_header:
            tenant = db.query(Tenant).filter_by(id=tenant_id_header).first()
            if tenant and tenant.status == TenantStatus.ACTIVE:
                request.state.tenant_context = TenantContext(tenant=tenant, ...)
        
        return await call_next(request)
```

### Issues

#### MT-001: x-tenant-id Header Trusted Without Authentication
**Severity:** HIGH  
**Location:** `tenancy/middleware.py:28-35`

The middleware accepts `x-tenant-id` header **without verifying the caller is authenticated** or authorized for that tenant. If an endpoint doesn't use `get_tenant_context` dependency, the header is accepted blindly.

```python
# Vulnerable pattern:
@router.get("/data")
def get_data(request: Request):  # No get_tenant_context dependency
    tenant_id = request.state.tenant_context.tenant_id  # Trusts header!
    return db.query(Data).filter_by(tenant_id=tenant_id).all()
```

**Impact:** Any authenticated user can access any tenant's data by sending `x-tenant-id: <target-tenant>`.

**Fix:** Remove header-based tenant resolution; **only** derive tenant from validated JWT. Header should be used only for platform admin impersonation (with permission check).

---

#### MT-002: Tenant Status Check Only in Middleware, Not RLS
**Severity:** MEDIUM  
**Location:** `tenancy/middleware.py:45-50`

```python
if tenant and tenant.status == TenantStatus.ACTIVE:
    request.state.tenant_context = TenantContext(tenant=tenant)
else:
    request.state.tenant_context = None  # But request continues!
```

If tenant is SUSPENDED/DELETED, context is `None` but **request still processes**. Downstream code must check `context is not None`. Missing check = potential access to suspended tenant data.

**Fix:** Middleware should return 403 immediately for non-ACTIVE tenants, or enforce at DB level via RLS.

---

## 3. Query-Level Isolation

### BaseModelMixin (`tenancy/models.py:15-25`)

```python
class BaseModelMixin:
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
```

All tenant-scoped models inherit this mixin. Queries **must** filter by `tenant_id`.

### TenantAwareQuery (`tenancy/query.py:10-40`)

```python
class TenantAwareQuery(Query):
    def __init__(self, *args, **kwargs):
        self._tenant_id = kwargs.pop("_tenant_id", None)
        super().__init__(*args, **kwargs)
    
    def _compile_context(self, *args, **kwargs):
        if self._tenant_id:
            # Auto-filter entities with tenant_id column
            for entity in self._entities:
                if hasattr(entity.entity_zero, "tenant_id"):
                    self = self.filter(entity.entity_zero.tenant_id == self._tenant_id)
        return super()._compile_context(*args, **kwargs)
```

**Usage:** `db.query(Model, _tenant_id=tenant_id).all()`

### Issues

#### MT-003: No Enforcement of Tenant Filter — Opt-In Only
**Severity:** CRITICAL  
**Location:** Throughout codebase

**Tenant filtering is NOT automatic** — developers must remember to:
1. Use `TenantAwareQuery` with `_tenant_id`
2. Or manually add `.filter(Model.tenant_id == tenant_id)`
3. Or use `get_tenant_context` dependency which provides `tenant_id`

**Evidence:** Multiple query patterns in codebase:
```python
# Pattern A: Explicit filter (correct)
db.query(Order).filter(Order.tenant_id == tenant_id).all()

# Pattern B: TenantAwareQuery (correct if used)
db.query(Order, _tenant_id=tenant_id).all()

# Pattern C: NO FILTER (VULNERABLE)
db.query(Order).all()  # Returns ALL tenants' orders!
```

**Search results:** Found ~15 query locations without explicit tenant filter in operations, payments, subscriptions modules.

**Impact:** Single missed filter = cross-tenant data leak.

**Fix:** Implement **database-level RLS** as mandatory backstop.

---

#### MT-004: TenantAwareQuery Not Used Consistently
**Severity:** HIGH  
**Location:** `tenancy/query.py` vs actual usage

`TenantAwareQuery` class exists but is **not the default query class**. Sessions use standard `Query`. Must explicitly opt-in.

**Fix:** Make `TenantAwareQuery` the default session query class, or better — use RLS.

---

#### MT-005: Raw SQL / ORM Bypass Possible
**Severity:** MEDIUM  
**Location:** Any service using `db.execute(text("..."))`

Raw SQL queries bypass ORM filters entirely. No tenant_id injection.

```python
# Vulnerable:
db.execute(text("SELECT * FROM orders WHERE status = 'PENDING'"))
# Returns all tenants' pending orders
```

**Fix:** Ban raw SQL for tenant-scoped data; use ORM with RLS.

---

## 4. Database Row-Level Security (RLS) — MISSING

### Current State: **NO RLS POLICIES DEFINED**

```sql
-- What SHOULD exist but DOESN'T:
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY orders_tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Set per-connection:
SET app.current_tenant_id = 'tenant-uuid-here';
```

### Why RLS is Critical

| Layer | Protection | Bypass Risk |
|-------|------------|-------------|
| Middleware | Header/JWT validation | Header spoofing (MT-001) |
| Dependency | TenantContext + permissions | Missing dependency |
| ORM Filter | Query-level filter | Forgotten filter (MT-003) |
| **RLS** | **Database-enforced** | **Cannot bypass from app** |

### Required RLS Implementation

```sql
-- 1. Enable RLS on all tenant-scoped tables
ALTER TABLE restaurant_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff_memberships ENABLE ROW LEVEL SECURITY;
-- ... all tables with tenant_id

-- 2. Create policies
CREATE POLICY tenant_isolation ON restaurant_tables
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- 3. Platform admin bypass (for platform realm)
CREATE POLICY platform_admin_bypass ON restaurant_tables
    USING (current_setting('app.is_platform_admin', true)::boolean = true);

-- 4. Connection setup in SQLAlchemy
# tenancy/session.py
@event.listens_for(Engine, "connect")
def set_tenant_context(dbapi_connection, connection_record):
    # Called when connection checked out from pool
    pass

# In request middleware:
with db.begin():
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": str(tenant_id)})
    # All queries in this transaction auto-filtered
```

---

## 5. Cross-Tenant Attack Vectors

### MT-006: Staff User with Multiple Memberships — Tenant Confusion
**Severity:** HIGH  
**Location:** `identity/auth.py:61-63`, `api/deps.py:79-118`

```python
# Login returns FIRST active membership only
membership = next((m for m in user.memberships if m.status == "ACTIVE"), None)
```

User with memberships in Tenant A (WAITER) and Tenant B (OWNER) gets Tenant A by default. Can they switch? **No tenant switching mechanism exists.**

**But:** If they craft request with `x-tenant-id: Tenant-B` + valid JWT for Tenant-A... middleware accepts header (MT-001) → cross-tenant access.

**Fix:** Remove header-based tenant resolution; add explicit tenant-switch endpoint that validates membership.

---

### MT-007: Platform Admin Impersonation Not Implemented (Good)
**Severity:** INFORMATIONAL  
**Location:** N/A

Platform admins **cannot** currently impersonate staff tenants. This is good — reduces attack surface. If added later, must be heavily audited.

---

### MT-008: Public QR Endpoints — Hostname-Based Isolation
**Severity:** MEDIUM  
**Location:** `hostname.py:30-80`, `qr/router.py:15-40`

QR ordering uses **subdomain-based tenant resolution**:

```python
# hostname.py
def resolve_tenant_from_hostname(host: str) -> UUID:
    # tenant1.platform.com → resolves tenant1
    # Maps subdomain to tenant
```

**Issues:**
1. Dev mode bypasses hostname check (AUTH-QR-004)
2. Subdomain takeover risk if DNS misconfigured
3. No rate limiting per tenant (CRIT-004)

**Fix:** Enforce hostname validation in all environments; add per-tenant rate limits.

---

### MT-009: Webhook / Callback Tenant Resolution
**Severity:** MEDIUM  
**Location:** `payments/router.py` (Stripe webhook)

Stripe webhook receives `tenant_id` in metadata. Must validate webhook signature **AND** that tenant_id matches the account.

```python
# Current: trusts metadata
tenant_id = event.data.object.metadata.get("tenant_id")
# Vulnerable if Stripe account compromised or metadata tampered
```

**Fix:** Store `stripe_account_id` per tenant; verify webhook `account` parameter matches.

---

## 6. Data Deletion / Tenant Offboarding

### MT-010: Tenant Deletion — CASCADE but No Verification
**Severity:** MEDIUM  
**Location:** `tenancy/models.py:15-25` (FK with CASCADE)

```python
tenant_id: Mapped[UUID] = mapped_column(
    ForeignKey("tenants.id", ondelete="CASCADE"),  # CASCADE DELETE
    nullable=False,
)
```

Deleting a tenant **cascades to all data** (orders, payments, menu, etc.). No:
- Soft delete / archive period
- Data export before deletion
- Confirmation workflow
- Audit log of deletion

**Fix:** Implement soft-delete (status=DELETED, deleted_at); hard delete after 90 days with export.

---

## 7. Tenant Resource Limits — MISSING

### MT-011: No Per-Tenant Resource Quotas
**Severity:** MEDIUM  
**Location:** N/A

No limits on:
- Database row counts per tenant
- API requests per tenant
- Storage usage
- Concurrent connections

One tenant's runaway process (infinite loop creating orders) can exhaust shared DB resources.

**Fix:** Implement per-tenant quotas at application level; consider PostgreSQL `ALTER ROLE ... SET statement_timeout`.

---

## 8. Recommendations Priority Matrix

| Priority | Finding | Effort |
|----------|---------|--------|
| P0 | MT-001: Remove header-based tenant resolution | 4h |
| P0 | MT-003: Implement Database RLS (critical backstop) | 16h |
| P0 | MT-006: Fix multi-membership tenant switching | 8h |
| P1 | MT-002: Middleware return 403 for non-ACTIVE tenants | 2h |
| P1 | MT-008: Enforce hostname validation in all envs | 4h |
| P1 | MT-009: Validate webhook tenant against Stripe account | 4h |
| P2 | MT-004: Make TenantAwareQuery default or remove | 4h |
| P2 | MT-005: Ban raw SQL for tenant data | 2h |
| P2 | MT-010: Soft-delete with archive period | 8h |
| P3 | MT-011: Per-tenant resource quotas | 12h |

---

## 9. Verification Test Suite

```python
# tests/test_multi_tenant.py

def test_header_tenant_id_rejected():
    """x-tenant-id header alone cannot set tenant context."""
    # 1. Login as staff in Tenant A → get token
    # 2. Request Tenant B data with header x-tenant-id: Tenant-B
    # 3. Assert: 403 or Tenant A data returned (not Tenant B)
    pass

def test_rls_enforces_isolation():
    """Database RLS prevents cross-tenant query even with raw SQL."""
    # 1. Set app.current_tenant_id = Tenant-A
    # 2. Execute: SELECT * FROM orders (no WHERE clause)
    # 3. Assert: Only Tenant-A orders returned
    pass

def test_suspended_tenant_blocked():
    """Suspended tenant returns 403 on all API calls."""
    # 1. Platform suspends tenant
    # 2. Staff makes API call with valid token
    # 3. Assert: 403 Tenant suspended
    pass

def test_multi_membership_tenant_switch():
    """User with multiple memberships can switch tenants explicitly."""
    # 1. User has memberships in Tenant A (WAITER) and Tenant B (OWNER)
    # 2. Login → gets Tenant A token
    # 4. Call POST /api/v1/auth/switch-tenant {tenant_id: Tenant-B}
    # 5. Assert: New token with Tenant-B context
    pass

def test_tenant_deletion_soft_delete():
    """Tenant deletion archives data, doesn't hard delete immediately."""
    # 1. Delete tenant
    # 2. Assert: tenant.status = DELETED, data intact
    # 3. Assert: Data export available
    pass

def test_cross_tenant_query_blocked():
    """Query without tenant filter returns empty/error, not all data."""
    # 1. Create orders for Tenant A and Tenant B
    # 2. db.query(Order).all() (no filter)
    # 3. Assert: Empty or error (RLS), NOT both tenants' orders
    pass
```

---

## Conclusion

The multi-tenant architecture relies **entirely on application-layer controls** with **no database-level enforcement**. This is a **critical architectural gap**.

**Immediate priorities:**
1. **Remove `x-tenant-id` header trust** (MT-001) — eliminates trivial cross-tenant access
2. **Implement PostgreSQL RLS** (MT-003) — mandatory defense-in-depth; cannot be bypassed by app bugs
3. **Fix multi-membership handling** (MT-006) — proper tenant switching

Without RLS, a single forgotten `.filter()` in any service = full cross-tenant data leak. RLS is not optional for a multi-tenant SaaS platform.