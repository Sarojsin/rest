# DevOps, Environments & Infrastructure

## 1. Environments

| Env | DB | Data | Deploy |
|-----|-----|------|--------|
| dev | Postgres 16 (docker-compose; **SQLite removed** D12) | seed/demo scripts | `start-dev.ps1` |
| staging | managed Postgres, prod-like config | anonymized replay of prod ×2 tenants | auto on main merge |
| prod | managed Postgres + PITR | live | tagged releases, manual approval |

Ephemeral per-PR DB instances for migration/isolation tests in CI.

## 2. Config & secrets

- All config via env + typed `core/config.py`; no secret in repo or image; separate secrets per realm (staff/customer/platform/payment/platform-billing).
- Runtime flags from §17 (`tenant_columns.*`, `platform.rls_enabled`) stored as platform config rows — ops can flip without redeploy.

## 3. CI/CD (GitHub Actions)

1. lint (ruff, mypy strict on domain/core, import-lint 02 §2) → 2. unit/api tests → 3. isolation suite (rls off/on) → 4. migration job (upgrade/down/upgrade) → 5. build images → 6. deploy staging → e2e smoke → 7. prod on approval.
- Generated clients (`packages/api-client`) regenerate on main merge; PR fails if drift committed unregenerated.

## 4. Runtime topology (pilot)

- Single API container (+workers in-process) behind reverse proxy; TLS via wildcard cert for `*.platform.com` (+ admin/customer subdomains); SSE pass-through.
- Managed Postgres 16: PITR 30d, nightly verified logical backup; connection pool sized for device fleet but SSE fan-out is app-side.

## 5. Backup & restore

- Nightly logical dump + WAL PITR; restore drill each release (Phase 10 gate): restore → isolation spot-tests → rowcount report.
- Backup retention targeting snapshots from primary region; RPO 5m (WAL), RTO 30m single-node restore.
- Ordering: dumps only after verifying post-M6 schema; legacy epoch dumps retained separately until removal.

## 6. Observability (production-grade from day one)

- Structured logs (request_id, tenant_id, branch_id, actor membership, **module name** — the module is part of the log envelope for every service call, since 02 §2.1 makes modules real boundaries); PII redaction per 19/T21.
- **Per-module telemetry:** every route/service span is tagged with `module.<name>` — so dashboards can answer "which module is slow / erroring" without any future split guesswork. Fires the extraction playbook (02 §2.6) when evidence accumulates. Backed by: per-route latency histograms tagged by module, module-scoped error counters, DB-time per module via SQLAlchemy event hooks.
- Metrics: p50/p95 per route, **per module**, outbox lag (internal handler lag included — bus stalls are module-boundary failures), SSE failures, DB pool saturation, migration lock waits, RLS var set failures, webhook latencies, usage-counter drift alerts (07 §3).
- Dashboards for platform ops (churn/subscriptions feed from 25 §6 metrics tables) separate from tenant ops analytics.
- Alerts: outbox lag >30s (internal bus or external), webhook unverified failures >5/15m, migration lock timeout, suspended-tenant spike (dunning bug smell), failed escalation timer, counter drift >0.1% (07 §3).

## 7. Mobile/store ops

- `GET /config/client-versions` for minimum-version enforcement + feature flags (16 §6).
- Release plan: staged rollout 10% → 100%; OTA (EAS update) only for JS fixes within store policy; native blockers handled by flag-gating server behavior.

## 8. DNS/TLS & hosting tasks (D5 irreversible)

- Apex + wildcard `*.platform.com` approved/registered in Phase 0; staging wildcard at `*.staging.platform.com`.
- Per-tenant subdomain DNS is dynamic (no per-tenant ops) via wildcard; custom domains deferred (23).
- Incident runbooks: DB outage, gateway outage, outbox stall, cross-tenant leak disclosure (slow: notify within statutory timelines; template text pre-written).
