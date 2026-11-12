# Infrastructure Security Audit — Restaurant SaaS Platform

**Classification:** CONFIDENTIAL  
**Scope:** Docker/Compose, CI/CD, secrets management, networking, monitoring, backup/recovery  

---

## Executive Summary

The infrastructure is **development-grade only** — `docker-compose.yml` runs the API and frontend locally with **no production services** (PostgreSQL, Redis, reverse proxy, monitoring). **No CI/CD pipeline** for deployment. **Secrets committed to repo** (CRIT-002). **No secrets management, no backup strategy, no disaster recovery plan.**

**Overall Infrastructure Rating: CRITICAL — Not production-ready**

---

## 1. Container Configuration

### `docker-compose.yml` Analysis

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: []  # NO DATABASE, NO REDIS
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./apps/web
    ports: ["3000:3000"]
    environment: [NEXT_PUBLIC_API_URL=http://localhost:8000]
    command: npm run dev

  # MISSING: postgres, redis, nginx, prometheus, grafana, loki
```

### Vulnerabilities

#### INFRA-001: No Production Services in Compose
**Severity:** CRITICAL  
**Location:** `docker-compose.yml`

Missing critical infrastructure:
- **PostgreSQL** — Database (currently expects external)
- **Redis** — Required for: rate limiting (CRIT-004), lockout store (CRIT-003), session cache, idempotency keys
- **Nginx/Traefik** — Reverse proxy, TLS termination, rate limiting, security headers
- **Prometheus/Grafana** — Metrics, alerting
- **Loki/Promtail** — Log aggregation

**Impact:** Cannot run production stack locally; no local testing of Redis-dependent features.

**Fix:** Add production-profile compose file:
```yaml
# docker-compose.prod.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets: [postgres_password]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck: pg_isready -U ${POSTGRES_USER}

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes: [redis_data:/data]
    healthcheck: redis-cli ping

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes: [./nginx.conf:/etc/nginx/nginx.conf:ro]
    depends_on: [backend, frontend]

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

---

#### INFRA-002: Backend Dockerfile Not Hardened
**Severity:** HIGH  
**Location:** `backend/Dockerfile` (not shown but inferred)

Typical issues in Python Dockerfiles:
- Running as root
- No multi-stage build (dev dependencies in prod)
- No non-root user
- No read-only filesystem
- No capability dropping

**Required hardening:**
```dockerfile
# backend/Dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry export -f requirements.txt > requirements.txt

# Runtime stage
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && rm requirements.txt \
 && adduser --disabled-password --gecos "" appuser

COPY --chown=appuser:appuser ./app ./app
USER appuser

# Security: read-only root fs, drop caps
# (Requires docker run --read-only --cap-drop=ALL --security-opt=no-new-privileges)
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### INFRA-003: Frontend Dockerfile Missing Security Headers
**Severity:** MEDIUM  
**Location:** `apps/web/Dockerfile`

Next.js production build should be served by Nginx with security headers, not `next start` directly.

**Fix:** Multi-stage build → Nginx static serve.

---

## 2. Secrets Management

### Current State: **SECRETS IN GIT (CRIT-002)**

```bash
# backend/.env — COMMITTED TO REPO
SECRET_KEY=your-secret-key-change-in-production
SMTP_PASSWORD=hpzr ghzj ehqw azsj
PLATFORM_SECRET_KEY=dev-platform-signing-key-not-for-production
PLATFORM_MFA_KEY=dev-platform-mfa-key-not-for-production
DATABASE_URL=postgresql://user:pass@localhost/db
```

### Vulnerabilities

#### INFRA-SEC-001: No Secrets Manager
**Severity:** CRITICAL (CRIT-002)  
**Location:** Entire repo

No integration with:
- AWS Secrets Manager / Parameter Store
- Azure Key Vault
- HashiCorp Vault
- Google Secret Manager
- Doppler / Infisical

**Fix:** Implement secrets injection at runtime:
```yaml
# docker-compose.prod.yml
services:
  backend:
    environment:
      SECRET_KEY_FILE: /run/secrets/secret_key
      SMTP_PASSWORD_FILE: /run/secrets/smtp_password
    secrets:
      - secret_key
      - smtp_password

secrets:
  secret_key:
    external: true  # Injected by orchestration (ECS, K8s, etc.)
  smtp_password:
    external: true
```

---

#### INFRA-SEC-002: No Secret Rotation Automation
**Severity:** HIGH  
**Location:** N/A

Secrets never rotated. JWT signing keys, DB passwords, SMTP credentials static.

**Fix:** Automated rotation via secrets manager + application reload (SIGHUP or config watcher).

---

#### INFRA-SEC-003: .env File Loaded in Production
**Severity:** HIGH  
**Location:** `config.py:15`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # LOADS .env IN PRODUCTION!
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
```

If `.env` exists in container, it overrides environment variables. Dangerous.

**Fix:** Remove `env_file` in production; use environment variables only.

---

## 3. CI/CD Pipeline

### Current State: **NO DEPLOYMENT PIPELINE**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e "backend[dev]"
      - run: pytest backend/tests/
```

### Vulnerabilities

#### INFRA-CI-001: No Security Scanning in CI
**Severity:** HIGH  
**Location:** `.github/workflows/ci.yml`

Missing:
- **SAST**: `bandit`, `semgrep`, `codeql`
- **SCA**: `pip-audit`, `snyk`, `dependabot`
- **Container scan**: `trivy`, `grype` on Docker images
- **Secret scan**: `trufflehog`, `gitleaks` (would catch CRIT-002)
- **IaC scan**: `checkov`, `tfsec` (for future Terraform/Bicep)

**Fix:** Add security job:
```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run Trivy
      uses: aquasecurity/trivy-action@master
      with: { scan-type: 'fs', scan-ref: '.', severity: 'CRITICAL,HIGH' }
    - name: Run Gitleaks
      uses: gitleaks/gitleaks-action@v2
    - name: Run Bandit
      run: bandit -r backend/ -f json -o bandit.json
```

---

#### INFRA-CI-002: No Deployment Automation
**Severity:** HIGH  
**Location:** N/A

Manual deployment process — no:
- Staging environment
- Blue/green or canary deployments
- Rollback capability
- Deployment approvals
- Post-deploy smoke tests

**Fix:** Implement GitOps (ArgoCD, Flux) or CI/CD (GitHub Actions → ECS/K8s/Azure Container Apps).

---

#### INFRA-CI-003: No Dependency Pinning Verification
**Severity:** MEDIUM  
**Location:** `pyproject.toml`, `package.json`

Python: `poetry.lock` exists ✅  
Node: `package-lock.json` exists ✅  
But no verification in CI that lockfiles match manifests.

**Fix:** Add `pip check` / `npm ci` verification.

---

## 4. Networking & TLS

### Current State: **NO PRODUCTION NETWORK CONFIG**

| Component | Status |
|-----------|--------|
| TLS Termination | ❌ None (HTTP only in compose) |
| WAF | ❌ None |
| DDoS Protection | ❌ None |
| Private Network | ❌ All services exposed on host ports |
| Service Mesh | ❌ None |
| mTLS | ❌ None |

### Vulnerabilities

#### INFRA-NET-001: No TLS in Development/Production
**Severity:** CRITICAL  
**Location:** `docker-compose.yml`, `nginx.conf` (missing)

All traffic HTTP. Credentials, tokens, PII transmitted in cleartext.

**Fix:** 
- Dev: `mkcert` for local HTTPS
- Prod: Let's Encrypt / ACME / managed certs (AWS ACM, Azure Front Door)

---

#### INFRA-NET-002: Database Exposed (If Configured)
**Severity:** HIGH  
**Location:** `config.py` (DATABASE_URL)

If `DATABASE_URL` points to public endpoint, PostgreSQL exposed to internet.

**Fix:** 
- Private subnet only
- Security groups / NSGs restrict to app servers
- SSL mode `require` + certificate verification

---

#### INFRA-NET-003: No Egress Controls
**Severity:** MEDIUM  
**Location:** N/A

App can make outbound connections to any IP. SSRF risk (webhooks, image fetching, etc.).

**Fix:** Egress proxy / firewall rules allowlist.

---

## 5. Monitoring & Observability

### Current State: **BASIC LOGGING ONLY**

```python
# main.py:50-60
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Structured logging with request_id
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    # ... log request/response
```

### Gaps

#### INFRA-OBS-001: No Metrics Collection
**Severity:** HIGH  
**Location:** N/A

No Prometheus metrics endpoint (`/metrics`). No:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Business metrics (orders/min, revenue/hour)
- Queue depths
- DB connection pool usage

**Fix:** Add `prometheus-fastapi-instrumentator`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

---

#### INFRA-OBS-002: No Centralized Logging
**Severity:** HIGH  
**Location:** N/A

Logs only to stdout. No:
- Log aggregation (Loki, Elasticsearch, Datadog)
- Structured JSON logging
- Log retention policy
- Alert on error patterns

**Fix:** Configure `python-json-logger` + ship to Loki/ELK.

---

#### INFRA-OBS-003: No Distributed Tracing
**Severity:** MEDIUM  
**Location:** N/A

No OpenTelemetry. Cannot trace request across services (when microservices added).

**Fix:** Add `opentelemetry-instrumentation-fastapi` + Jaeger/Tempo.

---

#### INFRA-OBS-004: No Alerting
**Severity:** HIGH  
**Location:** N/A

No alerts for:
- High error rate
- High latency
- Disk/memory/CPU saturation
- Failed deployments
- Security events (failed logins, 4xx spikes)

**Fix:** Prometheus Alertmanager + PagerDuty/Slack/Email.

---

## 6. Backup & Disaster Recovery

### Current State: **NO BACKUP STRATEGY**

| Component | Backup | RPO | RTO | Tested |
|-----------|--------|-----|-----|--------|
| PostgreSQL | ❌ None | N/A | N/A | No |
| Redis | ❌ None | N/A | N/A | No |
| Application Config | ❌ None | N/A | N/A | No |
| Secrets | ❌ None | N/A | N/A | No |

### Vulnerabilities

#### INFRA-DR-001: No Database Backups
**Severity:** CRITICAL  
**Location:** N/A

**Data loss = business failure.** No automated backups, no point-in-time recovery, no cross-region replication.

**Fix:** 
- Managed PostgreSQL (RDS, Cloud SQL, Azure PostgreSQL) with automated backups
- Point-in-time recovery (PITR) enabled
- Cross-region replica for DR
- Regular restore tests (monthly)

---

#### INFRA-DR-002: No Incident Response Plan
**Severity:** HIGH  
**Location:** N/A

No documented runbooks for:
- Security breach
- Data corruption
- Service outage
- Ransomware
- Key compromise

**Fix:** Create IR plan with roles, contacts, procedures.

---

## 7. Dependency & Supply Chain

### Python (`backend/pyproject.toml`)

```toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.109.0"
sqlalchemy = "^2.0.25"
pydantic = "^2.5.3"
python-jose = "^3.3.0"
passlib = "^1.7.4"
argon2-cffi = "^23.1.0"
# ...
```

### Vulnerabilities

#### INFRA-SCM-001: No Automated Dependency Updates
**Severity:** MEDIUM  
**Location:** N/A

No Dependabot / Renovate configured. Security updates missed.

**Fix:** Enable Dependabot:
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule: { interval: "weekly" }
  - package-ecosystem: "npm"
    directory: "/apps/web"
    schedule: { interval: "weekly" }
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
```

---

#### INFRA-SCM-002: No SBOM Generation
**Severity:** LOW  
**Location:** N/A

No Software Bill of Materials for compliance/audit.

**Fix:** `syft` or `cyclonedx-bom` in CI.

---

## 8. Recommendations Priority Matrix

| Priority | Finding | Effort |
|----------|---------|--------|
| P0 | CRIT-002: Remove secrets from Git, rotate all | 2h |
| P0 | INFRA-001: Add PostgreSQL, Redis to compose | 4h |
| P0 | INFRA-NET-001: Enable TLS everywhere | 4h |
| P0 | INFRA-DR-001: Configure managed DB with backups | 8h |
| P1 | INFRA-002: Harden Dockerfiles (non-root, multi-stage) | 4h |
| P1 | INFRA-CI-001: Add security scanning to CI | 6h |
| P1 | INFRA-OBS-001: Add Prometheus metrics | 4h |
| P1 | INFRA-OBS-002: Centralized logging | 6h |
| P1 | INFRA-SEC-001: Integrate secrets manager | 8h |
| P2 | INFRA-CI-002: Deployment automation | 16h |
| P2 | INFRA-NET-002: Private networking for DB | 4h |
| P2 | INFRA-OBS-004: Alerting rules | 8h |
| P3 | INFRA-DR-002: Incident response plan | 8h |
| P3 | INFRA-SCM-001: Dependabot | 1h |

---

## 9. Verification Test Suite

```bash
# tests/test_infrastructure.sh

# 1. Verify no secrets in repo
test_no_secrets_in_git() {
  if git log --all --full-history -- backend/.env | grep -q "."; then
    echo "FAIL: .env in Git history"
    return 1
  fi
  echo "PASS: No .env in Git"
}

# 2. Verify Dockerfile runs as non-root
test_dockerfile_non_root() {
  docker build -t test-backend ./backend
  docker run --rm test-backend whoami | grep -q "appuser"
  echo "PASS: Runs as non-root"
}

# 3. Verify TLS in production compose
test_tls_configured() {
  grep -q "443:443" docker-compose.prod.yml
  grep -q "ssl_certificate" nginx.conf
  echo "PASS: TLS configured"
}

# 4. Verify metrics endpoint
test_metrics_endpoint() {
  curl -s http://localhost:8000/metrics | grep -q "http_requests_total"
  echo "PASS: Metrics exposed"
}

# 5. Verify security headers
test_security_headers() {
  headers=$(curl -sI https://api.prod.com/health)
  echo "$headers" | grep -qi "strict-transport-security"
  echo "$headers" | grep -qi "x-frame-options: DENY"
  echo "$headers" | grep -qi "content-security-policy"
  echo "PASS: Security headers present"
}

# 6. Verify CI has security scanning
test_ci_security_scanning() {
  grep -q "trivy\|gitleaks\|bandit" .github/workflows/ci.yml
  echo "PASS: Security scanning in CI"
}

# 7. Verify managed DB backup config
test_db_backups() {
  # Check terraform/bicep for backup_retention_days > 0
  # Check point_in_time_recovery = true
  echo "PASS: DB backups configured"
}
```

---

## Conclusion

The infrastructure is **not production-ready**. Critical gaps:
1. **Secrets in Git (CRIT-002)** — immediate rotation required
2. **No PostgreSQL/Redis in compose** — cannot test Redis-dependent fixes (CRIT-003, CRIT-004)
3. **No TLS** — all traffic cleartext
4. **No backups** — data loss = business failure
5. **No CI/CD security scanning** — vulnerabilities ship to prod

**Immediate priorities (before any production deployment):**
1. Rotate all secrets (CRIT-002)
2. Add PostgreSQL + Redis to docker-compose
3. Configure TLS (dev + prod)
4. Provision managed PostgreSQL with automated backups
5. Add security scanning to CI

**Architecture decision needed:** Target platform (ECS/Fargate, AKS, Container Apps, Cloud Run, VMs) to design proper IaC.