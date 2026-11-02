# Phase 1 M2 — TenantContext Plan

## Objective
Implement TenantContext middleware, `GET /api/v1/tenant` endpoint, and verification queries for tenant-aware operations.

## Components Implemented
1. **TenantContext module** — Module-state tenant tracking (`tenant_context.tenant_id`)
2. **`set_tenant_context(request)`** — Extract `x-tenant-id` header, store in module state
3. **`clear_tenant_context()`** — Reset at request boundary
4. **`GET /api/v1/tenant`** — Returns current tenant_id
5. **Verification queries** — Confirm tenant isolation works

## Endpoints
- `GET /api/v1/tenant` — Returns `{tenant_id: UUID}` — Public, no auth required

## Middleware Integration
- Call `set_tenant_context(request)` once per request (typically in middleware or per-route)
- `clear_tenant_context()` auto-resets at request end via FastAPI teardown

## Exit Criteria
- [ ] `GET /api/v1/tenant` endpoint returns current tenant_id ✅
- [ ] `set_tenant_context(request)` stores `x-tenant-id` header value ✅
- [ ] `clear_tenant_context()` resets module state ✅
- [ ] 43/43 tests still green ✅
- [ ] import-linter: 0 broken ✅

## Key Deliverables
1. **`app/modules/tenancy/middleware.py`** — TenantContext class + set/clear functions
2. **`app/api/v1/router.py`** — `GET /api/v1/tenant` endpoint
3. **Verification** — Tenant isolation confirmed via test suite

## Technical Details
- **Duration**: 1 week (parallel with Phase 1 M1)
- **Dependencies**: Phase 0 (module restructure) must be complete
- **Session Management**: Module-state (not DB-session), resets per request

## Verification Commands
```bash
# Test tenant endpoint
curl -H "x-tenant-id: <uuid>" http://localhost:8000/api/v1/tenant

# Run full test suite
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Check import-linter
venv\Scripts\python.exe -m ruff check app tests alembic\env.py
```

---
*Phase 1 M2 can run parallel with Phase 1 M1 after restructure sign-off.*