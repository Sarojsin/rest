# Testing Strategy

## 1. Test pyramid & owners

| Layer | Where | What |
|-------|-------|------|
| Unit (domain) | `backend/tests/` (existing suites extend) | state machines, money math, entitlement merge, menu resolution |
| API contract | `backend/tests/test_api*.py` extended | endpoint behavior per 14, status-codes, error-code catalog |
| **Tenant isolation suite (merge-blocking)** | `backend/tests/isolation/` | the cross-tenant matrix below |
| **Module isolation suite (merge-blocking, D14)** | `backend/tests/modules/` | import-linter contracts (02 §2.1, 21 §10.2), per-module runs, event contract tests (§4 below) |
| RLS double-run | tenant-isolation suite, parametrized `rls=off/on` | proves L2/L3 and L5 independently |
| Migration tests | CI ephemeral Postgres | `upgrade → downgrade → upgrade`; backfill parity checks |
| E2E smoke (small set) | one happy-path per surface (order→serve→bill→pay) | guardrail, not substitute |
| Frontend/mobile | Vitest + React Testing Library; API mocked | context-switch cache clearing, error-code screens |

**Two suites, two guarantees:** tenant isolation (cannot see another tenant's data) and module isolation (`kitchen` cannot reach around operations' interface). The former protects customers; the latter protects the architecture's extractability promise (D14). Neither substitutes for the other; both gates block merges.

## 2. The tenant isolation matrix (generated, not hand-written)

For **every** protected endpoint across A/B tenants + their actors (staff-A, staff-B, customer-A, platform-admin):

1. A reads B's resource → **404** (not 403)
2. A mutates B's resource (valid guessed UUID) → 404
3. A's QR (branch/table A) touching branch B id → 404 + no data echo
4. Platform admin can reach both (expected-loud, audited)
5. WS topics: A subscribed session never receives B events
6. Idempotency key from A replays into B scope → not applied (unique scope separately)
7. Audit log of A never includes B entries
8. Search/list endpoints return only A's objects (no existence leak through sorting/filtering)

Fixture: `two_tenants_full` (two tenants × two branches each × seeded menus/tables/orders/bills), built via service layer only (no raw inserts) so fixture drift impossible. New endpoint ⇒ test auto-generated from route manifest; an endpoint lacking isolation coverage fails CI (route manifest is complete by construction).

## 3. Structural discipline assertions (cheap but catch the classic sins)

- Every `repositories/` function signature contains `ctx: TenantContext` (unit test introspecting modules; `02 §4`).
- Every route dependency chain includes realm middleware + `require_permission` (route manifest check; failing lint for unprotected routes).
- Every tenant table per 03 §4 classification exists in `rls_manifest.py` or the allowlist (04 §5).

## 4. Module isolation & event contract tests (D14/D15 — merge-blocking)

1. **Import graph:** import-linter runs as its own CI job with the forbidden/layered contracts from `02 §2.1` + `21 §10.2` — any `modules/A → modules/B.repositories|models` or `modules/* → api` import fails the merge with a readable diff. (Not a "best effort" lint; a build gate.)
2. **Per-module test runs:** each `backend/tests/modules/<name>/` suite imports *only* the module under test (+ shared/); a conftest guard fails the suite if any sibling module is imported. This proves modules run in isolation — the executable version of the extraction playbook.
3. **Internal event contract tests:** for each entry in the 13 §0 catalog: emit the event (via the emitting module's public service in a real transaction), run the dispatcher once, assert each registered consumer produced its expected effect (e.g., `order.accepted` ⇒ kitchen ticket exists; `order.completed` ⇒ bill affordance flips) *within the consuming module*, and idempotency (re-delivery of the same `event_id` produces no second effect).
4. **No-cross-repo behavioral test:** for each module, a test that exercises its public interface with the sibling repositories' modules' imports blocked at runtime (patch-guard) — belt to the import-linter suspenders.
5. **Worker/scheduler seam test (04 §8):** the dispatcher processing tenant A's events never touches tenant B; scheduler jobs call only public interfaces (asserted by monkeypatching repositories to raise-import-if-called).

## 5. Auth tests

- Token realm crossover rejected (`REALM_MISMATCH`); tenant-switch validation; pv bump invalidates live tokens within request; refresh-family reuse detection triggers revocation; suspension revokes sessions; QR token rotation kills sessions.

## 6. Migration & dual-write tests

Ephemeral Postgres per run: `alembic upgrade head → alembic downgrade base → upgrade`; assert row-preservation on downgrades where designed; assert CONCURRENTLY-indexed migrations run with lock-timeout (guarded by `SET lock_timeout='5s'`).
**M3 dual-write window rule:** every dual-write migration change (17 §M3) keeps the tenant isolation matrix green *before and after* in the same CI run; a dual-write commit whose matrix breaks anywhere is unmergeable — the M3 window is the riskiest migration period, so its gate is absolute.

## 7. Performance smoke (Phase 10 gate, `22`)

- 100 tenants / 500 concurrent staff / 10k QR orders-hr synthetic load (locust script in `backend/locust/`); p95 on endpoints under isolation gates must remain <200ms pre-scale decisions.

## 8. Demo tenant & fixtures (24 §5)

- `two_tenants_full` marks tenant1.is_demo true to exercise exclusion paths in analytics/billing APIs.
- Demo reset job isolation: the nightly scheduler reset (24 §4) is tested as a worker-seam test (§4.5) — it sets `app.current_tenant_id` per transaction (RLS-scoped, not exempt) and, if it ever uses the bypass role, asserts a `platform_audit_logs` entry exists.

## 9. Run gates summary

Merging main requires: lint+typecheck, **import-lint (module contracts)**, unit, api, **tenant isolation (rls off)**, tenant isolation (rls on, from M5), **module isolation + event contract tests**, migration job, e2e smoke. No endpoint skips the matrix; no module skips the import cons; failing any gate = no merge.
