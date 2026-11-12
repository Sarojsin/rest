# Remediation Plan — Restaurant SaaS Platform Security Audit

**Classification:** CONFIDENTIAL  
**Version:** 1.0  
**Date:** 2026-11-09  

---

## Executive Summary

This plan prioritizes remediation of **46 findings** across 9 audit domains. Findings are classified by **severity (CVSS 4.0)** and **exploitability**, then sequenced by **dependency order** (fixes that unblock other fixes come first).

**Total Estimated Effort: ~140 hours** (3.5 weeks for 1 engineer, or 1 week with 4 engineers parallelized)

**Critical Path:** CRIT-002 → CRIT-003/CRIT-004 → INFRA-001 → All other fixes

---

## 1. Severity Distribution

| Severity | Count | Examples |
|----------|-------|----------|
| **CRITICAL** | 4 | CORS wildcard+credentials, Secrets in Git, In-memory lockout, No rate limiting |
| **HIGH** | 15 | MANAGER→OWNER escalation, No refresh tokens, 8hr token expiry, No RLS, No TLS, No backups |
| **MEDIUM** | 22 | Weak dev keys, Support PII access, QR token binding, Missing security headers |
| **LOW** | 8 | Debug logging, No code obfuscation, No SBOM |
| **INFORMATIONAL** | 15 | Dev mode hostname bypass, No break-glass, No field-level permissions |

---

## 2. Phase 0: Immediate (Day 0-1) — "Stop the Bleeding"

**Goal:** Eliminate active exploitation vectors. **No code changes to app logic** — only configuration, secrets, infrastructure.

| ID | Finding | Action | Owner | Hours | Verification |
|----|---------|--------|-------|-------|--------------|
| **P0-1** | CRIT-002: Secrets in Git | 1. Generate ALL new secrets (SECRET_KEY, PLATFORM_SECRET_KEY, PLATFORM_MFA_KEY, SMTP password, DB password, JWT keys) 2. Rotate in production 3. Remove `.env` from Git history (`git filter-repo`) 4. Add `.env` to `.gitignore` | SecOps + Backend | 2 | `git log --all -- backend/.env` empty; new secrets work; old tokens invalid |
| **P0-2** | CRIT-001: CORS Wildcard | 1. Set `CORS_ORIGINS` to explicit production domains 2. Remove `allow_credentials=True` OR restrict origins 3. Deploy config change | Backend | 1 | `curl -H "Origin: https://evil.com" -H "Cookie: x=y" /api/...` → no ACAO reflection |
| **P0-3** | INFRA-NET-001: No TLS | 1. Provision certs (Let's Encrypt / ACM) 2. Configure Nginx/Traefik TLS termination 3. Redirect HTTP→HTTPS 4. Set `Secure` cookie flag | DevOps | 4 | `curl -I https://api.prod.com` → HSTS, valid cert |
| **P0-4** | INFRA-DR-001: No Backups | 1. Provision managed PostgreSQL (RDS/Cloud SQL/Azure PG) 2. Enable automated backups (7-day retention) 3. Enable point-in-time recovery 4. Test restore to staging | DevOps | 8 | Restore test succeeds; PITR works |

**Phase 0 Total: ~15 hours** — **MUST COMPLETE BEFORE ANY OTHER WORK**

---

## 3. Phase 1: Foundation (Week 1) — Infrastructure & Core Security

**Goal:** Deploy Redis, enable RLS, fix auth infrastructure. These unblock Phase 2.

| ID | Finding | Action | Owner | Hours | Dependencies | Verification |
|----|---------|--------|-------|-------|--------------|--------------|
| **P1-1** | INFRA-001: No Redis/Postgres in Compose | 1. Add `postgres`, `redis` to `docker-compose.prod.yml` 2. Configure connection pooling 3. Add healthchecks 4. Update `config.py` to use `REDIS_URL` | DevOps | 4 | P0-4 | `docker compose -f docker-compose.prod.yml up` → all healthy |
| **P1-2** | CRIT-003: In-Memory Lockout | 1. Implement Redis-backed lockout store (`security.py`) 2. Add `redis` dependency to `pyproject.toml` 3. Configure `LOCKOUT_PREFIX`, TTL 4. Add integration tests | Backend | 4 | P1-1 | Lockout persists across worker restarts; 5 attempts → 15min lock |
| **P1-3** | CRIT-004: No Rate Limiting | 1. Implement `RateLimitMiddleware` (Redis token bucket) 2. Add rules for: login, MFA, refresh, QR, webhooks 3. Return `429` with `Retry-After` 4. Add per-endpoint `Depends(rate_limit(...))` | Backend | 6 | P1-1 | 6th login attempt → 429; MFA brute force blocked |
| **P1-4** | MT-003: No Database RLS | 1. Enable RLS on all tenant tables 2. Create policies: `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)` 3. Add connection hook to set `app.current_tenant_id` per request 4. Test cross-tenant query blocked | Backend + DBA | 16 | P1-1 | `SELECT * FROM orders` (no WHERE) → only current tenant rows |
| **P1-5** | MT-001: Header-Based Tenant Trust | 1. Remove `x-tenant-id` header resolution from middleware 2. Derive tenant ONLY from validated JWT 3. Add explicit tenant-switch endpoint with membership check | Backend | 4 | P1-4 | Header `x-tenant-id: other-tenant` → ignored; 403 |
| **P1-6** | AUTH-STAFF-001/002: No Refresh Tokens + 8hr Expiry | 1. Add `StaffRefreshToken` model (family-based, rotating) 2. Reduce access token to 15 min 3. Implement refresh endpoint + rotation + reuse detection 4. Update mobile/web token storage | Backend | 8 | P1-2, P1-3 | Token refresh works; reuse → family revoked; 15min expiry |
| **P1-7** | INFRA-002: Harden Dockerfiles | 1. Multi-stage builds 2. Non-root user 3. Read-only fs, drop caps 4. Distroless/slim base | DevOps | 4 | P1-1 | `docker run --read-only --cap-drop=ALL` works |

**Phase 1 Total: ~46 hours** — **CAN PARALLELIZE: P1-1/P1-7 (DevOps), P1-2/P1-3/P1-6 (Backend), P1-4/P1-5 (Backend+DBA)**

---

## 4. Phase 2: Authentication & Authorization Hardening (Week 2)

**Goal:** Fix auth gaps, RBAC escalation, MFA, QR security.

| ID | Finding | Action | Owner | Hours | Dependencies | Verification |
|----|---------|--------|-------|-------|--------------|--------------|
| **P2-1** | RBAC-STAFF-002: MANAGER→OWNER | 1. Add role hierarchy validation in staff service 2. `require_permission` checks `requester_role >= target_role` 3. Unit tests for escalation attempts | Backend | 4 | P1-6 | MANAGER creates OWNER → 403 |
| **P2-2** | RBAC-PLAT-006: Bootstrap SUPERADMIN No MFA | 1. On first login, require MFA enrollment before any admin access 2. Add `mfa_enrolled` check to `get_current_platform_admin` 3. Redirect to enrollment if missing | Backend | 2 | P1-6 | New SUPERADMIN login → 403 MFA_REQUIRED until enrolled |
| **P2-3** | AUTH-STAFF-004: No Staff MFA | 1. Add TOTP to `StaffUser` model 2. Enforce for OWNER/MANAGER roles 3. Add enrollment/verification endpoints 4. Update mobile/web for MFA flow | Backend + Mobile + Web | 12 | P1-6 | OWNER login → MFA challenge; WAITER no MFA |
| **P2-4** | AUTH-QR-001: Status Token Binding | 1. On first use, bind `status_token` to client fingerprint (IP+UA hash) 2. Reject subsequent requests with different fingerprint 3. Rotate token on each status check | Backend | 4 | P1-4 | Status token from different IP → 403 |
| **P2-5** | AUTH-QR-003: No QR Rate Limiting | 1. Add per-QR-token rate limits (10 orders/5min, 60 menu/min) 2. Use Redis sliding window | Backend | 2 | P1-3 | 11th order in 5min → 429 |
| **P2-6** | RBAC-PLAT-003: OPS Unilateral Suspend | 1. Require SUPERADMIN approval for suspension 2. Add `SuspensionRequest` model + workflow 3. Notify tenant OWNER | Backend | 4 | P1-6 | OPS suspend → pending; SUPERADMIN approves → executed |
| **P2-7** | RBAC-PLAT-004: Unlimited Refunds | 1. Add refund limits: $500/txn, $2000/day per BILLING user 2. SUPERADMIN override 3. Alert on limit approach | Backend | 3 | P1-6 | BILLING refund >$500 → 403 |
| **P2-8** | API-QR-002: QR Token in URL | 1. Move sensitive ops (cancel, rate) to POST with token in body 2. Keep menu GET but add `Referrer-Policy: no-referrer` | Backend | 2 | P1-3 | Referer header doesn't contain QR token |
| **P2-9** | API-WEB-001: Webhook Replay | 1. Store processed `event.id` in Redis (30-day TTL) 2. Reject duplicates before processing | Backend | 2 | P1-1 | Same Stripe event delivered twice → 2nd rejected |

**Phase 2 Total: ~39 hours** — **PARALLELIZE: P2-1/P2-6/P2-7 (Backend), P2-3 (Full stack), P2-4/P2-5/P2-8/P2-9 (Backend)**

---

## 5. Phase 3: Application Security (Week 2-3)

**Goal:** API hardening, mobile security, frontend fixes.

| ID | Finding | Action | Owner | Hours | Dependencies | Verification |
|----|---------|--------|-------|-------|--------------|--------------|
| **P3-1** | API-VAL-001: Request Size Limits | 1. Add `RequestSizeLimitMiddleware` (1MB default) 2. Configurable per endpoint | Backend | 1 | P1-3 | 2MB payload → 413 |
| **P3-2** | Security Headers | 1. Add `SecurityHeadersMiddleware` (CSP, HSTS, X-Frame, etc.) 2. Test CSP doesn't break frontend | Backend + Web | 2 | P0-3 | All responses have headers |
| **P3-3** | API-ERR-001: Dev Stack Traces | 1. Remove traceback from production error responses 2. Log full trace server-side only | Backend | 1 | — | 500 response → no `traceback` field |
| **P3-4** | API-DOC-001: Swagger in Prod | 1. Disable `/docs`, `/redoc`, `/openapi.json` in production 2. Or protect with auth | Backend | 1 | — | `GET /docs` → 404 in prod |
| **P3-5** | MOB-004: Certificate Pinning | 1. Configure `expo-network` pinning in `app.json` 2. Add backup pins 3. Test cert rotation procedure | Mobile | 4 | P0-3 | Wrong cert → connection fails |
| **P3-6** | MOB-008: Biometric Auth | 1. Add `expo-local-authentication` 2. Prompt on app unlock (5min background) 3. Fallback to passcode | Mobile | 6 | P1-6 | Background 6min → biometric prompt |
| **P3-7** | MOB-009: App Lock | 1. `AppState` listener + timeout 2. Clear sensitive state on lock | Mobile | 4 | P3-6 | Background 5min → locked |
| **P3-8** | Web: HttpOnly Cookies for Staff | 1. Move staff token from `sessionStorage` to HttpOnly cookie 2. Add CSRF protection 3. Update `api.ts` interceptor | Web | 6 | P1-6 | XSS cannot steal token |
| **P3-9** | Web: Permission Checks | 1. Verify `hasPermission()` matches backend 2. Add E2E tests for RBAC | Web | 4 | P2-1 | MANAGER UI hides OWNER-only actions |

**Phase 3 Total: ~31 hours** — **PARALLELIZE: P3-1/P3-2/P3-3/P3-4 (Backend), P3-5/P3-6/P3-7 (Mobile), P3-8/P3-9 (Web)**

---

## 6. Phase 4: Infrastructure & Operations (Week 3)

**Goal:** CI/CD, monitoring, backups, incident response.

| ID | Finding | Action | Owner | Hours | Dependencies | Verification |
|----|---------|--------|-------|-------|--------------|--------------|
| **P4-1** | INFRA-CI-001: Security Scanning | 1. Add Trivy, Gitleaks, Bandit to CI 2. Fail on CRITICAL/HIGH 3. Add Dependabot | DevOps | 6 | — | PR with vulnerability → blocked |
| **P4-2** | INFRA-CI-002: Deployment Automation | 1. GitHub Actions → staging → production 2. Blue/green or canary 3. Automated rollback on health check fail 4. Post-deploy smoke tests | DevOps | 16 | P4-1 | `main` push → staged; manual promote → prod |
| **P4-3** | INFRA-OBS-001: Prometheus Metrics | 1. Add `prometheus-fastapi-instrumentator` 2. Custom business metrics 3. `/metrics` endpoint | Backend | 4 | P1-1 | `curl /metrics` → latency, errors, orders |
| **P4-4** | INFRA-OBS-002: Centralized Logging | 1. JSON structured logs 2. Ship to Loki/ELK 3. Retention: 90 days | DevOps | 6 | P1-1 | Query logs by `request_id`, `tenant_id` |
| **P4-5** | INFRA-OBS-004: Alerting | 1. Alertmanager rules: error rate >1%, p99 >2s, disk >80% 2. PagerDuty/Slack integration | DevOps | 8 | P4-3 | Alert fires on synthetic load test |
| **P4-6** | INFRA-SEC-001: Secrets Manager | 1. Integrate AWS Secrets Manager / Azure Key Vault 2. Inject at container startup 3. Remove all `env_file` usage | DevOps | 8 | P0-1 | No secrets in env; rotation works |
| **P4-7** | INFRA-DR-002: Incident Response | 1. Document IR plan (roles, contacts, runbooks) 2. Tabletop exercise 3. Update annually | SecOps | 8 | — | IR plan reviewed; exercise completed |

**Phase 4 Total: ~56 hours** — **PARALLELIZE: P4-1/P4-2 (DevOps), P4-3/P4-4/P4-5 (DevOps+Backend), P4-6 (DevOps), P4-7 (SecOps)**

---

## 7. Phase 5: Advanced Hardening (Post-Launch)

**Goal:** Defense-in-depth, compliance, advanced threats.

| ID | Finding | Action | Owner | Hours |
|----|---------|--------|-------|-------|
| **P5-1** | Immutable Audit Trail | Hash-chained audit logs + WORM storage | Backend | 12 |
| **P5-2** | Break-Glass Procedure | Time-limited emergency access + mandatory review | Backend | 8 |
| **P5-3** | Per-Tenant Quotas | Row counts, API rate limits, storage | Backend | 12 |
| **P5-4** | Field-Level Permissions | Attribute-based access for PII | Backend | 16 |
| **P5-5** | RASP / Mobile Anti-Tamper | `react-native-rasp`, jailbreak/root detection | Mobile | 8 |
| **P5-6** | mTLS Service Mesh | Istio / Linkerd for internal encryption | DevOps | 24 |
| **P5-7** | SBOM + Supply Chain | `syft` in CI, SLSA provenance | DevOps | 8 |
| **P5-8** | Penetration Test | Annual third-party pentest | SecOps | 40 |

**Phase 5 Total: ~128 hours** — **ONGOING / POST-MVP**

---

## 8. Resource Allocation (4 Engineers)

| Role | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|---------|
| **Backend Engineer 1** | P0-2 | P1-2, P1-3 | P2-1, P2-6, P2-7 | P3-1, P3-2, P3-3, P3-4 | P4-3 |
| **Backend Engineer 2** | P0-1 | P1-6 | P2-3, P2-4, P2-5, P2-9 | P3-8, P3-9 | P4-6 |
| **DevOps Engineer** | P0-3, P0-4 | P1-1, P1-7 | — | P3-5 | P4-1, P4-2, P4-4, P4-5 |
| **Mobile/Web Engineer** | — | — | P2-8 | P3-6, P3-7, P3-8, P3-9 | — |

**Timeline with 4 engineers:**
- Phase 0: **Day 1** (parallel)
- Phase 1: **Days 2-5** (parallel tracks)
- Phase 2: **Days 6-9** (parallel)
- Phase 3: **Days 10-13** (parallel)
- Phase 4: **Days 14-21** (parallel)
- **Total: ~3 weeks to production-ready**

---

## 9. Verification Checklist (Definition of Done)

### Pre-Deployment Gate (Must Pass All)

| Check | Tool/Method | Pass Criteria |
|-------|-------------|---------------|
| No secrets in Git | `gitleaks detect --source .` | 0 findings |
| No CRITICAL/HIGH vulns in deps | `trivy fs --severity CRITICAL,HIGH .` | 0 findings |
| SAST clean | `bandit -r backend/ -ll` | 0 HIGH/MEDIUM |
| RLS enforced | `psql -c "SELECT * FROM orders"` (as tenant) | Only tenant rows |
| Rate limiting works | `hey -n 10 -c 2 /api/auth/login` | 429 on 6th |
| Token refresh + reuse detection | Integration test suite | All pass |
| MFA required for OWNER/MANAGER | E2E test | Login → MFA challenge |
| TLS + Security headers | `curl -I https://prod` | HSTS, CSP, X-Frame, etc. |
| Metrics exposed | `curl /metrics` | `http_requests_total` present |
| Logs structured + queryable | Loki query by `request_id` | Returns single trace |
| CI/CD pipeline green | GitHub Actions | All checks pass |
| DR restore tested | Runbook execution | RTO < 4hr, RPO < 1hr |

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Redis dependency breaks local dev | Medium | Low | Provide `docker-compose.dev.yml` with Redis; mock in unit tests |
| RLS breaks complex queries | Medium | High | Thorough test suite; staged rollout (shadow mode first) |
| Certificate pinning rotation missed | Low | High | Calendar reminder 30 days before expiry; dual pins |
| Staff MFA adoption resistance | High | Medium | Phased rollout: OWNER first, then MANAGER; clear UX |
| Rate limiting false positives | Low | Medium | Generous initial limits; monitor 429s; adjust |
| Secret rotation causes downtime | Low | High | Blue/green deploy with new secrets; health checks |

---

## 11. Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Lead | | | |
| Backend Lead | | | |
| DevOps Lead | | | |
| Mobile Lead | | | |
| Web Lead | | | |
| CTO / Engineering Director | | | |

---

## Appendix: Finding Index

| ID | Title | Severity | Phase | Report |
|----|-------|----------|-------|--------|
| CRIT-001 | CORS Wildcard + Credentials | CRITICAL | 0 | CRITICAL_FINDINGS.md |
| CRIT-002 | Secrets in Git | CRITICAL | 0 | CRITICAL_FINDINGS.md |
| CRIT-003 | In-Memory Lockout | CRITICAL | 1 | CRITICAL_FINDINGS.md |
| CRIT-004 | No Rate Limiting | CRITICAL | 1 | CRITICAL_FINDINGS.md |
| MT-001 | Header-Based Tenant Trust | HIGH | 1 | MULTI_TENANT_SECURITY_AUDIT.md |
| MT-003 | No Database RLS | CRITICAL | 1 | MULTI_TENANT_SECURITY_AUDIT.md |
| AUTH-STAFF-001 | No Staff Refresh Tokens | HIGH | 1 | AUTHENTICATION_AUDIT.md |
| AUTH-STAFF-002 | 8hr Token Expiry | HIGH | 1 | AUTHENTICATION_AUDIT.md |
| AUTH-STAFF-004 | No Staff MFA | HIGH | 2 | AUTHENTICATION_AUDIT.md |
| AUTH-QR-001 | QR Status Token Binding | HIGH | 2 | AUTHENTICATION_AUDIT.md |
| RBAC-STAFF-002 | MANAGER→OWNER Escalation | CRITICAL | 2 | RBAC_AUDIT.md |
| RBAC-PLAT-003 | OPS Unilateral Suspend | HIGH | 2 | RBAC_AUDIT.md |
| RBAC-PLAT-004 | Unlimited Refunds | HIGH | 2 | RBAC_AUDIT.md |
| RBAC-PLAT-006 | Bootstrap No MFA | HIGH | 2 | RBAC_AUDIT.md |
| MOB-004 | No Certificate Pinning | HIGH | 3 | MOBILE_SECURITY_AUDIT.md |
| MOB-008 | No Biometric Auth | HIGH | 3 | MOBILE_SECURITY_AUDIT.md |
| INFRA-NET-001 | No TLS | CRITICAL | 0 | INFRASTRUCTURE_SECURITY_AUDIT.md |
| INFRA-DR-001 | No Backups | CRITICAL | 0 | INFRASTRUCTURE_SECURITY_AUDIT.md |
| INFRA-CI-001 | No Security Scanning | HIGH | 4 | INFRASTRUCTURE_SECURITY_AUDIT.md |
| API-VAL-001 | No Request Size Limits | MEDIUM | 3 | API_SECURITY_AUDIT.md |
| ... | ... | ... | ... | ... |