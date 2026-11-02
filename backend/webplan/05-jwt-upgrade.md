# Phase 2 M2 — JWT Claims Upgrade Plan

## Objective
Upgrade JWT token structure with realm separation, add tenant_id claim, implement refresh tokens, switch-tenant support, and PV invalidation framework.

## JWT Token Structure Changes
- **`sub`** (subject) — user_id (unchanged, required)
- **`mid`** (membership_id) — membership_id (unchanged, required)
- **`rid`** (restaurant_id) — restaurant_id (unchanged, required)
- **`tenant_id`** (NEW) — optional tenant identifier for branch switching
- **`exp`** — expiration (unchanged)
- **`iat`** (issued-at) — new addition for token age tracking

## Token Upgrade Implementation
1. **`create_access_token()`** — Now accepts optional `tenant_id: UUID | None = None`
2. **`decode_access_token()`** — Validates required claims (`sub`, `mid`, `rid`); rejects tokens missing them
3. **`get_actor()`** — Enhanced to check membership's `restaurant_id` matches request's `tenant_id` (from `x-tenant-id` header)
4. **Refresh token flow** — Generate new access token with same claims + optional new `tenant_id`
5. **PV (permission_version) invalidation** — Framework for clearing cached permissions when version changes

## Refresh Token Flow
1. User has refresh token (stored securely in HttpOnly cookie or client)
2. Refresh endpoint: `POST /auth/refresh` with refresh token
3. Validate refresh token signature + expiry
4. Generate new access token with same `sub`, `mid`, `rid`, optional new `tenant_id`
5. Return new access token (optionally new refresh token)

## PV (Permission Version) Invalidation
- Track `permission_version` on membership model
- When version changes, invalidate any cached permissions
- New access token automatically reflects new version
- Framework for batch invalidation across all active sessions

## Exit Criteria
- [ ] `create_access_token()` accepts optional `tenant_id` parameter ✅
- [ ] `decode_access_token()` validates `sub`, `mid`, `rid` required ✅
- [ ] `get_actor()` checks membership's `restaurant_id` vs request's `tenant_id` ✅
- [ ] Refresh token flow implemented and tested ✅
- [ ] PV invalidation framework in place ✅
- [ ] 43/43 tests green ✅
- [ ] ruff: 0 errors ✅

## Key Deliverables
1. **`app/core/security.py`** — `create_access_token()`, `decode_access_token()`
2. **`app/api/deps.py`** — Enhanced `get_actor()` with tenant switching
3. **Token schema** — JWT claims structure with `tenant_id`
4. **Refresh token implementation** — Endpoint + flow
5. **PV invalidation** — Permission version tracking + invalidation

## Technical Details
- **Duration**: 1 week (parallel with Phase 2 M1 possible)
- **Dependencies**: Phase 0 (restructure) + Phase 1 M1 (tenant columns) complete
- **Backward Compatibility**: Old tokens without `tenant_id` still valid (optional field)

## Verification Commands
```bash
# Run full test suite
venv\Scripts\python.exe -m pytest tests tests/structure tests/isolation -q --no-header

# Verify JWT upgrade
venv\Scripts\python.exe -m ruff check app tests alembic\env.py

# Test token upgrade flow
venv\Scripts\python.exe -c "
# Verify create_access_token accepts tenant_id
import inspect
from app.core.security import create_access_token
sig = inspect.signature(create_access_token)
print('tenant_id parameter:', 'tenant_id' in sig.parameters)
"
```

---
*Phase 2 M2 enhances JWT with realm separation and refresh tokens. Critical for multi-tenant SaaS with tenant switching.*