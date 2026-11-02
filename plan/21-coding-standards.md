# Coding Standards (Senior-Level Conventions)

How code is written so the architecture (02) is real, not aspirational. Enforced by lint rules where possible.

## 1. The context rule

```python
# ❌ NEVER in repositories — a repo without ctx can leak tenants
async def get_order(db, order_id): ...

# ✅ ctx is mandatory; scoping is part of the signature
async def get_order(db: Session, ctx: TenantContext, order_id: UUID) -> Order | None:
    stmt = select(Order).where(Order.id == order_id, Order.tenant_id == ctx.tenant_id)
    if ctx.is_branch_scoped:
        stmt = stmt.where(Order.branch_id.in_(ctx.branch_ids))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None: return None
    assert row.tenant_id == ctx.tenant_id          # L3 double-check; cheap
    return row
```

Rule set (CI-enforced via signature introspection test, 18 §3): every repo fn takes `ctx`; every repo SELECT filters tenant; services receive ctx (never request objects); services re-verify ownership before mutation (L3); no service does raw SQL outside repositories.

## 2. Layering (02 §2 import-lint)

`api → services → repositories → models`. DTO boundaries: routes parse Pydantic input; repos return models; services return domain objects; routes serialize explicitly (no `from_orm` surprises on relations).

## 3. Error handling

```python
class PlatformError(Exception):
    code: str; http_status: int; details: dict
class EntitlementExceeded(PlatformError):   # raises with details per 07 §2
    code = "ENTITLEMENT_EXCEEDED"; http_status = 409
```

- Services raise typed subclasses; one global handler maps to API error bodies (14 §4). No bare `HTTPException` in services; route handlers only reorder/serialize.
- Errors never leak internals: details whitelist per exception; log with stack + request_id; response sanitized.

## 4. Money & time

- Money everywhere in minor units + currency triple; `services/money.py` is the only place decimals exist (existing module, extended).
- Quantities: integers (portions) unless validated need (schema.md 5.2 note preserved).
- Time: aware datetimes only; tenant/branch timezone resolved via `ctx.tenant_timezone`/branch timezone; `now(tz)` helpers; **no naive `datetime.now()` anywhere in `backend/` (lint rule)**.

## 5. API surface hygiene

- Route manifests declare: realm, permission, `public: bool`, idempotent scope, response models — single source of truth also consumed by isolation-test generator (18 §2) and OpenAPI.
- Mutation POSTs accept `Idempotency-Key`; replay returns same result with marker header (`IDEMPOTENT_REPLAY`, 21 §7 / 14 §6).
- Deprecations in code explicit (`deprecated=True` in decorator) so OpenAPI + Deprecation-header generate together.

## 6. Transactions & side effects

One transaction per business operation (`02 §4` sequence). Side effects (outbox rows, audit rows) written inside the same transaction — commit is the guarantee; external calls (gateways, email) happen **post-commit** via worker/admin post-commit hooks, never inside.

## 7. Idempotency & optimistic concurrency

- Idempotency ledger store `(branch_id, scope, key, request_fingerprint)`; on replay with same fingerprint → replay stored response; different → `409 IDEMPOTENT_CONFLICT`.
- Aggregates (bill, order) carry `version`; `UPDATE ... WHERE version = n` inside tx; mismatch ⇒ `CONCURRENT_MODIFICATION` (14 §4).

## 8. Naming/config discipline

- Module names single words where possible (`tenancy`, `menu`, `billing`...); service fn names verb-first; JSONB config keys snake_case with Pydantic validation at edges (03 §5.3).
- No magic strings: permission codes, error codes, event topics, roles are enum constants in `core/constants.py` (grep-able, typed).
- Feature flags: runtime config rows, accessed via injected `Flags` service, defaults fail-closed for platform, fail-open only where D9 soft limits dictate.

## 9. Frontend/mobile mirror rules

- React Query keys factory `(tenantId, branchId, ...resource)`; context switch clears (15 §2 is a code-level fixture test in frontend tests).
- Error screens keyed on `code` constants (shared with backend via generated constants package — `packages/api-client`).
- Types generated from OpenAPI; hand-written API types disallowed (lint).

## 10. Module boundaries (D14 — first-class norm, referenced by 02 §2.1)

### 10.1 Ownership rule (restated as code contract)

Every table has exactly one owning module. Anyone else reads via the owner's public service interface. Example:

```python
# ❌ kitchen module reading operations tables directly (forbidden by import-linter)
from app.modules.operations.repositories import get_order      # import-lint FAILURE

# ✅ kitchen consumes operations' public interface
from app.modules.operations import services as operations      # public iface
order = await operations.get_order_for_kitchen(db, ctx, order_id)
```

Public interface = `modules/<x>/services/__init__.py` exports (no `_` prefix). Everything else is private by convention AND by import-lint `forbidden` contract from siblings.

### 10.2 Import-linter config (checked into repo, CI-blocking)

```ini
; pyproject.toml [tool.importlinter] (excerpt — full file in repo root)
[importlinter:root_package]
root = app

[importlinter:contract:api_composition]
name = api modules compose services only
type = layers
layers =
    app.api | app.workers
    app.modules.*.services
    app.modules.*.repositories
    app.modules.*.models

[importlinter:contract:no_cross_module_repositories]
name = modules never import sibling repositories
type = forbidden
source_modules = app.modules
forbidden_modules = app.modules.*.repositories, app.modules.*.models
# enforced pairwise (source = each module separately)

[importlinter:contract:shared_is_kernel]
name = shared/ imported by all, imports no domain
type = independence
modules = app.shared
```

CI job `make import-lint` (20 §3) fails the merge; the same graph feeds the per-module test guard (18 §4.2).

### 10.3 Adding a new module (checklist)

1. Decide table ownership (one owner; update 02 §2.2 table + `docs/schema.md`).
2. Create `modules/<name>/{models,schemas,repositories,services,router,events}.py`; services expose the public iface in `__init__.py`.
3. Register events it emits/consumes in the 13 §0 catalog + `shared/events.py`.
4. Add module to import-linter pairwise matrix (mechanical — list-based).
5. RLS-manifest entry + isolation-allowlist decision (03 §5.1, 04 §5).
6. Route manifest entry: realm, permission, public/idempotent scopes (21 §5).
7. Per-module test dir + at least one event contract test if events exist (18 §4.3).
8. Update observability envelope (module tag) — free via decorator.

### 10.4 Extracting a module (checklist — the monolith's honest escape hatch)

1. Consult 02 §2.6 difficulty + prereqs; write ADR (23 §4) with read-model plan.
2. First step is always interface-hardening: no consumer bypasses the public iface (import-lint + per-module test prove it).
3. Replace in-process service calls across the boundary with the bus (D15) where latency allows.
4. Then: separate process / separate DB *only when* a real driver exists (fault isolation, compliance, scale) — otherwise stop; free architecture wins are real.

### 10.5 The scheduler exclusion zone (02 §2.5, 04 §8)

`workers/` is a composition-layer like `api/`: calls public interfaces only; repositories/models imports are white-list-forbidden by the same import-linter contract (source = app.workers). No exceptions without ADR.

## 12. Review checklist per PR (unchanged — merged from prior §10)

1. refs a `22-phase-roadmap.md` task  2. tenant scoping via ctx only  3. permission on route  4. errors use code catalog  5. side effects in-tx/out-of-tx correct  6. money/time helpers used  7. new table in manifests (03/04/18)  8. tests updated including isolation matrix hit.
